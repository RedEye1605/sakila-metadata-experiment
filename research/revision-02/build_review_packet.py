"""Reproducible flat review forms; source data and blank decisions stay separate."""
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
    parser.add_argument("--selection-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("csv", "json-intermediate"), default="csv")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a new review packet directory")
    selection = args.selection_directory
    data = ROOT / "data/benchmarks/revision-02"
    questions, gold = load_questions(selection / "questions.jsonl"), load_gold(selection / "gold.jsonl")
    contracts = {row["question_id"]: row for row in map(json.loads, (selection / "contracts.jsonl").read_bytes().splitlines())}
    profiles = {row["question_id"]: row for row in json.loads((selection / "profiles.json").read_bytes())}
    specification = json.loads((data / "annotations.json").read_bytes())
    pilot_questions, pilot_gold = load_questions(data / "pilot.questions.jsonl"), load_gold(data / "pilot.gold-a.jsonl")
    blanks = {"reviewer_code": "", "decision": "", "reason": "", "proposed_correction": "", "review_date": ""}
    tables = {}
    tables["questions-blind"] = [{"question_id": q.question_id, "question": q.question,
                                  "independent_interpretation": "", "independent_sql": "", "ambiguities": "", **blanks} for q in questions]
    tables["questions-reference"] = [{"question_id": q.question_id, "question": q.question, "complexity": q.complexity,
        "spider_level": profiles[q.question_id]["spider_level"], "component1": profiles[q.question_id]["component1"],
        "component2": profiles[q.question_id]["component2"], "others": profiles[q.question_id]["others"],
        "reference_sql": gold[q.question_id].sql, "column_count": gold[q.question_id].column_count,
        "ordered": str(gold[q.question_id].ordered).lower(), "grain": contracts[q.question_id]["grain"],
        "population": contracts[q.question_id]["population"], "required_fact_ids": "; ".join(contracts[q.question_id]["required_fact_ids"]),
        "zero_and_null_policy": contracts[q.question_id]["zero_and_null_policy"],
        "duplicate_policy": contracts[q.question_id]["duplicate_policy"],
        "ordering_and_ties": contracts[q.question_id]["ordering_and_ties"],
        "numeric_policy": contracts[q.question_id]["numeric_policy"],
        "independent_review_notes": "; ".join(contracts[q.question_id].get("review_notes", [])),
        "source_urls": "; ".join(contracts[q.question_id]["source_urls"]),
        "semantic_valid": "", "complexity_valid": "", "alternative_sql": "", **blanks} for q in questions]
    tables["annotations"] = [{"element_id": a["element_id"], "short": a["short"], "detailed": a["detailed"],
                              "source_url": a["source_url"], "factual_valid": "", "redundancy_issue": "", "answer_leakage": "", **blanks}
                              for a in specification["annotations"]]
    tables["business-terms"] = [{"term_id": term["term_id"], "name": term["name"], "definition": term["definition"],
        "applies_to": "; ".join(term["applies_to"]), "source_urls": "; ".join(term["sources"]),
        "executable_source_sha256": term["executable_source"]["sha256"], "rule_supported": "", "critical_exceptions_complete": "", **blanks}
        for term in specification["business_terms"]]
    tables["pilot-reference"] = [{"question_id": q.question_id, "question": q.question,
        "reference_sql": pilot_gold[q.question_id].sql, "ambiguities": "", "semantic_valid": "", **blanks} for q in pilot_questions]
    if args.format == "csv":
        for name, rows in tables.items():
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            publish_artifact(args.output / (name + ".csv"), stream.getvalue().encode("utf-8"))
    else:
        publish_artifact(args.output / "tables.json", canonical_json({name: {"columns": list(rows[0]), "rows": [list(row.values()) for row in rows]} for name, rows in tables.items()}))
    guide = """# Panduan review instrumen Sakila revision02

Paket ini memuat proposal30soal dan12pilot,106elemen anotasi, serta3aturan domain. Status seluruh keputusan masih kosong. Paket tidak mengandung prediksi LLM, EX, statistik perlakuan atau identitas reviewer yang dibuat otomatis. Proposal masih menunggu independent AI follow-up; persetujuan manusia tidak diasumsikan.

Gunakan dua reviewer yang bekerja sendiri. Berikan salinan kosong tersendiri kepada tiap reviewer. Kode reviewer dapat dipakai pada CSV; simpan pemetaan nama dan tanggal asli terpisah. Jangan mengubah ID atau menimpa kolom sumber. Catat perubahan di proposed_correction dan alasan di reason. Isi decision dengan accept, revise, reject, atau uncertain. Biarkan kosong untuk item yang belum diperiksa; kosong bukan accept dan bukan nol.

## Tahap1: interpretasi independen

Buka questions-blind.csv sebelum questions-reference.csv. Baca soal, schema Sakila dan definisi global resmi yang relevan. Tulis independent_interpretation, independent_sql dan ambiguities. Bedakan kebutuhan pengetahuan yang memang tersedia dalam metadata dari maksud permintaan yang tetap ambigu meskipun S3 lengkap. Jangan menebak hasil eksperimen. Simpan dan hitung SHA-256 file tahap1 sebelum melihat reference usulan. Catat waktu penyerahan tahap1.

## Tahap2: reference dan struktur SQL

Buka questions-reference.csv. Periksa populasi, grain, unit, waktu, peran entitas, NULL/zero, duplikat, urutan kolom, threshold dan ties. Pastikan query menjawab maksud soal, bukan sekadar berhasil dieksekusi. Tulis SQL alternatif bila berbeda. Bandingkan pada Sakila dan kasus pembeda yang telah ditetapkan, termasuk entitas tanpa transaksi dan nilai tepat pada batas. Klasifikasi kompleksitas mengikuti canonical SQL dan adapter Spider yang didokumentasikan; bukan persepsi reviewer tentang sulit/mudah dan bukan hasil LLM. Catat alternative structure bila solusi wajar lebih sederhana.

## Tahap3: metadata dan aturan

Pada annotations.csv, bandingkan short/detailed dengan sumber resmi. Tambahan panjang tanpa proposisi baru tidak wajib. Elemen trivial boleh sama. Periksa kekeliruan fakta, repetisi yang tidak membantu, definisi yang saling bertentangan dan bocoran jawaban. Pada business-terms.csv, periksa executable source dan dokumentasi, bukan asumsi bisnis DVD rental secara umum. Aturan rewards memakai payment events dan dua batas strict. Stock memakai keadaan rental pada snapshot. Komponen keterlambatan bukan full customer balance; cutoff inclusive DATETIME, date-only midnight dan nol untuk pelanggan tanpa rental relevan harus konsisten dengan sumber. Jangan memasukkan gold SQL, recipe join atau threshold benchmark ke metadata global.

## Tahap4: pilot dan konsolidasi

Pilot12soal adalah diagnostik terpisah, bukan tambahan sampel utama. Periksa pilot-reference.csv dengan standar semantik yang sama. Konsolidasikan dua submission sesudah keduanya dikunci hash. Catat setiap ketidaksepakatan dan keputusan adjudikasi. Jangan mengisi approval massal secara otomatis. Jika review dilakukan sesudah generation, tulis tanggal sebenarnya dan sebut post-run review. Gold-only correction dapat dinilai ulang sebagai laporan turunan; perubahan wording/metadata/prompt memerlukan versi instrumen dan generation baru. Tidak boleh mengubah input demi memperoleh EX lebih tinggi atau p-value signifikan.

## Konvensi umum yang harus dibaca bersama soal

Urutan kolom mengikuti keluaran yang diminta; aliases diabaikan. Urutan baris bebas kecuali permintaan ordering/ranking. Duplikat dipertahankan sesuai grain. Komponen tanggal tersimpan memakai UTC tanpa konversi tersirat. Rerata/rasio ditampilkan empat desimal dan threshold dibandingkan sebelum pembulatan. Groups NULL dipertahankan; SUM tanpa observasi numeric tetap NULL, kecuali definisi domain eksplisit menetapkan nol. Setiap entitas yang diminta dalam laporan dipertahankan dengan count nol bila tidak memiliki relasi yang memenuhi. Baca prompts/generation-v2.txt dan protokol revision02 untuk teks sebenarnya.

Keterbatasan: hasil pada database tetap tidak membuktikan ekuivalensi semantik universal. AI-assisted review bukan review manusia. Jumlah30 dan pembagian10–10–10 adalah constrained study design, bukan klaim mencakup seluruh SQL atau workload operasional.
"""
    selection_status = json.loads((selection / "selection.json").read_bytes())["status"]
    if selection_status == "selected_before_inference":
        guide = guide.replace("Proposal masih menunggu independent AI follow-up; persetujuan manusia tidak diasumsikan.",
                              "Input exploratory telah dibekukan sesudah independent AI review dan reference/fixture checks; persetujuan manusia belum tersedia. Periksa versi/hash paket ini saat mengirim submission.")
    publish_artifact(args.output / "review-guide.md", guide.encode())
    inputs = [selection / name for name in ("questions.jsonl", "gold.jsonl", "contracts.jsonl", "profiles.json", "selection.json")]
    inputs += [data / name for name in ("annotations.json", "pilot.questions.jsonl", "pilot.gold-a.jsonl")]
    publish_artifact(args.output / "input-hashes.json", canonical_json({"inputs": [{"path": str(path.resolve().relative_to(ROOT)), "sha256": sha256_bytes(path.read_bytes())} for path in inputs],
        "records": {name: len(rows) for name, rows in tables.items()}, "human_review_complete": False, "model_results_included": False, "selection_status": selection_status}))
    print(json.dumps({"status": "blank_review_inputs_created", "records": {name: len(rows) for name, rows in tables.items()}, "human_review_complete": False}), flush=True)


if __name__ == "__main__":
    main()
