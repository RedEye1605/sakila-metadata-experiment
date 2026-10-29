from collections import Counter
import json

import httpx
import pytest

from sakila_experiment.contracts import DatasetError, Question
from sakila_experiment.experiment.candidate_pilot import candidate_schedule, capability_decision, load_candidate_bundle, validate_candidate_sampler
from sakila_experiment.config import InferenceConfig
from sakila_experiment.generation.llama import BackendEvidence, CheckedPrompt, LlamaClient
from test_generation import prompt


def inputs():
    questions = tuple(Question(question_id=f"P{i}", question=f"Pertanyaan pilot berbeda nomor {i}?", complexity="medium")
                      for i in range(301, 313))
    protocol = dict(repetitions=2, scenario_ids=["S0", "S1", "S2", "S3"], question_count=12,
                    assigned_trials_per_candidate=96, order_seed=19, inference_seed_base=29)
    return questions, protocol


def test_capability_schedule_is_paired_and_reproducible():
    q, p = inputs()
    a = candidate_schedule(q, p)
    assert a == candidate_schedule(tuple(reversed(q)), p)
    assert len({x.trial_id for x in a}) == 96
    assert Counter(x.scenario_id for x in a) == dict.fromkeys(p["scenario_ids"], 24)
    for question in q:
        for repetition in (1, 2):
            assert len({x.inference_seed for x in a if x.question_id == question.question_id
                        and x.repetition_id == repetition}) == 1
    assert a != candidate_schedule(q, {**p, "order_seed": 20})


@pytest.mark.parametrize("change", [dict(repetitions=5), dict(question_count=30), dict(assigned_trials_per_candidate=600)])
def test_capability_design_cannot_become_main(change):
    q, p = inputs()
    with pytest.raises(DatasetError):
        candidate_schedule(q, {**p, **change})


def evidence(s0_correct=0, domain_correct=12):
    q, p = inputs()
    attributes = {x.question_id: {"primary_need": "domain_integration" if i >= 6 else "schema_mapping",
                                "semantic_family": f"rule-{(i - 6) // 2}" if i >= 6 else x.question_id}
                  for i, x in enumerate(q)}
    rows = []
    seen_domain = 0
    for assignment in candidate_schedule(q, p):
        success = True
        if assignment.scenario_id == "S3" and attributes[assignment.question_id]["primary_need"] == "domain_integration":
            success = seen_domain < domain_correct
            seen_domain += 1
        rows.append(dict(question_id=assignment.question_id, scenario_id=assignment.scenario_id,
                         repetition_id=assignment.repetition_id,
                         execution_accuracy=(s0_correct if assignment.scenario_id == "S0" else int(success)),
                         execution_status="success"))
    return rows, attributes


def test_admission_never_uses_baseline_gain_or_significance():
    low, a = evidence(s0_correct=0)
    high, _ = evidence(s0_correct=1)
    assert capability_decision(low, a) == capability_decision(high, a)
    assert capability_decision(high, a)["status"] == "capability_pass"
    assert capability_decision(high, a)["main_experiment_allowed"] is False


def test_pilot_cannot_pass_on_easy_tasks_without_domain_capability():
    rows, attributes = evidence(domain_correct=0)
    result = capability_decision(rows, attributes)
    assert result["status"] == "capability_not_demonstrated"
    assert not result["checks"]["S3_domain_correct_at_least6of12"]


def test_incomplete_capability_is_not_reported():
    rows, attributes = evidence()
    with pytest.raises(DatasetError):
        capability_decision(rows[:-1], attributes)


def test_duplicate_or_infrastructure_observations_cannot_pass_admission():
    rows, attributes = evidence()
    with pytest.raises(DatasetError):
        capability_decision(rows[:-1] + [rows[0]], attributes)
    rows[0]["execution_accuracy"] = None
    with pytest.raises(DatasetError):
        capability_decision(rows, attributes)


def test_candidate_evidence_cannot_claim_main_or_human_approval(tmp_path):
    p = tmp_path / "manifest.json"
    for changes in ({"main_experiment_allowed": True}, {"human_review_complete": True}):
        body = dict(status="frozen_AI_checked_engineering_pilot", main_experiment_allowed=False, human_review_complete=False)
        p.write_text(json.dumps(body | changes))
        with pytest.raises(DatasetError, match="impersonate"):
            load_candidate_bundle(tmp_path, p)


@pytest.mark.parametrize("final", ["SELECT 1", None])
def test_server_reasoning_is_preserved_but_never_substituted_for_final_sql(final):
    body = {"choices": [{"message": {"content": final, "reasoning_content": "Synthetic internal fixture text"},
                           "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 90}}
    transport = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))
    evidence = BackendEvidence("fixture-model", "a" * 64, "fixture", 16384, "b" * 64)
    try:
        with LlamaClient(InferenceConfig(model_id="fixture-model"), evidence, client=transport) as client:
            response = client.generate(CheckedPrompt(prompt(), 10, evidence), 123)
        assert response.text == final
        assert response.response_valid is (final is not None)
        assert response.output_tokens == 90
        assert response.raw_response["choices"][0]["message"]["reasoning_content"] == "Synthetic internal fixture text"
    finally:
        transport.close()


def sampler_evidence():
    expected = dict(seed=2026102903, temperature=.6, top_p=.95, top_k=20, min_p=0.0,
                    repeat_penalty=1.0, max_tokens=4096)
    manifest = dict(inference_config=dict(temperature=.6, top_p=.95, top_k=20, max_output_tokens=4096),
                    model_version_or_hash="a"*64, backend_evidence_sha256="b"*64)
    rows = [dict(schedule_position=96, trial_id="P301-S3-r02", inference_seed=2026102903)]
    proof = dict(status="sampler_seed_cache_verified", model_sha256="a"*64,
                 backend_evidence_sha256="b"*64, pilot_manifest_sha256="c"*64,
                 source_trial="P301-S3-r02", generation_requests=0, expected_request_settings=expected,
                 observed_slots=[dict(is_processing=False, n_prompt_tokens_cache=0, params=expected.copy())])
    return proof, manifest, rows


@pytest.mark.parametrize("field,bad", [("status","NOT_VERIFIED"), ("model_sha256","d"*64),
    ("backend_evidence_sha256","d"*64), ("pilot_manifest_sha256","d"*64),
    ("source_trial","other-trial"), ("generation_requests",1)])
def test_stale_existing_sampler_cannot_authorize_capability(field, bad):
    proof, manifest, rows = sampler_evidence()
    proof[field] = bad
    with pytest.raises(DatasetError, match="Sampler"):
        validate_candidate_sampler(proof, manifest, rows, "c"*64)


def test_candidate_sampler_checks_exact_large_seed_and_observed_slot():
    proof, manifest, rows = sampler_evidence()
    validate_candidate_sampler(proof, manifest, rows, "c"*64)
    proof["observed_slots"][0]["params"]["seed"] += 1
    with pytest.raises(DatasetError, match="Observed"):
        validate_candidate_sampler(proof, manifest, rows, "c"*64)
