import json
from types import SimpleNamespace

import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.config import AppConfig
from sakila_experiment.contracts import DatasetError
from sakila_experiment.experiment.execution_review import REVIEW_SCOPE, stimulus_scope, validate_execution_review
from sakila_experiment.experiment.runner import RunError, _build_inputs
from sakila_experiment.instrument import ArtifactReference


def attestation(tmp_path):
    fields, paths = {}, {}
    for name in REVIEW_SCOPE:
        path = tmp_path / (name + ".json")
        value = {"snapshot_sha256": {s: "a" * 64 for s in ("S0", "S1", "S2", "S3")}} if name == "metadata_snapshots" else {"synthetic_test_only": name}
        path.write_bytes(canonical_json(value))
        fields[name] = ArtifactReference(path=path.name, sha256=sha256_bytes(path.read_bytes()))
        paths[name] = path
    path = tmp_path / "review.json"
    manifest = SimpleNamespace(**fields, execution_review=ArtifactReference(path=path.name, sha256="b" * 64))
    review = {"status": "user_attested_complete", "source": "direct_user_statement", "statement": "Synthetic researcher declaration for tests only",
              "recorded_at_utc": "2026-10-29T00:00:00Z", "scope": stimulus_scope(manifest),
              "snapshot_sha256": json.loads(paths["metadata_snapshots"].read_bytes())["snapshot_sha256"],
              "reviewer_identity_status": "pending_user_entry", "reviewer_names": [], "review_date_utc": None}
    path.write_bytes(canonical_json(review));paths["execution_review"] = path
    return manifest, paths, review


def test_researcher_statement_preserves_unprovided_reviewer_details(tmp_path):
    manifest, paths, _ = attestation(tmp_path)
    review = validate_execution_review(tmp_path, manifest, paths)
    assert review["reviewer_names"] == [] and review["review_date_utc"] is None
    assert review["reviewer_identity_status"] == "pending_user_entry"


@pytest.mark.parametrize("fault", ["scope", "snapshot", "missing_statement", "invented_provided_status", "changed_bytes"])
def test_review_cannot_authorize_unbound_or_unexplained_inputs(tmp_path, fault):
    manifest, paths, review = attestation(tmp_path)
    if fault == "scope": review["scope"].pop("gold")
    elif fault == "snapshot": review["snapshot_sha256"]["S0"] = "c" * 64
    elif fault == "missing_statement": review["statement"] = ""
    elif fault == "invented_provided_status": review["reviewer_identity_status"] = "provided"
    else: paths["gold"].write_bytes(b"changed unreviewed bytes")
    paths["execution_review"].write_bytes(canonical_json(review))
    with pytest.raises(DatasetError): validate_execution_review(tmp_path, manifest, paths)


def test_engineering_smoke_cannot_bypass_legacy_review_without_a_manifest(tmp_path):
    with pytest.raises(RunError, match="versioned user-attested"):
        _build_inputs(AppConfig(project_root=tmp_path), tmp_path, tmp_path / "backend", mode="engineering_smoke")
    assert not list(tmp_path.iterdir())
