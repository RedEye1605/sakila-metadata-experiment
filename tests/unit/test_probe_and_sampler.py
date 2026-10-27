from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from sakila_experiment.artifacts import canonical_json
from sakila_experiment.config import AppConfig, InferenceConfig
from sakila_experiment.generation import backend, probe, runtime
from sakila_experiment.generation.llama import BackendEvidence
from sakila_experiment.analysis import report


def test_draft_probe_stops_before_backend_access(tmp_path, monkeypatch):
    for name, data in (("questions.jsonl", {"question_id": "P007", "question": "Pertanyaan pilot sintetis yang belum direview?", "complexity": "complex"}),
                       ("gold.jsonl", {"question_id": "P007", "sql": "SELECT 1", "column_count": 1, "review_status": "draft"})):
        path = tmp_path / "data/pilot" / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(canonical_json(data))
    monkeypatch.setattr(probe, "load_backend_evidence", lambda *a: pytest.fail("Draft inputs must not reach backend verification"))
    with pytest.raises(ValueError, match="draft"):
        probe.repetition_probe(AppConfig(project_root=tmp_path), tmp_path, tmp_path / "backend.json", tmp_path / "probe")
    assert not (tmp_path / "probe").exists()


def test_sampler_belongs_to_audited_backend_and_seed(tmp_path, monkeypatch):
    evidence = BackendEvidence("fixture", "a" * 64, "fixture", 16384, "b" * 64)
    config = AppConfig(project_root=tmp_path, inference=InferenceConfig(model_id="fixture"))
    monkeypatch.setattr(backend, "load_backend_evidence", lambda p: (evidence, {}))
    monkeypatch.setattr(backend, "check_live_backend", lambda *a: None)
    pilot = tmp_path / "pilot"; pilot.mkdir(); (pilot / "manifest.json").write_text("synthetic manifest")
    manifest = {"inference_config": config.inference.model_dump(mode="json"), "backend_evidence_sha256": "b" * 64}
    records = [{"schedule_position": 1, "inference_seed": 123, "trial_id": "P001-S0-r01"}]
    monkeypatch.setattr(report, "audit_run", lambda p: (manifest, records))
    slots = [{"is_processing": False, "n_prompt_tokens_cache": 0, "params": {"seed": 123, "temperature": .2, "top_p": .95, "top_k": 40, "min_p": 0., "repeat_penalty": 1., "max_tokens": 1024}}]
    calls = []
    def handler(request):
        calls.append(request.url.path); assert request.method == "GET" and request.url.path == "/slots"
        return httpx.Response(200, json=slots)
    client = httpx.Client
    monkeypatch.setattr(runtime.httpx, "Client", lambda **k: client(transport=httpx.MockTransport(handler), **k))
    result = runtime.verify_sampler(config, tmp_path / "backend.json", pilot, tmp_path / "sampler.json")
    assert result["generation_requests"] == 0 and calls == ["/slots"]
    slots[0]["params"]["seed"] = 124
    with pytest.raises(ValueError, match="sampler/seed"):
        runtime.verify_sampler(config, tmp_path / "backend.json", pilot, tmp_path / "wrong.json")
    assert not (tmp_path / "wrong.json").exists()
