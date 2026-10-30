"""Explicit researcher-selected replication without additional pilot generation.

The waiver is hash-bound to one model/configuration and the already reviewed
stimulus. Database, reference, context, safety and logging checks still apply.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import Field

from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from ..config import StrictModel, load_config
from ..contracts import DatasetError
from ..generation.backend import check_live_backend, load_backend_evidence
from ..generation.model_assets import ModelSpec
from ..instrument import ArtifactReference, read_manifest
from .execution_review import stimulus_identity, stimulus_scope


class DirectMainAmendment(StrictModel):
    amendment_version: Literal[1] = 1
    status: Literal["user_authorized_direct_main"]
    source: Literal["direct_user_statement"]
    statement: str = Field(min_length=40)
    recorded_at_utc: str
    upstream_model: Literal["Qwen/Qwen3.5-9B"]
    selection_basis: Literal["researcher_selected_after_prior_results"]
    source_instrument: ArtifactReference
    model_specification: ArtifactReference
    configuration: ArtifactReference
    compose: ArtifactReference
    prior_main_manifest: ArtifactReference
    prior_candidate_completion: ArtifactReference
    scope: dict[str, ArtifactReference]
    stimulus_identity: str = Field(pattern=r"^[a-f0-9]{64}$")
    backend_command: tuple[str, ...]
    capability_pilot: Literal["waived_by_researcher"]
    generation_smoke: Literal["waived_by_researcher"]
    preflight_generation_requests: Literal[0]
    main_trial_count: Literal[600]
    sampler_policy: Literal["verify_each_completed_main_request_without_new_generation"]
    monitoring: Literal["researcher_only_after_launch"]
    actual_results_publication: Literal["local_only"]
    limitations: tuple[str, ...] = Field(min_length=2)


def validate_direct_amendment(root: Path, instrument, paths) -> DirectMainAmendment:
    if instrument.execution_amendment is None or instrument.smoke_test is not None:
        raise DatasetError("Direct execution needs its explicit amendment and no smoke claim")
    document = DirectMainAmendment.model_validate_json(paths["execution_amendment"].read_bytes())
    if datetime.fromisoformat(document.recorded_at_utc.replace("Z", "+00:00")).utcoffset() is None:
        raise DatasetError("Amendment recording time must include its UTC offset")
    source_path = document.source_instrument.verified_path(root)
    original, _ = read_manifest(root, source_path)
    if (document.stimulus_identity != stimulus_identity(instrument)
            or stimulus_scope(original) != stimulus_scope(instrument)
            or {k: v.model_dump(mode="json") for k, v in document.scope.items()} != stimulus_scope(instrument)
            or instrument.execution_review != original.execution_review):
        raise DatasetError("Amendment changed the reviewed stimulus or review provenance")
    for name in ("model_specification", "configuration", "compose", "prior_main_manifest", "prior_candidate_completion"):
        getattr(document, name).verified_path(root)
    spec = ModelSpec.model_validate_json(document.model_specification.verified_path(root).read_bytes())
    if (spec.model_id != "unsloth/Qwen3.5-9B-GGUF"
            or spec.model_sha256 != "03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8"
            or spec.alias != "sakila-qwen35-9b-q4km"):
        raise DatasetError("The researcher locked this amendment to the pinned Qwen3.5-9B")
    prior = json.loads(document.prior_main_manifest.verified_path(root).read_bytes())
    candidate = json.loads(document.prior_candidate_completion.verified_path(root).read_bytes())
    if (prior.get("mode") != "main" or prior.get("trial_count") != 600
            or candidate.get("status") != "candidate_pipeline_complete"):
        raise DatasetError("The amendment must retain the actual prior research history")
    return document


def direct_main_inputs(config, manifest, questions, backend_path: Path):
    root = config.project_root
    instrument, paths = read_manifest(root, config.resolve(config.benchmark_manifest))
    amendment = validate_direct_amendment(root, instrument, paths)
    if load_config(amendment.configuration.verified_path(root)) != config:
        raise DatasetError("Runtime configuration differs from the authorized amendment")
    evidence, backend = load_backend_evidence(backend_path)
    spec = ModelSpec.model_validate_json(amendment.model_specification.verified_path(root).read_bytes())
    if (evidence.model_sha256 != spec.model_sha256 or evidence.model_id != spec.alias
            or backend.get("model_repository_revision") != spec.repository_revision
            or backend.get("model_repository") != spec.model_id
            or backend.get("compose_sha256") != amendment.compose.sha256
            or backend.get("command") != list(amendment.backend_command)):
        raise DatasetError("Observed backend differs from the explicitly locked model/deployment")
    command = list(amendment.backend_command)
    for name, expected in (("--reasoning", "on"), ("--reasoning-format", "deepseek"), ("--reasoning-budget", "2048")):
        if name not in command or command[command.index(name) + 1] != expected:
            raise DatasetError("The amended reasoning settings are incomplete")
    from .runner import _prompt_budgets
    budgets = _prompt_budgets(config, backend_path, questions, root / "runs/revision-02/metadata/preparation-03/snapshots")
    expected = {(q, s) for q in questions for s in config.experiment.scenario_ids}
    if len(budgets) != 120 or {(b["question_id"], b["scenario_id"]) for b in budgets} != expected:
        raise DatasetError("Every one of the120main contexts must fit completely")
    manifest.update(execution_amendment=amendment.model_dump(mode="json"),
                    execution_amendment_sha256=instrument.execution_amendment.sha256,
                    model_selection_status=amendment.selection_basis,
                    additional_capability_pilot_requests=0, engineering_generation_requests=0,
                    complete_main_prompt_budgets=budgets, verified_pilot_manifest_sha256=None,
                    sampler_checkpoint_policy=amendment.sampler_policy,
                    note=manifest["note"] + " Researcher-selected post-first-run replication; additional pilot/smoke generation explicitly waived.")


def validate_main_sampler(proof: dict, manifest: dict, row: dict, manifest_sha256: str) -> None:
    settings = manifest["inference_config"]
    expected = {"seed": row["inference_seed"], "temperature": settings["temperature"],
                "top_p": settings["top_p"], "top_k": settings["top_k"], "min_p": 0.0,
                "repeat_penalty": 1.0, "max_tokens": settings["max_output_tokens"]}
    if (proof.get("status") != "main_sampler_seed_cache_verified"
            or proof.get("model_sha256") != manifest["model_version_or_hash"]
            or proof.get("backend_evidence_sha256") != manifest["backend_evidence_sha256"]
            or proof.get("manifest_sha256") != manifest_sha256
            or proof.get("source_trial") != row["trial_id"]
            or proof.get("source_outcome_sha256") != sha256_bytes(canonical_json(row))
            or proof.get("expected_request_settings") != expected or proof.get("generation_requests") != 0):
        raise DatasetError("Main sampler proof does not bind this actual completed request")
    slots = proof.get("observed_slots", [])
    if (len(slots) != 1 or slots[0].get("is_processing") is not False
            or slots[0].get("n_prompt_tokens_cache") != 0):
        raise DatasetError("Main sampler is active, cached or does not have exactly one slot")
    params = slots[0].get("params", {})
    for key, value in expected.items():
        actual = params.get(key)
        if (type(actual) not in (int, float)
                or (actual != value if type(value) is int else not math.isclose(actual, value, rel_tol=1e-6))):
            raise DatasetError("Observed main sampler differs: " + key)


def verify_main_sampler(config, backend_path: Path, directory: Path, trial_id: str) -> dict:
    """Observe the just-completed main request; never add a generation request."""
    data = (directory / "manifest.json").read_bytes()
    manifest = json.loads(data)
    if (manifest.get("mode") != "main" or not manifest.get("execution_amendment_sha256")
            or manifest.get("inference_config") != config.inference.model_dump(mode="json")):
        raise DatasetError("Per-request main observation requires this amended frozen configuration")
    with sqlite3.connect((directory / "ledger.sqlite3").resolve().as_uri() + "?mode=ro", uri=True) as connection:
        registered = connection.execute("SELECT manifest_sha256 FROM experiments WHERE experiment_id=?", (manifest["experiment_id"],)).fetchone()
        event = connection.execute("SELECT payload_json,payload_sha256 FROM events WHERE experiment_id=? AND trial_id=? AND kind='trial_completed'", (manifest["experiment_id"], trial_id)).fetchone()
    if (registered != (sha256_bytes(data),) or event is None or sha256_bytes(event[0].encode()) != event[1]):
        raise DatasetError("Sampler observation requires a hash-verified durable main outcome")
    row = json.loads(event[0])
    if (row.get("model_version_or_hash") != manifest["model_version_or_hash"]
            or row.get("inference_config") != manifest["inference_config"]):
        raise DatasetError("Sampler source outcome uses another model or inference configuration")
    output = directory / "sampler" / f"{trial_id}.json"
    if output.exists():
        proof = json.loads(output.read_bytes())
        validate_main_sampler(proof, manifest, row, sha256_bytes(data))
        return proof
    evidence, backend = load_backend_evidence(backend_path)
    if evidence.verification_artifact_sha256 != manifest["backend_evidence_sha256"]:
        raise DatasetError("Sampler backend identity changed")
    check_live_backend(config.inference, backend)
    with httpx.Client(timeout=15, trust_env=False) as client:
        response = client.get(config.inference.base_url + "/slots")
        response.raise_for_status()
        slots = response.json()
    proof = {"status": "main_sampler_seed_cache_verified", "model_sha256": evidence.model_sha256,
             "backend_evidence_sha256": evidence.verification_artifact_sha256,
             "manifest_sha256": sha256_bytes(data), "source_trial": trial_id,
             "source_outcome_sha256": event[1], "generation_requests": 0,
             "expected_request_settings": {"seed": row["inference_seed"], "temperature": config.inference.temperature,
                 "top_p": config.inference.top_p, "top_k": config.inference.top_k, "min_p": 0.0,
                 "repeat_penalty": 1.0, "max_tokens": config.inference.max_output_tokens}, "observed_slots": slots}
    validate_main_sampler(proof, manifest, row, sha256_bytes(data))
    publish_artifact(output, canonical_json(proof))
    return proof
