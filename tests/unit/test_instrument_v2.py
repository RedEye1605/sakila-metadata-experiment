import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sakila_experiment.artifacts import sha256_bytes
from sakila_experiment.contracts import DatasetError
from sakila_experiment.instrument import ArtifactReference, BenchmarkManifest, SemanticContract

ROOT = Path(__file__).parents[2]


def test_candidate_contracts_are_private_complete_drafts_with_real_fact_ids():
    directory = ROOT / "data/benchmarks/revision-02"
    facts = {item["fact_id"] for item in json.loads((directory / "facts.json").read_bytes())["facts"]}
    rows = [SemanticContract.model_validate_json(line) for line in (directory / "candidates.contracts.jsonl").read_bytes().splitlines()]
    assert len(rows) == len({row.question_id for row in rows}) == 60
    assert all(set(row.required_fact_ids) <= facts for row in rows)
    assert all(row.human_review_status == "pending" for row in rows)
    altered = rows[0].model_dump()
    altered["fact_availability"][altered["required_fact_ids"][0]].pop("S0")
    with pytest.raises(ValidationError, match="exactly S0-S3"):
        SemanticContract.model_validate(altered)


def test_manifest_rejects_changed_bytes_traversal_and_fake_main_approval(tmp_path):
    path = tmp_path / "input.json"
    path.write_text("{}")
    ref = ArtifactReference(path="input.json", sha256=sha256_bytes(path.read_bytes()))
    assert ref.verified_path(tmp_path) == path
    path.write_text("[]")
    with pytest.raises(DatasetError, match="changed"):
        ref.verified_path(tmp_path)
    for value in ("../input.json", str(path)):
        with pytest.raises(DatasetError, match="escapes"):
            ArtifactReference(path=value, sha256=ref.sha256).verified_path(tmp_path)
    fields = {key: ref.model_dump() for key in ("questions", "gold", "contracts", "annotation_specification", "fact_inventory", "analysis_protocol", "evaluation_protocol", "source_lock", "selection_receipt", "prompt_template", "information_audit", "metadata_snapshots", "reference_validation", "reference_validation_lock", "fixture_specification")}
    fields.update(benchmark_id="revision-02", estimand="metadata-package-domain-information-availability", main_experiment_allowed=True)
    with pytest.raises(ValidationError, match="main_experiment_allowed"):
        BenchmarkManifest.model_validate(fields)


def test_new_authoring_does_not_replace_original_datasets_or_metadata():
    protected = ROOT / "runs/revision-02/protected-inputs.json"
    if not protected.exists():
        pytest.skip("Local original-artifact receipt is intentionally not public")
    for item in json.loads(protected.read_bytes()):
        assert sha256_bytes((ROOT / item["path"]).read_bytes()) == item["sha256"]


def test_detailed_metadata_can_equal_short_without_dropping_coverage():
    old = json.loads((ROOT / "data/annotations/specification.json").read_bytes())
    new = json.loads((ROOT / "data/benchmarks/revision-02/annotations.json").read_bytes())
    assert {a["element_id"] for a in old["annotations"]} == {a["element_id"] for a in new["annotations"]}
    assert len(new["annotations"]) == 106
    elements = {a["element_id"]: a for a in new["annotations"]}
    assert elements["actor.actor_id"]["short"] == elements["actor.actor_id"]["detailed"]
    assert "home store" in elements["customer.store_id"]["detailed"]
    assert {term["term_id"] for term in new["business_terms"]} == {"inventory-availability", "monthly-rewards", "returned-rental-late-component"}
    assert new["status"] == "draft"
