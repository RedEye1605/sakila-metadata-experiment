import csv
import json
import shutil

import pytest

from sakila_experiment.annotations import CRITERIA, build_annotation_round, consolidate, rows
from sakila_experiment.artifacts import canonical_json
from test_review_package import fixture


def annotation_fixture(root):
    fixture(root)
    folder = root / "snapshots/candidates-v2/S0"
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_bytes(canonical_json({"payload_file": "schema.json"}))
    (folder / "schema.json").write_bytes(canonical_json({"technical_schema": {"tables": []}}))
    package = root / "package"
    record = build_annotation_round(root, package)
    for reviewer in ("A01", "A02"):
        shutil.copytree(package / reviewer, root / reviewer)
        for path in (root / reviewer).glob("*.csv"): path.chmod(0o644)
    return package, record


def rewrite(path, values):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0])); writer.writeheader(); writer.writerows(values)


def test_independent_templates_and_pending_consolidation_never_approve(tmp_path):
    package, record = annotation_fixture(tmp_path)
    assert record["items_per_annotator"] == 4
    assert record["model_scores_included"] is False
    assert all(r["decision"] == "pending" for r in rows(package / "A01/questions.csv"))
    assert (package / "reference/results/Q001.json").exists()
    result = consolidate(package, tmp_path / "A01", tmp_path / "A02", tmp_path / "consolidated")
    assert result["paired_completed"] == 0 and result["approvals_created"] == 0
    assert all(r["final_decision"] == "pending" for r in rows(tmp_path / "consolidated/adjudication.csv"))


def test_annotation_source_changes_and_incomplete_acceptance_are_rejected(tmp_path):
    package, _ = annotation_fixture(tmp_path)
    path = tmp_path / "A01/questions.csv"
    original = rows(path); changed = [dict(r) for r in original]
    changed[0]["gold_sql"] = "SELECT 2"; rewrite(path, changed)
    with pytest.raises(ValueError, match="Immutable"):
        consolidate(package, tmp_path / "A01", tmp_path / "A02", tmp_path / "bad")
    changed = [dict(r) for r in original]; changed[0]["decision"] = "accepted"; rewrite(path, changed)
    with pytest.raises(ValueError, match="every criterion"):
        consolidate(package, tmp_path / "A01", tmp_path / "A02", tmp_path / "bad")


def test_complete_synthetic_agreement_still_requires_adjudication(tmp_path):
    package, _ = annotation_fixture(tmp_path)
    for reviewer in ("A01", "A02"):
        for kind, criteria in CRITERIA.items():
            path = tmp_path / reviewer / (kind + ".csv"); data = rows(path)
            for row in data:
                row.update({c: "yes" for c in criteria}); row.update(decision="accepted", annotated_at_utc="2026-10-27T10:00:00Z")
            rewrite(path, data)
    result = consolidate(package, tmp_path / "A01", tmp_path / "A02", tmp_path / "consolidated")
    assert result["paired_completed"] == result["resolution_agreements"] == 4
    assert result["approvals_created"] == 0
    assert len(result["submission_sha256"]) == 6
    assert result["adjudication_template_sha256"]
    assert json.loads((tmp_path / "data/private/main.gold.jsonl").read_bytes())["review_status"] == "draft"
