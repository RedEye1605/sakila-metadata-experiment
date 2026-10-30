from copy import deepcopy
import json

import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.contracts import DatasetError
from sakila_experiment.instrument import validate_permutation_witnesses


def proof(tmp_path):
    lock = tmp_path / "input-lock.json"
    lock.write_bytes(canonical_json({"synthetic_test_only": True}))
    row = {"question_id": "Q001", "fixture_id": "baseline", "input_lock_sha256": sha256_bytes(lock.read_bytes()),
           "author_a_status": "success", "author_b_status": "success", "reference_agreement": True,
           "mutations": [{"mutation_id": "wrong", "execution_status": "success", "semantic_difference_observed": True}]}
    case = tmp_path / "baseline/comparisons.json"
    case.parent.mkdir()
    case.write_bytes(canonical_json([row]))
    checks = {"cases": ["baseline"], "input_lock_sha256": sha256_bytes(lock.read_bytes()),
              "case_evidence_sha256": {"baseline": sha256_bytes(case.read_bytes())},
              "records": [{"question_id": "Q001", "witnesses": {"wrong": ["baseline"]}}]}
    return tmp_path / "summary.json", lock, checks, {"Q001": [{"mutation_id": "wrong"}]}, {"Q001"}


def test_only_actual_hash_bound_declared_witnesses_are_accepted(tmp_path):
    args = proof(tmp_path)
    validate_permutation_witnesses(*args)


@pytest.mark.parametrize("fault", ["unknown_mutant", "missing_mutant", "unknown_case", "duplicate_case", "duplicate_question", "stale_lock"])
def test_summary_cannot_substitute_invented_or_incomplete_witnesses(tmp_path, fault):
    path, lock, checks, mutants, identifiers = proof(tmp_path)
    if fault == "unknown_mutant": checks["records"][0]["witnesses"] = {"invented": ["baseline"]}
    elif fault == "missing_mutant": mutants["Q001"].append({"mutation_id": "reverse-ties"})
    elif fault == "unknown_case": checks["records"][0]["witnesses"]["wrong"] = ["not-a-declared-fixture"]
    elif fault == "duplicate_case": checks["records"][0]["witnesses"]["wrong"] = ["baseline", "baseline"]
    elif fault == "duplicate_question": checks["records"].append(deepcopy(checks["records"][0]))
    elif fault == "stale_lock": lock.write_bytes(canonical_json({"different_synthetic_test": True}))
    with pytest.raises(DatasetError):
        validate_permutation_witnesses(path, lock, checks, mutants, identifiers)


@pytest.mark.parametrize("fault", ["changed_case_file", "changed_case_lock", "duplicate_case_question", "missing_case_mutant", "failed_mutant", "failed_reference"])
def test_per_case_evidence_is_checked_instead_of_trusting_summary_flags(tmp_path, fault):
    path, lock, checks, mutants, identifiers = proof(tmp_path)
    case = tmp_path / "baseline/comparisons.json"
    rows = json.loads(case.read_bytes())
    if fault == "changed_case_file": rows[0]["new_field"] = "unbound change"
    elif fault == "changed_case_lock": rows[0]["input_lock_sha256"] = "0" * 64
    elif fault == "duplicate_case_question": rows.append(deepcopy(rows[0]))
    elif fault == "missing_case_mutant": rows[0]["mutations"] = []
    elif fault == "failed_mutant": rows[0]["mutations"][0]["execution_status"] = "model_error"
    elif fault == "failed_reference": rows[0]["reference_agreement"] = False
    case.write_bytes(canonical_json(rows))
    if fault != "changed_case_file":
        checks["case_evidence_sha256"]["baseline"] = sha256_bytes(case.read_bytes())
    with pytest.raises(DatasetError):
        validate_permutation_witnesses(path, lock, checks, mutants, identifiers)
