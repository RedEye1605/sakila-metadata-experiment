"""Reference-only reevaluation of durable predictions; no inference imports."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..analysis.report import audit_run, csv_bytes, descriptive
from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from ..contracts import load_gold, load_questions
from ..db.execute import ResultTable, execute_sql
from ..db.inspect import inspect_database
from ..db.values import decode_value
from ..metadata.snapshots import validate_scenario_set
from .compare import ComparisonSpec, compare_results


def generation_signature(manifest: dict) -> str:
    return sha256_bytes(canonical_json({k: manifest[k] for k in ("questions_sha256", "model_version_or_hash", "inference_config", "prompt_template_sha256", "database_schema_sha256", "database_data_sha256")} | {"snapshots": manifest["snapshots"]["snapshot_sha256"]}))


def validate_adjudication(manifest, receipt, gold_path, package, adjudication_file):
    """Require complete independent review and a hash-bound human adjudication."""
    from ..annotations import CRITERIA, rows
    package_manifest = json.loads((package / "manifest.json").read_bytes())
    consolidation = json.loads((adjudication_file.parent / "report.json").read_bytes())
    expected = {r["item_id"] for kind in CRITERIA for r in rows(package / "A01" / (kind + ".csv"))}
    decisions = rows(adjudication_file)
    if len(decisions) != len(expected) or {r["item_id"] for r in decisions} != expected:
        raise ValueError("Adjudication must cover every distributed review item")
    if (consolidation.get("paired_completed") != len(expected) or consolidation.get("items") != len(expected)
            or consolidation.get("source_manifest_sha256") != sha256_bytes((package / "manifest.json").read_bytes())):
        raise ValueError("Both independent submissions must be complete before adjudication")
    for row in decisions:
        if (row["final_decision"] not in {"accepted", "accepted_with_correction"} or not row["adjudicator"].strip()
                or not row["rationale"].strip() or (row["final_decision"] == "accepted_with_correction" and not row["final_correction"].strip())):
            raise ValueError("Every item needs a documented final human decision")
        if row["final_decision"] == "accepted_with_correction":
            # A corrected question/annotation cannot be silently ignored while
            # reusing predictions generated from the old treatment.
            allowed = {"gold_sql", "column_count", "ordered", "approximate_columns", "semantic_notes"}
            correction = json.loads(row["final_correction"])
            if row["kind"] != "questions" or not isinstance(correction, dict) or not correction or not set(correction) <= allowed:
                raise ValueError("Only gold SQL/result-contract corrections permit reference-only reevaluation; regenerate after other corrections")
        stamp = datetime.fromisoformat(row["adjudicated_at_utc"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Adjudication date must include a timezone")
    sources = package_manifest["source_input_sha256"]
    if sources.get("data/public/main.questions.jsonl") != manifest["questions_sha256"] or sources.get("data/private/main.gold.jsonl") != manifest["gold_sha256"]:
        raise ValueError("Review package is not bound to the original generation dataset")
    if manifest.get("metadata_provenance") and sources.get("data/annotations/specification.json") != manifest["metadata_provenance"][0]["annotation_spec_sha256"]:
        raise ValueError("Review package metadata differs from the generated snapshot preparation")
    if (receipt.get("status") != "adjudicated" or set(receipt.get("reviewers", [])) != {"A01", "A02"}
            or not receipt.get("adjudicator") or not receipt.get("adjudicated_at_utc")
            or receipt.get("generation_signature") != generation_signature(manifest)
            or receipt.get("gold_sha256") != sha256_bytes(gold_path.read_bytes())
            or receipt.get("adjudication_sha256") != sha256_bytes(adjudication_file.read_bytes())
            or receipt.get("review_package_sha256") != sha256_bytes((package / "manifest.json").read_bytes())):
        raise ValueError("Adjudication receipt does not bind the reviewed reference and unchanged generation inputs")


def reevaluate(config, source: Path, gold_path: Path, questions_path: Path, snapshots: Path, receipt_path: Path, output: Path, *, review_package: Path, adjudication_file: Path):
    if output.exists():
        raise ValueError("Reevaluation output exists; original evidence is never overwritten")
    manifest, rows = audit_run(source)
    if manifest["mode"] not in {"preliminary", "main"}:
        raise ValueError("Reference reevaluation requires a complete 600-trial benchmark")
    receipt = json.loads(receipt_path.read_bytes())
    references = load_gold(gold_path)
    if any(r.review_status != "approved" for r in references.values()):
        raise ValueError("All replacement references require semantic approval")
    questions = load_questions(questions_path)
    if (sha256_bytes(questions_path.read_bytes()) != manifest["questions_sha256"] or set(references) != {q.question_id for q in questions}
            or validate_scenario_set(snapshots)["snapshot_sha256"] != manifest["snapshots"]["snapshot_sha256"]
            or sha256_bytes((config.project_root / "prompts/generation.txt").read_bytes()) != manifest["prompt_template_sha256"]
            or config.inference.model_dump(mode="json") != manifest["inference_config"]):
        raise ValueError("Generation inputs changed; a new 600-trial generation run is required")
    validate_adjudication(manifest, receipt, gold_path, review_package, adjudication_file)
    audit = inspect_database(config)
    if audit["schema_sha256"] != manifest["database_schema_sha256"] or audit["data_sha256"] != manifest["database_data_sha256"]:
        raise ValueError("Database changed; reference-only reevaluation is not allowed")
    tables = frozenset(t["name"] for t in audit["technical_schema"]["tables"])
    gold = {}
    for qid, reference in references.items():
        execution = execute_sql(config, reference.sql, tables)
        if execution.status != "success": raise ValueError("Reviewed gold execution failed: " + qid)
        compare_results(execution.result, execution.result, ComparisonSpec(reference.column_count, reference.ordered, reference.approximate_columns))
        gold[qid] = execution
        publish_artifact(output / "gold-results" / (qid + ".json"), canonical_json(execution.result.encoded()))
    revised = []
    for row in rows:
        item = dict(row)
        reference = references[row["question_id"]]
        if row["execution_status"] == "success":
            payload = json.loads((source / "results" / (row["trial_id"] + ".json")).read_bytes())
            count = payload["column_count"]
            actual = ResultTable(tuple("column_" + str(i) for i in range(count)), tuple(0 for _ in range(count)),
                                 tuple(tuple(decode_value(c) for c in r) for r in payload["rows"]))
            comparison = compare_results(actual, gold[row["question_id"]].result, ComparisonSpec(reference.column_count, reference.ordered, reference.approximate_columns))
            item.update(execution_accuracy=comparison.execution_accuracy, comparison_reason=comparison.reason)
        else:
            item["execution_accuracy"] = 0
        item.update(source_execution_accuracy=row["execution_accuracy"], gold_result_hash=gold[row["question_id"]].result_sha256,
                    evaluation_status="reviewed_reference_reevaluation", reference_review_status="approved")
        revised.append(item)
    from ..analysis.statistics import paired_analysis
    statistics = paired_analysis(revised, seed=manifest["experiment_config"]["analysis_seed"])
    report = {"evaluation_status": "reviewed_reference_reevaluation", "source_experiment_id": manifest["experiment_id"], "generation_requests": 0,
              "source_manifest_sha256": sha256_bytes((source / "manifest.json").read_bytes()), "adjudication_receipt_sha256": sha256_bytes(receipt_path.read_bytes()),
              "generation_signature": generation_signature(manifest), "gold_sha256": sha256_bytes(gold_path.read_bytes()),
              "descriptive": descriptive(revised), "paired_analysis": statistics, "original_ledger_unchanged": True}
    publish_artifact(output / "trials.jsonl", b"".join(canonical_json(r) for r in revised))
    publish_artifact(output / "report.json", canonical_json(report))
    publish_artifact(output / "execution-accuracy.csv", csv_bytes(report["descriptive"]["by_scenario"], ["scenario_id", "trials", "correct", "execution_accuracy_percent"]))
    return report
