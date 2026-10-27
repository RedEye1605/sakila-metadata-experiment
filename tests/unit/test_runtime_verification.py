import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.config import AppConfig, InferenceConfig
from sakila_experiment.generation import runtime


@pytest.fixture
def runtime_case(tmp_path, monkeypatch):
    model = tmp_path / "downloads/models/revision/fixture.gguf"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"synthetic model")
    receipt = tmp_path / "download.json"
    receipt.write_bytes(canonical_json({"status": "download_verified", "local_file": str(model.relative_to(tmp_path)), "model_sha256": sha256_bytes(model.read_bytes()),
                                      "model_id": "Qwen/fixture", "repository_revision": "b" * 40, "filename": model.name}))
    compose = tmp_path / "compose.yaml"; compose.write_text("synthetic fixture")
    command = ["--model", "/models/fixture.gguf", "--alias", "fixture", "--ctx-size", "16384", "--parallel", "1", "--n-gpu-layers", "24", "--threads", "6", "--batch-size", "512", "--ubatch-size", "128", "--fit", "off", "--cache-ram", "0", "--no-cache-prompt", "--no-context-shift", "--no-cont-batching"]
    container = {"State": {"Running": True}, "Config": {"Image": "fixture@sha256:" + "a" * 64, "Cmd": command}, "Image": "fixture-id", "HostConfig": {"Memory": 7 * 2**30},
                 "Mounts": [{"Destination": "/models", "RW": False, "Source": str(model.parent)}]}
    def run(arguments, **kwargs):
        if arguments[:2] == ["docker", "inspect"]: data = [container]
        elif arguments[:3] == ["docker", "image", "inspect"]:
            data = [{"Config": {"Labels": {"org.opencontainers.image.revision": "a" * 40, "org.opencontainers.image.version": "btest"}}}]
        else: return SimpleNamespace(stdout="Synthetic GPU fixture")
        return SimpleNamespace(stdout=json.dumps(data))
    monkeypatch.setattr(runtime.subprocess, "run", run)
    props = {"total_slots": 1, "model_alias": "fixture", "default_generation_settings": {"n_ctx": 16384}, "model_ftype": "Q4_K - Medium", "build_info": "btest-aaaaaaaaa", "chat_template": "synthetic template"}
    requests = []
    def handler(request):
        path = request.url.path; requests.append(path)
        documents = {"/health": {"status": "ok"}, "/v1/models": {"data": [{"id": "fixture"}]}, "/props": props, "/slots": [],
                     "/apply-template": {"prompt": "synthetic rendered prompt"}, "/tokenize": {"tokens": list(range(10))}}
        assert path in documents, "Verification must never dispatch model generation"
        return httpx.Response(200, json=documents[path])
    client = httpx.Client
    monkeypatch.setattr(runtime.httpx, "Client", lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setattr(runtime, "validate_scenario_set", lambda p: {})
    snapshots = tmp_path / "snapshots"
    payload = {"technical_schema": {}, "descriptions": [], "business_context": []}
    for scenario in ("S0", "S1", "S2", "S3"):
        folder = snapshots / scenario; folder.mkdir(parents=True)
        (folder / "payload.json").write_bytes(canonical_json(payload))
        (folder / "manifest.json").write_bytes(canonical_json({"payload_file": "payload.json", "snapshot_sha256": sha256_bytes(canonical_json(payload))}))
    (tmp_path / "data/pilot").mkdir(parents=True)
    (tmp_path / "data/pilot/questions.jsonl").write_bytes(canonical_json({"question_id": "P001", "question": "Pertanyaan sintetis untuk token budget?", "complexity": "simple"}))
    (tmp_path / "prompts").mkdir(); (tmp_path / "prompts/generation.txt").write_text("Generate SQL only")
    config = AppConfig(project_root=tmp_path, inference=InferenceConfig(model_id="fixture"))
    return config, receipt, compose, snapshots, container, requests, model


def test_model_and_context_verification_makes_zero_generation_requests(runtime_case, tmp_path):
    config, receipt, compose, snapshots, container, requests, model = runtime_case
    report = runtime.verify_backend(config, receipt, compose, "fixture", snapshots, tmp_path / "evidence")
    assert report["generation_requests"] == 0 and report["pilot_prompts_checked"] == 4
    assert "/v1/chat/completions" not in requests


def test_modified_weights_fail_before_any_server_call(runtime_case, tmp_path):
    config, receipt, compose, snapshots, container, requests, model = runtime_case
    model.write_bytes(b"modified weights")
    with pytest.raises(ValueError, match="bytes/path"):
        runtime.verify_backend(config, receipt, compose, "fixture", snapshots, tmp_path / "evidence")
    assert requests == []


def test_adaptive_execution_settings_are_rejected(runtime_case, tmp_path):
    config, receipt, compose, snapshots, container, requests, model = runtime_case
    container["Config"]["Cmd"][container["Config"]["Cmd"].index("--fit") + 1] = "on"
    with pytest.raises(ValueError, match="execution options"):
        runtime.verify_backend(config, receipt, compose, "fixture", snapshots, tmp_path / "evidence")
    assert requests == []
