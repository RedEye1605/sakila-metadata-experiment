"""One-request llama-server transport, gated by backend and token-budget evidence.

HTTP contracts have offline tests. A real model/backend verification record must
be produced during the later runtime milestone before this client is used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from time import perf_counter

import httpx

from ..artifacts import canonical_json, sha256_bytes
from ..config import InferenceConfig
from .prompt import PromptArtifact


class LLMServiceError(RuntimeError):
    def __init__(self, code: str, *, raw_response=None):
        super().__init__(code)
        self.code = code
        self.raw_response = raw_response


@dataclass(frozen=True)
class BackendEvidence:
    model_id: str
    model_sha256: str
    backend_revision: str
    effective_context_tokens: int
    verification_artifact_sha256: str

    def __post_init__(self):
        if self.model_id == "UNVERIFIED" or not self.backend_revision or self.effective_context_tokens < 1024:
            raise LLMServiceError("backend_evidence_incomplete")
        if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in (self.model_sha256, self.verification_artifact_sha256)):
            raise LLMServiceError("backend_evidence_hash_invalid")


@dataclass(frozen=True)
class CheckedPrompt:
    prompt: PromptArtifact
    input_tokens: int
    backend_evidence: BackendEvidence


@dataclass(frozen=True)
class GenerationResponse:
    raw_response: dict
    text: str | None
    finish_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    token_usage_source: str
    inference_latency_ms: float
    response_valid: bool
    infrastructure_error: str | None = None


class LlamaClient:
    def __init__(self, settings: InferenceConfig, evidence: BackendEvidence, *, client: httpx.Client | None = None):
        if settings.model_id != evidence.model_id or settings.context_tokens > evidence.effective_context_tokens:
            raise LLMServiceError("configuration_differs_from_verified_backend")
        self.settings = settings
        self.evidence = evidence
        self.client = client or httpx.Client(timeout=httpx.Timeout(settings.timeout_s, connect=5), trust_env=False)
        self.owns_client = client is None

    def close(self):
        if self.owns_client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _post(self, path: str, payload: dict) -> dict:
        try:
            response = self.client.post(self.settings.base_url + path, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise LLMServiceError("backend_http_error", raw_response=error.response.text) from None
        except httpx.HTTPError:
            # No automatic retry: a lost generation response can be ambiguous.
            raise LLMServiceError("backend_transport_error") from None
        try:
            document = response.json()
        except ValueError:
            raise LLMServiceError("backend_non_json_response", raw_response=response.text) from None
        if not isinstance(document, dict):
            raise LLMServiceError("backend_invalid_response_object", raw_response=document)
        return document

    def prepare(self, prompt: PromptArtifact) -> CheckedPrompt:
        if sha256_bytes(canonical_json(prompt.chat_messages())) != prompt.prompt_sha256:
            raise LLMServiceError("prompt_hash_mismatch")
        rendered = self._post("/apply-template", {"messages": prompt.chat_messages()})
        if not isinstance(rendered.get("prompt"), str) or not rendered["prompt"]:
            raise LLMServiceError("backend_template_response_invalid", raw_response=rendered)
        tokenized = self._post("/tokenize", {"content": rendered["prompt"], "add_special": False, "parse_special": True, "with_pieces": False})
        tokens = tokenized.get("tokens")
        if not isinstance(tokens, list) or not tokens or any(type(token) is not int or token < 0 for token in tokens):
            raise LLMServiceError("backend_tokenizer_response_invalid", raw_response=tokenized)
        if len(tokens) + self.settings.max_output_tokens + self.settings.safety_margin_tokens > self.settings.context_tokens:
            raise LLMServiceError("prompt_exceeds_complete_context_budget")
        return CheckedPrompt(prompt, len(tokens), self.evidence)

    def generate(self, checked: CheckedPrompt, seed: int) -> GenerationResponse:
        if checked.backend_evidence != self.evidence or not 0 <= seed < 2147483647:
            raise LLMServiceError("request_evidence_or_seed_invalid")
        if checked.input_tokens < 1:
            raise LLMServiceError("input_token_evidence_invalid")
        if sha256_bytes(canonical_json(checked.prompt.chat_messages())) != checked.prompt.prompt_sha256:
            raise LLMServiceError("prompt_hash_mismatch")
        if checked.input_tokens + self.settings.max_output_tokens + self.settings.safety_margin_tokens > self.settings.context_tokens:
            raise LLMServiceError("prompt_exceeds_complete_context_budget")
        payload = {"model": self.evidence.model_id, "messages": checked.prompt.chat_messages(),
                   "temperature": self.settings.temperature, "top_p": self.settings.top_p,
                   "top_k": self.settings.top_k, "min_p": 0.0, "repeat_penalty": 1.0,
                   "max_tokens": self.settings.max_output_tokens, "seed": seed,
                   "stream": False, "cache_prompt": False, "n": 1}
        started = perf_counter()
        raw = self._post("/v1/chat/completions", payload)
        elapsed = (perf_counter() - started) * 1000
        choices = raw.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            return GenerationResponse(raw, None, None, None, None, "unavailable", elapsed, False, "backend_choices_invalid")
        choice = choices[0]
        message = choice.get("message")
        text = message.get("content") if isinstance(message, dict) else None
        usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        def count(name):
            value = usage.get(name)
            return value if type(value) is int and value >= 0 else None
        inputs, outputs = count("prompt_tokens"), count("completion_tokens")
        mismatch = inputs is not None and inputs != checked.input_tokens
        return GenerationResponse(raw, text if isinstance(text, str) else None, choice.get("finish_reason"), inputs, outputs,
                                  "api_usage" if inputs is not None and outputs is not None else "unavailable_or_partial",
                                  elapsed, isinstance(text, str) and bool(text.strip()),
                                  "input_token_accounting_mismatch" if mismatch else None)

