import csv
import json

import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.review import build_review_package


def fixture(root):
    def write(name, value):
        p = root / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(canonical_json(value)); return p
    for scope, prefix in (("main", "Q"), ("pilot", "P")):
        write("data/public/main.questions.jsonl" if scope == "main" else "data/pilot/questions.jsonl",
              {"question_id": prefix + "001", "question": f"Berapa nilai {scope} untuk pengujian sintetis?", "complexity": "simple"})
        write("data/private/main.gold.jsonl" if scope == "main" else "data/pilot/gold.jsonl",
              {"question_id": prefix + "001", "sql": "SELECT 1", "column_count": 1, "review_status": "draft"})
    write("data/annotations/specification.json", {"annotations": [{"element_id": "actor", "short": "Pemeran.", "detailed": "Identitas pemeran film.", "source_url": "https://dev.mysql.com/doc/sakila/en/sakila-structure-tables-actor.html"}],
          "business_terms": [{"term_id": "fixture", "name": "Synthetic term", "definition": "Synthetic definition", "applies_to": ["actor"], "sources": ["https://example.invalid/fixture"]}]})
    result = write("runs/gold/main-draft-01/Q001.result.json", {"column_count": 1, "rows": [[["number", "1"]]]})
    write("runs/gold/main-draft-01/validation.json", {"questions_sha256": sha256_bytes((root / "data/public/main.questions.jsonl").read_bytes()),
          "gold_sha256": sha256_bytes((root / "data/private/main.gold.jsonl").read_bytes()), "records": [{"question_id": "Q001", "result_sha256": sha256_bytes(result.read_bytes())}]})
    return result


def test_review_packet_never_approves_or_changes_inputs(tmp_path):
    fixture(tmp_path)
    path = tmp_path / "data/private/main.gold.jsonl"
    before = path.read_bytes()
    report = build_review_package(tmp_path, tmp_path / "packet")
    assert report["status"] == "pending_human_review" and path.read_bytes() == before
    with (tmp_path / "packet/questions.csv").open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2 and all(row["decision"] == "pending" and not row["reviewer"] for row in rows)
    assert rows[0]["reference_rows"] == "1"


def test_stale_reference_results_are_not_presented_as_current(tmp_path):
    fixture(tmp_path)
    p = tmp_path / "data/private/main.gold.jsonl"
    d = json.loads(p.read_bytes()); d["sql"] = "SELECT 2"; p.write_bytes(canonical_json(d))
    build_review_package(tmp_path, tmp_path / "packet")
    with (tmp_path / "packet/questions.csv").open(encoding="utf-8-sig") as handle:
        row = next(csv.DictReader(handle))
    assert "stale" in row["reference_result"] and not row["reference_rows"]


def test_tampered_reference_result_is_rejected(tmp_path):
    result = fixture(tmp_path)
    result.write_bytes(b"modified")
    with pytest.raises(ValueError, match="result hash mismatch"):
        build_review_package(tmp_path, tmp_path / "packet")
