import json
from pathlib import Path

import httpx
import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.config import InferenceConfig
from sakila_experiment.contracts import GenerationInput
from sakila_experiment.generation.llama import BackendEvidence, LlamaClient, LLMServiceError
from sakila_experiment.generation.prompt import PromptError, build_prompt

ROOT = Path(__file__).resolve().parents[2]


def prompt():
    # Synthetic fixture only: never persisted as an experimental snapshot.
    payload = {"technical_schema": {"tables": []}, "descriptions": [], "business_context": []}
    return build_prompt(GenerationInput(question="Berapa jumlah film yang tercatat?"), payload, sha256_bytes(canonical_json(payload)), ROOT / "prompts/generation.txt")


def fixture_client(token_count=10, *, usage=True, failure=False):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path == "/apply-template":
            return httpx.Response(200, json={"prompt": "formatted fixture"})
        if request.url.path == "/tokenize":
            return httpx.Response(200, json={"tokens": list(range(token_count))})
        if failure:
            raise httpx.ReadTimeout("fixture timeout", request=request)
        body = {"choices": [{"message": {"content": "SELECT 1"}, "finish_reason": "stop"}]}
        if usage:
            body["usage"] = {"prompt_tokens": token_count, "completion_tokens": 3}
        return httpx.Response(200, json=body)
    evidence = BackendEvidence("fixture-model", "a" * 64, "fixture-revision", 16384, "b" * 64)
    transport = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    return LlamaClient(InferenceConfig(model_id="fixture-model"), evidence, client=transport), requests, transport


def test_one_generation_request_has_no_history_tools_or_scenario_label():
    client, requests, transport = fixture_client()
    try:
        prepared = client.prepare(prompt())
        response = client.generate(prepared, 123)
        generation = [r for r in requests if r.url.path == "/v1/chat/completions"]
        assert len(generation) == 1
        payload = json.loads(generation[0].content)
        assert [m["role"] for m in payload["messages"]] == ["system", "user"]
        assert "tools" not in payload
        assert payload["cache_prompt"] is False
        assert payload["seed"] == 123
        assert response.raw_response["choices"][0]["message"]["content"] == "SELECT 1"
        assert response.input_tokens == 10
    finally:
        transport.close()


def test_complete_context_overflow_never_dispatches_generation():
    client, requests, transport = fixture_client(token_count=16384)
    try:
        with pytest.raises(LLMServiceError, match="prompt_exceeds"):
            client.prepare(prompt())
        assert not any(r.url.path == "/v1/chat/completions" for r in requests)
    finally:
        transport.close()


def test_missing_backend_usage_is_null_not_an_invented_count():
    client, _, transport = fixture_client(usage=False)
    try:
        response = client.generate(client.prepare(prompt()), 123)
        assert response.input_tokens is response.output_tokens is None
        assert response.token_usage_source == "unavailable_or_partial"
    finally:
        transport.close()


def test_transport_failure_does_not_retry_generation():
    client, requests, transport = fixture_client(failure=True)
    try:
        prepared = client.prepare(prompt())
        with pytest.raises(LLMServiceError):
            client.generate(prepared, 123)
        assert sum(r.url.path == "/v1/chat/completions" for r in requests) == 1
    finally:
        transport.close()


def test_snapshot_labels_and_hash_mismatches_are_rejected():
    with pytest.raises(PromptError):
        build_prompt(GenerationInput(question="Berapa jumlah film yang tercatat?"), {"scenario_id": "S3"}, "a" * 64, ROOT / "prompts/generation.txt")
    payload = {"technical_schema": {}, "descriptions": [], "business_context": []}
    with pytest.raises(PromptError, match="hash"):
        build_prompt(GenerationInput(question="Berapa jumlah film yang tercatat?"), payload, "a" * 64, ROOT / "prompts/generation.txt")


def test_repetitions_send_identical_messages_without_previous_response():
    client, requests, transport = fixture_client()
    try:
        prepared = client.prepare(prompt())
        client.generate(prepared, 123)
        client.generate(prepared, 456)
        payloads = [json.loads(r.content) for r in requests if r.url.path == "/v1/chat/completions"]
        assert payloads[0]["messages"] == payloads[1]["messages"]
        assert [p["seed"] for p in payloads] == [123, 456]
        assert all(len(p["messages"]) == 2 for p in payloads)
    finally:
        transport.close()


def test_default_unverified_model_configuration_cannot_generate():
    evidence = BackendEvidence("fixture-model", "a" * 64, "fixture", 16384, "b" * 64)
    with pytest.raises(LLMServiceError, match="configuration_differs"):
        LlamaClient(InferenceConfig(), evidence)

