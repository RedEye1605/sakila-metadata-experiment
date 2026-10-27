"""Prepare human review artifacts without modifying or approving research data."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .artifacts import canonical_json, publish_artifact, sha256_bytes
from .contracts import load_gold, load_questions


def write_csv(path: Path, rows: list[dict]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    publish_artifact(path, buffer.getvalue().encode("utf-8-sig"))


def build_review_package(root: Path, output: Path, *, main_results: Path | None = None, pilot_results: Path | None = None) -> dict:
    inputs, items = {}, []
    guide = ["# Paket review ilmiah", "", "Status: **draft, belum disetujui**. Reviewer: peneliti bersama dosen/rekan. Tidak ada persetujuan otomatis dari hasil eksekusi atau EX pilot.", "",
             "## Cara meninjau", "", "Salin CSV ke directory kerja reviewer; artifact paket ini tidak ditimpa. Isi decision dengan accepted, revise, atau rejected; tulis rationale, reviewer, dan reviewed_at_utc. Keputusan CSV merupakan catatan review, bukan perubahan otomatis pada dataset atau approval gate.", "",
             "Untuk setiap soal, periksa makna, kolom yang diminta, grain agregasi, JOIN, duplikasi, NULL, urutan, tie-breaking dan kesesuaian rubric. Bedakan keberhasilan eksekusi dari kebenaran semantik. Periksa paraphrase pilot terhadap semua soal utama; kesamaan struktur SQL saja tidak berarti soal identik.", "",
             "Untuk anotasi, periksa sumber, satuan, nullability, peran relasi dan konteks bisnis. S1/S2 harus mencakup elemen sama; S3 mempertahankan S2. Tolak SQL solusi, petunjuk spesifik soal, atau aturan bisnis tanpa dasar. Jangan mengubah soal agar model mendapat skor lebih tinggi.", "",
             "Setelah koreksi disepakati, buat dataset/specification versi baru, validasi ulang referensi dan snapshots yang terpengaruh, lalu catat approval untuk hash final. Persetujuan statistik masih menunggu bimbingan.", ""]
    for scope, questions_name, gold_name, results in (
        ("main", "data/public/main.questions.jsonl", "data/private/main.gold.jsonl", "runs/gold/main-draft-01"),
        ("pilot", "data/pilot/questions.jsonl", "data/pilot/gold.jsonl", "runs/gold/pilot-draft-01"),
    ):
        questions, gold = load_questions(root / questions_name), load_gold(root / gold_name)
        results_directory = (main_results if scope == "main" else pilot_results) or root / results
        validation_path = results_directory / "validation.json"
        validated = json.loads(validation_path.read_bytes()) if validation_path.is_file() else {}
        current_results = (validated.get("questions_sha256") == sha256_bytes((root / questions_name).read_bytes())
                           and validated.get("gold_sha256") == sha256_bytes((root / gold_name).read_bytes()))
        result_hashes = {r["question_id"]: r["result_sha256"] for r in validated.get("records", [])} if current_results else {}
        if current_results:
            inputs[str(validation_path.relative_to(root)) if validation_path.is_relative_to(root) else str(validation_path)] = sha256_bytes(validation_path.read_bytes())
        if {q.question_id for q in questions} != gold.keys():
            raise ValueError("Question and gold IDs differ; review package not created")
        for name in (questions_name, gold_name):
            inputs[name] = sha256_bytes((root / name).read_bytes())
        for question in questions:
            reference = gold[question.question_id]
            result_path = results_directory / (question.question_id + ".result.json")
            result = None
            if question.question_id in result_hashes and result_path.is_file():
                data = result_path.read_bytes()
                if sha256_bytes(data) != result_hashes[question.question_id]:
                    raise ValueError("Reference result hash mismatch; validate gold before creating a review package")
                result = json.loads(data)
            result_name = str(result_path.relative_to(root)) if result_path.is_relative_to(root) else str(result_path)
            if result is not None:
                inputs[result_name] = sha256_bytes(result_path.read_bytes())
            items.append({"scope": scope, "question_id": question.question_id, "question": question.question,
                          "complexity": question.complexity, "gold_sql": reference.sql, "column_count": reference.column_count,
                          "ordered": reference.ordered, "approximate_columns": json.dumps(reference.approximate_columns),
                          "reference_result": result_name if result else "not available or stale; validate gold again",
                          "reference_rows": len(result["rows"]) if result else "", "current_status": reference.review_status,
                          "decision": "pending", "rationale": "", "reviewer": "", "reviewed_at_utc": ""})
            guide += [f"## {question.question_id} ({scope}, {question.complexity})", "", question.question, "", "```sql", reference.sql, "```", "",
                      f"Kontrak: {reference.column_count} kolom; ordered={reference.ordered}; approximate columns={reference.approximate_columns}.", ""]
            if result:
                guide += ["Cuplikan hasil referensi bertipe (maksimum 3 baris; hasil lengkap tersedia pada reference_result di CSV):", "", "```json", json.dumps(result["rows"][:3], ensure_ascii=False), "```", ""]
    spec_path = root / "data/annotations/specification.json"
    specification = json.loads(spec_path.read_bytes())
    inputs["data/annotations/specification.json"] = sha256_bytes(spec_path.read_bytes())
    annotations = [{"element_id": a["element_id"], "short": a["short"], "detailed": a["detailed"], "source": a["source_url"],
                    "decision": "pending", "rationale": "", "reviewer": "", "reviewed_at_utc": ""} for a in specification["annotations"]]
    terms = [{"term_id": t["term_id"], "name": t["name"], "definition": t["definition"], "applies_to": ", ".join(t["applies_to"]),
              "sources": ", ".join(t["sources"]), "decision": "pending", "rationale": "", "reviewer": "", "reviewed_at_utc": ""} for t in specification["business_terms"]]
    write_csv(output / "questions.csv", items)
    write_csv(output / "annotations.csv", annotations)
    write_csv(output / "business-terms.csv", terms)
    publish_artifact(output / "review-guide.md", ("\n".join(guide).rstrip() + "\n").encode())
    report = {"format_version": 1, "status": "pending_human_review", "questions": len(items), "annotations": len(annotations),
              "business_terms": len(terms), "input_sha256": inputs, "main_experiment_allowed": False,
              "reviewers": "Researcher with supervisor or peer; identities and decisions not yet supplied"}
    publish_artifact(output / "manifest.json", canonical_json(report))
    return report
