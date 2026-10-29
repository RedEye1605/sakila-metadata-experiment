import json
from types import SimpleNamespace
from pathlib import Path

import pytest
from pydantic import ValidationError

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.contracts import DatasetError
from sakila_experiment.experiment.direct_main import validate_direct_amendment, validate_main_sampler
from sakila_experiment.experiment.execution_review import stimulus_scope
from sakila_experiment.instrument import ArtifactReference, BenchmarkManifest, read_manifest, validate_instrument

ROOT = Path(__file__).resolve().parents[2]
SELECTED = "data/benchmarks/revision-03/qwen35-9b-execution-01/manifest.json"


@pytest.fixture
def direct_case(tmp_path):
    def artifact(name, value):
        path = tmp_path / name
        path.write_bytes(canonical_json(value))
        return ArtifactReference(path=name, sha256=sha256_bytes(path.read_bytes()))
    names = ["questions", "gold", "contracts", "annotation_specification", "fact_inventory", "analysis_protocol",
             "evaluation_protocol", "source_lock", "selection_receipt", "prompt_template", "information_audit",
             "metadata_snapshots", "reference_validation", "reference_validation_lock", "fixture_specification"]
    fields = {name: artifact(name + ".json", {"synthetic_test_only": name}) for name in names}
    original = BenchmarkManifest(benchmark_id="synthetic-original", estimand="metadata-package-domain-information-availability",
        status="frozen_user_attested", main_experiment_allowed=True, human_review_status="user_attested_complete",
        execution_review=artifact("review.json", {"synthetic_review_only": True}),
        smoke_test=artifact("smoke.json", {"synthetic_smoke_only": True}), **fields)
    original_ref = artifact("original.json", original.model_dump(mode="json"))
    model = json.loads((ROOT / "configs/models/qwen35-9b-q4km.json").read_bytes())
    document = {"amendment_version": 1, "status": "user_authorized_direct_main", "source": "direct_user_statement",
        "statement": "Synthetic authorization fixture only; this is never an actual researcher approval.",
        "recorded_at_utc": "2026-10-29T12:00:00Z", "upstream_model": "Qwen/Qwen3.5-9B",
        "selection_basis": "researcher_selected_after_prior_results", "source_instrument": original_ref.model_dump(),
        "model_specification": artifact("model.json", model).model_dump(),
        "configuration": artifact("config.json", {"synthetic_config": True}).model_dump(),
        "compose": artifact("compose.json", {"synthetic_compose": True}).model_dump(),
        "prior_main_manifest": artifact("prior-main.json", {"mode": "main", "trial_count": 600}).model_dump(),
        "prior_candidate_completion": artifact("prior-candidate.json", {"status": "candidate_pipeline_complete"}).model_dump(),
        "scope": stimulus_scope(original),
        "stimulus_identity": sha256_bytes(canonical_json(stimulus_scope(original))),
        "backend_command": ["--model", "/models/synthetic.gguf"], "capability_pilot": "waived_by_researcher",
        "generation_smoke": "waived_by_researcher", "preflight_generation_requests": 0, "main_trial_count": 600,
        "sampler_policy": "verify_each_completed_main_request_without_new_generation",
        "monitoring": "researcher_only_after_launch", "actual_results_publication": "local_only",
        "limitations": ["Synthetic test data.", "No actual review or generation."]}
    amendment_ref = artifact("amendment.json", document)
    instrument = original.model_copy(update={"benchmark_id": "synthetic-replication", "smoke_test": None,
                                              "execution_amendment": amendment_ref})
    return tmp_path, instrument, instrument.paths(tmp_path), document


def test_direct_amendment_preserves_reviewed_stimuli_and_prior_history(direct_case):
    root, instrument, paths, document = direct_case
    amendment = validate_direct_amendment(root, instrument, paths)
    original, _ = read_manifest(root, root / document["source_instrument"]["path"])
    assert stimulus_scope(instrument) == stimulus_scope(original)
    assert instrument.smoke_test is None
    assert amendment.preflight_generation_requests == 0
    assert amendment.main_trial_count == 600
    assert amendment.selection_basis == "researcher_selected_after_prior_results"
    assert amendment.generation_smoke == "waived_by_researcher"


@pytest.mark.parametrize("fault", ["scope", "time", "extra", "pilot_claim", "wrong_model", "prior_history"])
def test_direct_amendment_rejects_unbound_or_false_claims(direct_case, fault):
    root, instrument, paths, document = direct_case
    if fault == "scope":
        document["scope"].pop("gold")
    elif fault == "time":
        document["recorded_at_utc"] = "2026-10-29T12:00:00"
    elif fault == "extra":
        document["skip_sql_safety"] = True
    elif fault == "pilot_claim":
        document["capability_pilot"] = "passed"
    else:
        name = "model_specification" if fault == "wrong_model" else "prior_candidate_completion"
        p = root / document[name]["path"]
        value = json.loads(p.read_bytes())
        if fault == "wrong_model":
            value["model_id"] = "unsloth/Qwen3.5-4B-GGUF"
        else:
            value["status"] = "interrupted"
        p.write_bytes(canonical_json(value))
        document[name]["sha256"] = sha256_bytes(p.read_bytes())
    paths["execution_amendment"].write_bytes(canonical_json(document))
    with pytest.raises((DatasetError, ValidationError)):
        validate_direct_amendment(root, instrument, paths)


def test_direct_amendment_does_not_replace_original_default_smoke_gate():
    old = json.loads((ROOT / "data/benchmarks/revision-03/execution-01/manifest.json").read_bytes())
    assert BenchmarkManifest.model_validate(old).execution_amendment is None
    old["smoke_test"] = None
    with pytest.raises(ValidationError):
        BenchmarkManifest.model_validate(old)


def test_smoke_and_waiver_cannot_both_be_claimed():
    value = json.loads((ROOT / SELECTED).read_bytes())
    value["smoke_test"] = {"path": "synthetic-smoke.json", "sha256": "a" * 64}
    with pytest.raises(ValidationError):
        BenchmarkManifest.model_validate(value)


@pytest.mark.integration
def test_actual_amended_instrument_validates_offline_without_generation():
    result = validate_instrument(ROOT, ROOT / SELECTED)
    assert result["generation_requests"] == 0 and result["question_count"] == 30


@pytest.fixture
def sampler_case():
    settings = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "max_output_tokens": 4096}
    manifest = {"inference_config": settings, "model_version_or_hash": "a" * 64, "backend_evidence_sha256": "b" * 64}
    row = {"trial_id": "Q101-S3-r01", "inference_seed": 2026102903}
    expected = {"seed": row["inference_seed"], "temperature": 0.6, "top_p": 0.95, "top_k": 20,
                "min_p": 0.0, "repeat_penalty": 1.0, "max_tokens": 4096}
    proof = {"status": "main_sampler_seed_cache_verified", "model_sha256": "a" * 64,
             "backend_evidence_sha256": "b" * 64, "manifest_sha256": "c" * 64,
             "source_trial": row["trial_id"], "source_outcome_sha256": sha256_bytes(canonical_json(row)),
             "generation_requests": 0, "expected_request_settings": expected,
             "observed_slots": [{"is_processing": False, "n_prompt_tokens_cache": 0, "params": dict(expected)}]}
    return proof, manifest, row


def test_main_sampler_accepts_float32_serialization_noise_but_exact_integer_seed(sampler_case):
    proof, manifest, row = sampler_case
    proof["observed_slots"][0]["params"]["temperature"] = 0.60000002384
    validate_main_sampler(proof, manifest, row, "c" * 64)
    proof["observed_slots"][0]["params"]["seed"] += 1
    with pytest.raises(DatasetError):
        validate_main_sampler(proof, manifest, row, "c" * 64)


@pytest.mark.parametrize("fault", ["status", "model", "backend", "manifest", "trial", "payload", "settings", "cache", "active", "slots", "nan"])
def test_main_sampler_rejects_stale_cached_or_wrong_request_proof(sampler_case, fault):
    proof, manifest, row = sampler_case
    if fault == "status": proof["status"] = "unverified"
    elif fault == "model": proof["model_sha256"] = "d" * 64
    elif fault == "backend": proof["backend_evidence_sha256"] = "d" * 64
    elif fault == "manifest": proof["manifest_sha256"] = "d" * 64
    elif fault == "trial": proof["source_trial"] = "Q102-S3-r01"
    elif fault == "payload": row["execution_accuracy"] = 1
    elif fault == "settings": proof["expected_request_settings"]["max_tokens"] = 1024
    elif fault == "cache": proof["observed_slots"][0]["n_prompt_tokens_cache"] = 5
    elif fault == "active": proof["observed_slots"][0]["is_processing"] = True
    elif fault == "slots": proof["observed_slots"] = []
    else: proof["observed_slots"][0]["params"]["temperature"] = float("nan")
    with pytest.raises(DatasetError):
        validate_main_sampler(proof, manifest, row, "c" * 64)


def test_sampler_observation_uses_only_get_and_durable_completed_response(tmp_path, monkeypatch):
    import httpx
    from sakila_experiment.config import AppConfig, InferenceConfig
    from sakila_experiment.experiment import direct_main
    from sakila_experiment.experiment.ledger import Ledger
    from sakila_experiment.experiment.schedule import TrialAssignment

    config = AppConfig(project_root=tmp_path, inference=InferenceConfig(model_id="synthetic-qwen", temperature=0.6, top_k=20, max_output_tokens=4096))
    assignment = TrialAssignment("Q101-S3-r01", "Q101", "simple", "S3", 1, 2026102903, 1)
    manifest = {"mode": "main", "experiment_id": "synthetic-no-inference", "execution_amendment_sha256": "d" * 64,
                "inference_config": config.inference.model_dump(mode="json"),
                "model_version_or_hash": "a" * 64, "backend_evidence_sha256": "b" * 64}
    (tmp_path / "manifest.json").write_bytes(canonical_json(manifest))
    row = {"trial_id": assignment.trial_id, "inference_seed": assignment.inference_seed,
           "model_version_or_hash": "a" * 64, "inference_config": manifest["inference_config"], "execution_accuracy": 0}
    with Ledger(tmp_path / "ledger.sqlite3") as ledger:
        ledger.register(manifest["experiment_id"], manifest, (assignment,))
        attempt = ledger.start_attempt(manifest["experiment_id"], assignment.trial_id)
        ledger.record_response(manifest["experiment_id"], assignment.trial_id, attempt, {"synthetic_response": True})
        ledger.finish_trial(manifest["experiment_id"], assignment.trial_id, attempt, row)
    monkeypatch.setattr(direct_main, "load_backend_evidence", lambda _: (SimpleNamespace(model_sha256="a" * 64, verification_artifact_sha256="b" * 64), {}))
    monkeypatch.setattr(direct_main, "check_live_backend", lambda *_: None)
    calls = []
    expected = {"seed": assignment.inference_seed, "temperature": 0.6, "top_p": 0.95, "top_k": 20,
                "min_p": 0.0, "repeat_penalty": 1.0, "max_tokens": 4096}
    def handler(request):
        calls.append((request.method, request.url.path))
        assert calls[-1] == ("GET", "/slots")
        return httpx.Response(200, json=[{"is_processing": False, "n_prompt_tokens_cache": 0, "params": expected}])
    client_type = httpx.Client
    monkeypatch.setattr(direct_main.httpx, "Client", lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    proof = direct_main.verify_main_sampler(config, tmp_path / "unused", tmp_path, assignment.trial_id)
    assert proof["generation_requests"] == 0
    direct_main.verify_main_sampler(config, tmp_path / "unused", tmp_path, assignment.trial_id)
    assert calls == [("GET", "/slots")]
