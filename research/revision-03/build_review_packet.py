"""Blank human forms for the active revision; never include model outcomes."""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.contracts import load_gold, load_questions

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("csv", "json-intermediate"), default="csv")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a new review package directory")
    data = ROOT / "data/benchmarks/revision-03/final-02"
    questions, gold = load_questions(data / "questions.jsonl"), load_gold(data / "gold.jsonl")
    contracts = {r["question_id"]: r for r in map(json.loads, (data / "contracts.jsonl").read_bytes().splitlines())}
    spec_path = ROOT / "data/benchmarks/revision-02/annotations.json"
    specification = json.loads(spec_path.read_bytes())
    blank = {"reviewer_code": "", "decision": "", "reason": "", "proposed_correction": "", "review_date": ""}
    tables = {"questions-blind": [{"question_id": q.question_id, "question": q.question,
                "independent_interpretation": "", "independent_sql": "", "ambiguities": "", **blank} for q in questions]}
    tables["questions-reference"] = [{"question_id": q.question_id, "question": q.question, "complexity": q.complexity,
        "reference_sql": gold[q.question_id].sql, "column_count": gold[q.question_id].column_count,
        "column_order": gold[q.question_id].column_order, "ordered_rows": gold[q.question_id].ordered,
        "grain": contracts[q.question_id]["grain"], "population": contracts[q.question_id]["population"],
        "measure": contracts[q.question_id]["measure"], "ordering_and_ties": contracts[q.question_id]["ordering_and_ties"],
        "source_urls": "; ".join(contracts[q.question_id]["source_urls"]), "semantic_valid": "", "alternative_sql": "", **blank} for q in questions]
    tables["annotations"] = [{"element_id": a["element_id"], "short": a["short"], "detailed": a["detailed"],
        "source_url": a["source_url"], "factual_valid": "", "redundancy_issue": "", "answer_leakage": "", **blank} for a in specification["annotations"]]
    tables["business-terms"] = [{"term_id": t["term_id"], "name": t["name"], "definition": t["definition"],
        "source_urls": "; ".join(t["sources"]), "rule_supported": "", "critical_exceptions_complete": "", **blank} for t in specification["business_terms"]]
    if args.format == "json-intermediate":
        publish_artifact(args.output / "tables.json", canonical_json({name: {"columns": list(rows[0]), "rows": [list(r.values()) for r in rows]} for name, rows in tables.items()}))
    else:
        for name, rows in tables.items():
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows({key: str(value).lower() if isinstance(value, bool) else value for key, value in row.items()} for row in rows)
            publish_artifact(args.output / (name + ".csv"), stream.getvalue().encode())
    guide = """# Review instrumen revision03

Paket memuat30pertanyaan/gold,106deskripsi dan3aturan domain. Seluruh keputusan dan identitas reviewer masih kosong. Tidak ada prediksi model atau skor EX.

1. Berikan questions-blind.csv dan generation-instruction.txt terlebih dahulu. Reviewer menulis interpretasi sendiri sebelum melihat reference. Baca technical schema dan definisi metadata yang relevan; bedakan pengetahuan yang hanya tersedia pada S3 dari maksud yang masih ambigu sesudah S3 lengkap. Simpan submission tahap pertama dengan hash/tanggal sebenarnya.
2. Berikan questions-reference.csv setelah tahap pertama dikunci. Periksa output bisnis, populasi/grain, filtering, waktu, duplikat, NULL dan rules. Output columns merupakan himpunan yang diminta dalam prose, bukan posisi teknis. Alternatif projection order dan aliases diperbolehkan. Urutan baris diperiksa hanya bila diminta. Baca konvensi ties/top-k pada prompt bersama.
3. Periksa annotations.csv dan business-terms.csv terhadap sumber resmi/executable source. Definisi harus membantu memahami domain secara umum, bukan memuat SQL recipe, gold atau jawaban per soal. Jangan mengganti metadata/soal karena model gagal atau suatu skenario menang.
4. Isi decision dengan accept/revise/reject/uncertain dan berikan alasan. Kolom kosong belum direview. Jika memungkinkan gunakan dua reviewer independen dan adjudication terdokumentasi. Jangan mengarang identitas, tanggal atau approval. Review sesudah generation dicatat sebagai post-run, bukan approval sebelumnya.

Nomor, nama, metrik dan filter yang diminta merupakan maksud laporan, bukan petunjuk SQL. Pertanyaan sengaja tidak memiliki footer schema identifiers. Gold dan kontrak private tidak dikirim ke LLM. Perubahan wording/prompt/metadata memerlukan versi dan generation baru. Gold-only correction setelah review harus menjadi laporan turunan yang dapat diaudit; approval tidak terjadi otomatis karena query berhasil dieksekusi.
"""
    publish_artifact(args.output / "review-guide.md", guide.encode())
    publish_artifact(args.output / "generation-instruction.txt", (ROOT / "prompts/generation-v3.txt").read_bytes())
    sources = [data / name for name in ("questions.jsonl", "gold.jsonl", "contracts.jsonl", "manifest.json")]
    sources += [spec_path, ROOT / "prompts/generation-v3.txt"]
    publish_artifact(args.output / "input-hashes.json", canonical_json({"records": {k: len(v) for k, v in tables.items()},
        "inputs": [{"path": str(p.relative_to(ROOT)), "sha256": sha256_bytes(p.read_bytes())} for p in sources],
        "human_review_complete": False, "model_results_included": False}))
    print(json.dumps({"status": "blank_review_package", "rows": {k: len(v) for k, v in tables.items()}}))


if __name__ == "__main__":
    main()
