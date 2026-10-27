import json

import pytest

from sakila_experiment.annotations import CRITERIA, consolidate, rows
from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.evaluation.reevaluate import generation_signature, validate_adjudication
from test_annotations import annotation_fixture, rewrite


def test_reference_only_reevaluation_requires_bound_complete_human_records(tmp_path):
    package, _ = annotation_fixture(tmp_path)
    inputs = json.loads((package / "manifest.json").read_bytes())["source_input_sha256"]
    manifest = {"questions_sha256": inputs["data/public/main.questions.jsonl"], "gold_sha256": inputs["data/private/main.gold.jsonl"],
                "model_version_or_hash": "m", "inference_config": {}, "prompt_template_sha256": "p", "database_schema_sha256": "s",
                "database_data_sha256": "d", "snapshots": {"snapshot_sha256": {"S0": "s0"}}}
    gold = tmp_path / "corrected.jsonl"; gold.write_text("synthetic replacement reference\n")
    for reviewer in ("A01", "A02"):
        for kind, criteria in CRITERIA.items():
            path = tmp_path / reviewer / (kind + ".csv"); data = rows(path)
            for row in data:
                row.update({c: "yes" for c in criteria}); row.update(decision="accepted", annotated_at_utc="2026-10-27T10:00:00Z")
            rewrite(path, data)
    output = tmp_path / "consolidated"
    consolidate(package, tmp_path / "A01", tmp_path / "A02", output)
    adjudication = output / "adjudication.csv"; adjudication.chmod(0o644)
    receipt = {"status": "adjudicated", "reviewers": ["A01", "A02"], "adjudicator": "synthetic-test-only", "adjudicated_at_utc": "2026-10-27T12:00:00Z",
               "generation_signature": generation_signature(manifest), "gold_sha256": sha256_bytes(gold.read_bytes()),
               "review_package_sha256": sha256_bytes((package / "manifest.json").read_bytes()), "adjudication_sha256": sha256_bytes(adjudication.read_bytes())}
    with pytest.raises(ValueError, match="final human"):
        validate_adjudication(manifest, receipt, gold, package, adjudication)
    data = rows(adjudication)
    for row in data:
        row.update(final_decision="accepted", adjudicator="synthetic-test-only", rationale="Synthetic validation case", adjudicated_at_utc="2026-10-27T12:00:00Z")
    rewrite(adjudication, data); receipt["adjudication_sha256"] = sha256_bytes(adjudication.read_bytes())
    validate_adjudication(manifest, receipt, gold, package, adjudication)
    receipt["adjudication_sha256"] = "bad"
    with pytest.raises(ValueError, match="receipt"):
        validate_adjudication(manifest, receipt, gold, package, adjudication)
