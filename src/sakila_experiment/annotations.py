"""Blind two-annotator templates and validated consolidation; no auto-approval."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from .artifacts import canonical_json, publish_artifact, sha256_bytes
from .review import build_review_package, write_csv

EDITABLE = ("decision", "question_clear", "answerable", "gold_correct", "contract_correct", "complexity_correct", "no_overlap",
            "short_correct", "detailed_correct", "source_grounded", "no_solution_leak", "definition_correct", "bindings_correct",
            "proposed_question", "proposed_gold_sql", "proposed_complexity", "proposed_short", "proposed_detailed", "proposed_definition", "proposed_bindings", "notes", "annotated_at_utc")
CRITERIA = {"questions": ("question_clear", "answerable", "gold_correct", "contract_correct", "complexity_correct", "no_overlap"),
            "metadata": ("short_correct", "detailed_correct", "source_grounded", "no_solution_leak"),
            "business": ("definition_correct", "bindings_correct", "source_grounded", "no_solution_leak")}
PROPOSALS = {"questions": ("proposed_question", "proposed_gold_sql", "proposed_complexity"),
             "metadata": ("proposed_short", "proposed_detailed"), "business": ("proposed_definition", "proposed_bindings")}


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_annotation_round(root: Path, output: Path):
    if output.exists():
        raise ValueError("Annotation round exists; choose a new version")
    package = build_review_package(root, output / "reference")
    source = {"questions": rows(output / "reference/questions.csv"), "metadata": rows(output / "reference/annotations.csv"), "business": rows(output / "reference/business-terms.csv")}
    for row in source["questions"]:
        result = root / row["reference_result"]
        if result.is_file():
            relative = "reference/results/" + row["question_id"] + ".json"
            publish_artifact(output / relative, result.read_bytes())
            row["reference_result"] = relative
    snapshot_root = root / "snapshots/candidates-v2"
    if not snapshot_root.exists():
        snapshot_root = root / "snapshots/distribution-v1"
    schema_manifest = json.loads((snapshot_root / "S0/manifest.json").read_bytes())
    publish_artifact(output / "schema.json", (snapshot_root / "S0" / schema_manifest["payload_file"]).read_bytes())
    template_hashes = {}
    for reviewer in ("A01", "A02"):
        for kind, source_rows in source.items():
            template = []
            for original in source_rows:
                immutable = {k: v for k, v in original.items() if k not in {"decision", "rationale", "reviewer", "reviewed_at_utc"}}
                identity = immutable.get("question_id") or immutable.get("element_id") or immutable["term_id"]
                item = {"item_id": kind + ":" + identity, "annotator_id": reviewer, **immutable}
                item["item_sha256"] = sha256_bytes(canonical_json(item))
                item.update({k: "" for k in CRITERIA[kind] + PROPOSALS[kind] + ("notes", "annotated_at_utc")})
                item["decision"] = "pending"
                template.append(item)
            path = output / reviewer / (kind + ".csv")
            write_csv(path, template)
            template_hashes[str(path.relative_to(output))] = sha256_bytes(path.read_bytes())
    guide = """# Panduan anotator independen

Tujuan: menilai kebenaran dan kejelasan benchmark serta anotasi metadata. Ini bukan penilaian apakah model berhasil menjawab. Hasil model berada dalam embargo selama review.

1. A01 dan A02 mengerjakan salinan folder masing-masing secara independen. Jangan melihat isian anotator lain, SQL prediksi, EX, atau laporan error model sebelum submit.
2. Baca schema.json, pertanyaan, draft gold, kontrak hasil dan sumber metadata. Reference/review-guide.md memuat cuplikan hasil referensi bertipe. Keberhasilan SQL dieksekusi tidak otomatis membuat maknanya benar.
3. Isi setiap criterion dengan yes, no, atau uncertain. Isi decision dengan accepted, revise, rejected, atau uncertain. Pending berarti belum dikerjakan. Accepted mensyaratkan seluruh criterion yes tanpa usulan perubahan.
4. Tulis usulan pada proposed_*; jangan mengganti teks sumber, ID, kontrak atau hash. Tulis alasan di notes, terutama untuk keputusan selain accepted. Isi annotated_at_utc dengan ISO 8601 bertimezone, misalnya 2026-10-27T12:00:00Z (gunakan tanggal sebenarnya).
5. Soal: periksa makna Indonesia, answerability, JOIN/aggregation grain, NULL, duplikat, kolom, ordering/ties, gold SQL, complexity dan paraphrase overlap antara pilot/utama. Simple tanpa JOIN/group/subquery; medium memakai JOIN/group/HAVING tanpa struktur complex; complex memakai subquery/CTE/window/set operation atau sedikitnya tiga JOIN.
6. Metadata: short dan detailed dinilai terpisah. Periksa fakta, unit, nullability, peran FK, sumber dan tidak adanya SQL solusi/petunjuk khusus soal. Banyaknya deskripsi tidak otomatis berarti kualitas lebih baik. Istilah bisnis harus grounded dan bindings relevan.
7. Setelah kedua submission selesai, peneliti/adjudikator membahas konflik. Jangan mengubah soal atau anotasi untuk meningkatkan skor model. Koreksi harus berdasarkan makna dan sumber.

Kirim CSV melalui kanal yang ditetapkan peneliti. Simpan identitas asli di luar paket public; gunakan A01/A02 pada isian. Program konsolidasi tidak membuat persetujuan final dan tidak mengubah gold/snapshot.
"""
    publish_artifact(output / "GUIDE.md", guide.encode())
    manifest = {"format_version": 1, "status": "pending_external_annotation", "annotators": ["A01", "A02"],
                "items_per_annotator": sum(len(r) for r in source.values()), "source_input_sha256": package["input_sha256"],
                "template_sha256": template_hashes, "model_predictions_included": False, "model_scores_included": False}
    publish_artifact(output / "manifest.json", canonical_json(manifest))
    return manifest


def consolidate(package: Path, a01: Path, a02: Path, output: Path):
    manifest = json.loads((package / "manifest.json").read_bytes())
    adjudication, paired, agreements = [], 0, 0
    for kind in CRITERIA:
        submitted = {}
        for reviewer, directory in (("A01", a01), ("A02", a02)):
            template_path = package / reviewer / (kind + ".csv")
            if sha256_bytes(template_path.read_bytes()) != manifest["template_sha256"][str(template_path.relative_to(package))]:
                raise ValueError("Distributed template changed")
            expected = {r["item_id"]: r for r in rows(template_path)}
            incoming = rows(directory / (kind + ".csv"))
            actual = {r["item_id"]: r for r in incoming}
            if len(actual) != len(incoming) or actual.keys() != expected.keys():
                raise ValueError("Missing, duplicate or unexpected annotation IDs")
            for identity, row in actual.items():
                if any(not isinstance(value, str) for value in row.values()):
                    raise ValueError("Malformed CSV row or missing annotation cells")
                if set(row) != set(expected[identity]) or any(row[k] != v for k, v in expected[identity].items() if k not in EDITABLE):
                    raise ValueError("Immutable annotation source fields changed")
                decision = row["decision"]
                if decision not in {"pending", "accepted", "revise", "rejected", "uncertain"}:
                    raise ValueError("Unknown annotation decision")
                if decision == "pending":
                    continue
                if any(row[c] not in {"yes", "no", "uncertain"} for c in CRITERIA[kind]):
                    raise ValueError("Completed annotations require every criterion")
                try:
                    stamp = datetime.fromisoformat(row["annotated_at_utc"].replace("Z", "+00:00"))
                    if stamp.tzinfo is None: raise ValueError()
                except ValueError:
                    raise ValueError("A real timezone-aware annotation date is required") from None
                if decision == "accepted" and (any(row[c] != "yes" for c in CRITERIA[kind]) or any(row[p].strip() for p in PROPOSALS[kind])):
                    raise ValueError("Accepted annotations require yes criteria and no proposed correction")
                if decision != "accepted" and not row["notes"].strip():
                    raise ValueError("Non-accepted decisions require a rationale")
            submitted[reviewer] = actual
        for identity, first in submitted["A01"].items():
            second = submitted["A02"][identity]
            complete = first["decision"] != "pending" and second["decision"] != "pending"
            agreement = complete and first["decision"] == second["decision"] != "uncertain" and all(first[p] == second[p] for p in CRITERIA[kind] + PROPOSALS[kind])
            paired += int(complete); agreements += int(agreement)
            adjudication.append({"item_id": identity, "kind": kind, "a01_decision": first["decision"], "a02_decision": second["decision"],
                                 "a01_notes": first["notes"], "a02_notes": second["notes"], "a01_proposals": json.dumps({p: first[p] for p in PROPOSALS[kind]}, ensure_ascii=False),
                                 "a02_proposals": json.dumps({p: second[p] for p in PROPOSALS[kind]}, ensure_ascii=False), "agreement": agreement,
                                 "final_decision": "pending", "final_correction": "", "adjudicator": "", "rationale": "", "adjudicated_at_utc": ""})
    write_csv(output / "adjudication.csv", adjudication)
    report = {"status": "pending_adjudication", "items": len(adjudication), "paired_completed": paired, "resolution_agreements": agreements,
              "agreement_percent": agreements / paired * 100 if paired else None, "approvals_created": 0,
              "source_manifest_sha256": sha256_bytes((package / "manifest.json").read_bytes())}
    publish_artifact(output / "report.json", canonical_json(report))
    return report
