"""Strict non-secret configuration; credentials are resolved only when needed."""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator, model_validator


class ConfigurationError(ValueError):
    """A safe-to-display configuration problem."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class DatabaseConfig(StrictModel):
    host: str = "127.0.0.1"
    port: int = Field(default=13306, ge=1, le=65535)
    database: str = "sakila"
    username: str = "experiment_reader"
    password_env: str = "SAKILA_READER_PASSWORD"
    password_file: str | None = "secrets/reader_password.txt"
    connect_timeout_s: int = Field(default=5, ge=1, le=60)
    read_timeout_s: int = Field(default=15, ge=1)
    query_timeout_ms: int = Field(default=10000, ge=1)
    max_rows: int = Field(default=100000, ge=1)
    max_result_bytes: int = Field(default=67108864, ge=1)
    sql_mode: str = "ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION"
    time_zone: str = "+00:00"
    sql_policy_version: Literal["mysql-readonly-v1", "mysql-readonly-v2"] = "mysql-readonly-v1"
    time_names_locale: Literal["en_US"] | None = None

    @field_validator("database", "username")
    @classmethod
    def safe_identifier(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError("must be a simple SQL identifier")
        return value

    @field_validator("username")
    @classmethod
    def no_admin(cls, value: str) -> str:
        if value.lower() in {"root", "admin", "mysql", "datahub"}:
            raise ValueError("an experiment-specific read-only account is required")
        return value

    @field_validator("password_env")
    @classmethod
    def env_name(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
            raise ValueError("must name an environment variable")
        return value

    @model_validator(mode="after")
    def timeout_order(self) -> Self:
        if self.read_timeout_s * 1000 <= self.query_timeout_ms:
            raise ValueError("client read timeout must exceed server query timeout")
        if self.time_zone != "+00:00":
            raise ValueError("the experiment database session must use UTC")
        return self


def validate_service_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("must be an HTTP service URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("service URLs must not contain credentials, query, or fragment")
    try:
        parsed.port
    except ValueError:
        raise ValueError("invalid service port") from None
    return value.rstrip("/")


class DataHubConfig(StrictModel):
    gms_url: str = "http://127.0.0.1:18080"
    ui_url: str = "http://127.0.0.1:19002"
    token_env: str = "DATAHUB_GMS_TOKEN"
    server_version: str = "0.8.0"
    field_description_length_limit: int = Field(default=16384, ge=121)
    description_length_limit: int = Field(default=65536, ge=121)

    _urls = field_validator("gms_url", "ui_url")(validate_service_url)


class InferenceConfig(StrictModel):
    base_url: str = "http://127.0.0.1:18081"
    model_id: str = "UNVERIFIED"
    context_tokens: int = Field(default=16384, ge=1024)
    max_output_tokens: int = Field(default=1024, ge=1)
    safety_margin_tokens: int = Field(default=256, ge=1)
    temperature: float = Field(default=0.2, gt=0, le=2, allow_inf_nan=False)
    top_p: float = Field(default=0.95, gt=0, le=1, allow_inf_nan=False)
    top_k: int = Field(default=40, ge=0)
    timeout_s: int = Field(default=600, ge=1)

    _url = field_validator("base_url")(validate_service_url)

    @model_validator(mode="after")
    def context_budget(self) -> Self:
        if self.max_output_tokens + self.safety_margin_tokens >= self.context_tokens:
            raise ValueError("context must reserve space for the input prompt")
        return self


class ExperimentConfig(StrictModel):
    repetitions: int = 5
    question_count: int = 30
    questions_per_complexity: int = 10
    scenario_ids: tuple[str, ...] = ("S0", "S1", "S2", "S3")
    order_seed: int = Field(default=20261027, ge=0)
    inference_seed_base: int = Field(default=27102026, ge=0)
    analysis_seed: int = Field(default=20261029, ge=0)

    @model_validator(mode="after")
    def approved_design(self) -> Self:
        if (self.repetitions, self.question_count, self.questions_per_complexity) != (5, 30, 10):
            raise ValueError("the approved main design is 30 questions, 10 per complexity, 5 repetitions")
        if self.scenario_ids != ("S0", "S1", "S2", "S3"):
            raise ValueError("the approved scenario order is S0, S1, S2, S3")
        return self


class AppConfig(StrictModel):
    project_root: Path = Path("..")
    benchmark_manifest: str | None = None
    diagnostic_manifest: str | None = None
    prompt_template: str = "prompts/generation.txt"
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    datahub: DataHubConfig = Field(default_factory=DataHubConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    experiment: ExperimentConfig = Field(default_factory=ExperimentConfig)

    def resolve(self, relative: str | Path) -> Path:
        return (self.project_root / relative).resolve()

    def database_password(self) -> SecretStr:
        value = os.environ.get(self.database.password_env)
        if value:
            return SecretStr(value)
        if self.database.password_file:
            path = self.resolve(self.database.password_file)
            try:
                value = path.read_text(encoding="utf-8").strip()
            except OSError:
                value = None
            if value:
                return SecretStr(value)
        raise ConfigurationError("Database reader credential is unavailable; configure its environment variable or secret file")


def load_config(path: str | Path) -> AppConfig:
    source = Path(path).resolve()
    try:
        with source.open("rb") as handle:
            document = tomllib.load(handle)
    except OSError:
        raise ConfigurationError("Configuration file cannot be read") from None
    except tomllib.TOMLDecodeError:
        raise ConfigurationError("Configuration file is not valid TOML") from None
    try:
        config = AppConfig.model_validate(document)
    except ValidationError as exc:
        # Do not display values, validator contexts, or raw TOML.
        issues = [f"{'.'.join(map(str, item['loc'])) or 'configuration'}: {item['type']}"
                  for item in exc.errors(include_input=False, include_context=False, include_url=False)]
        raise ConfigurationError("Invalid configuration: " + "; ".join(issues)) from None
    return config.model_copy(update={"project_root": (source.parent / config.project_root).resolve()})

