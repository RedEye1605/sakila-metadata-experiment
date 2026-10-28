import importlib.metadata
import platform
from dataclasses import replace

import pytest

from sakila_experiment.artifacts import sha256_bytes
from sakila_experiment.config import InferenceConfig
from sakila_experiment.contracts import DatasetError
from sakila_experiment.experiment.diagnostics import validate_pilot_cases
from sakila_experiment.experiment.runner import RunError, validate_context_backend, validate_reference_database
from sakila_experiment.generation.llama import BackendEvidence
from sakila_experiment.instrument import REFERENCE_VALIDATION_PACKAGES, REFERENCE_VALIDATION_SOURCES, validate_reference_code


def test_pilot_proof_rejects_duplicate_cases_changed_primary_and_vacuous_witnesses():
    fixtures = [f"case{i}" for i in range(8)]
    valid = {"cases": ["baseline", *fixtures], "primary_database_unchanged": True,
             "records": [{"question_id": "P101", "witnesses": {"wrong": [fixtures[0]]}}]}
    validate_pilot_cases(valid, {"P101"}, fixtures)
    for changed in ({**valid, "cases": ["not-declared"] * 9}, {**valid, "primary_database_unchanged": False},
                    {**valid, "records": [{"question_id": "P101", "witnesses": {}}]},
                    {**valid, "records": [{"question_id": "P101", "witnesses": {"wrong": []}}]},
                    {**valid, "records": [{"question_id": "P101", "witnesses": {"wrong": ["not-declared"]}}]}):
        with pytest.raises(DatasetError):
            validate_pilot_cases(changed, {"P101"}, fixtures)


def test_each_reference_proof_must_match_live_content_and_server():
    actual = {"schema_sha256": "schema", "data_sha256": "data", "server": {"version": "8.4"}}
    proof = {"database_schema_sha256": "schema", "database_data_sha256": "data", "mysql_version": "8.4"}
    validate_reference_database(proof, actual)
    for key in proof:
        with pytest.raises(RunError, match="different frozen"):
            validate_reference_database({**proof, key: "stale-pilot-proof"}, actual)


def test_annotation_context_proof_is_bound_to_model_bytes_build_and_template():
    evidence = BackendEvidence("selected", "a" * 64, "revision", 16384, "b" * 64)
    backend = {"build_info": "fixed-build", "chat_template_sha256": "c" * 64}
    proof = {"model_id": "selected", "model_sha256": "a" * 64, "backend_revision": "revision",
             "backend_build_info": "fixed-build", "chat_template_sha256": "c" * 64, "context_tokens": 16384}
    settings = InferenceConfig(model_id="selected")
    validate_context_backend(proof, evidence, backend, settings)
    for key in proof:
        with pytest.raises(RunError, match="selected model"):
            validate_context_backend({**proof, key: "other-model-or-backend"}, evidence, backend, settings)


def test_bootstrap_inspector_and_runtime_version_changes_invalidate_reference_proof(tmp_path):
    hashes = {}
    for relative in REFERENCE_VALIDATION_SOURCES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic source for dependency hash test: " + relative)
        hashes[relative] = sha256_bytes(path.read_bytes())
    proof = {"implementation_sha256": hashes, "python_version": platform.python_version(),
             "package_versions": {name: importlib.metadata.version(name) for name in REFERENCE_VALIDATION_PACKAGES}}
    validate_reference_code(tmp_path, proof)
    for relative in ("src/sakila_experiment/bootstrap.py", "src/sakila_experiment/db/inspect.py"):
        path = tmp_path / relative
        original = path.read_bytes()
        path.write_bytes(original + b"\nchanged")
        with pytest.raises(DatasetError, match="source lock"):
            validate_reference_code(tmp_path, proof)
        path.write_bytes(original)
    with pytest.raises(DatasetError, match="runtime versions"):
        validate_reference_code(tmp_path, {**proof, "python_version": "different"})
