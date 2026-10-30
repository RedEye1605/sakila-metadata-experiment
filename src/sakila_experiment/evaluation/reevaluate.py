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
from .compare import COMPARATOR_VERSION, compare_results, comparison_spec
from .gold import structural_complexity


def generation_signature(manifest: dict) -> str:
    return sha256_bytes(canonical_json({k: manifest[k] for k in ("questions_sha256", "model_version_or_hash", "inference_config", "prompt_template_sha256", "database_schema_sha256", "database_data_sha256")} | {"snapshots": manifest["snapshots"]["snapshot_sha256"]}))


FIXED_EVALUATOR_FILES = (
    "src/sakila_experiment/evaluation/compare.py", "src/sakila_experiment/evaluation/safety.py",
    "src/sakila_experiment/db/connection.py", "src/sakila_experiment/db/execute.py",
    "src/sakila_experiment/db/values.py", "src/sakila_experiment/analysis/statistics.py", "uv.lock",
    "src/sakila_experiment/evaluation/gold.py", "src/sakila_experiment/contracts.py",
)


def validate_fixed_evaluation(config, manifest):
    if config.database.model_dump(mode="json") != manifest["database_config"] or manifest["comparator_version"] != COMPARATOR_VERSION:
        raise ValueError("Reference-only reevaluation requires the frozen database execution/comparison policy")
    if sha256_bytes((config.project_root / "docs/analysis-plan.md").read_bytes()) != manifest["analysis_protocol_sha256"]:
        raise ValueError("Frozen analysis protocol changed")
    hashes = {r["path"]: r["sha256"] for r in manifest["source_version"]["source_files"]}
    for name in FIXED_EVALUATOR_FILES:
        if hashes.get(name) != sha256_bytes((config.project_root / name).read_bytes()):
            raise ValueError("Frozen evaluation implementation changed: " + name)


def validate_adjudication(manifest, receipt, gold_path, package, adjudication_file):
    """Require complete independent review and a hash-bound human adjudication."""
    from ..annotations import CRITERIA, rows
    package_manifest = json.loads((package / "manifest.json").read_bytes())
    consolidation = json.loads((adjudication_file.parent / "report.json").read_bytes())
    base = package.resolve()
    for name, digest in package_manifest["template_sha256"].items():
        path = (package / name).resolve()
        if not path.is_relative_to(base) or sha256_bytes(path.read_bytes()) != digest:
            raise ValueError("Distributed review template changed after consolidation")
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
            or receipt.get("consolidation_report_sha256") != sha256_bytes((adjudication_file.parent / "report.json").read_bytes())
            or receipt.get("review_package_sha256") != sha256_bytes((package / "manifest.json").read_bytes())):
        raise ValueError("Adjudication receipt does not bind the reviewed reference and unchanged generation inputs")
    return decisions


def validate_reference_changes(package, decisions, references, questions):
    """A reviewed file must implement exactly the adjudicated reference changes."""
    from ..annotations import rows
    original = {r["question_id"]: r for r in rows(package / "A01/questions.csv") if r["scope"] == "main"}
    final = {r["item_id"]: r for r in decisions}
    if original.keys() != references.keys():
        raise ValueError("Reviewed references must cover the original main benchmark")
    for question in questions:
        qid = question.question_id
        row = original[qid]
        ordered = row["ordered"].lower()
        if ordered not in {"true", "false"}:
            raise ValueError("Invalid distributed ordering contract")
        expected = {"sql": row["gold_sql"], "column_count": int(row["column_count"]),
                    "ordered": ordered == "true", "approximate_columns": json.loads(row["approximate_columns"])}
        decision = final["questions:" + qid]
        if decision["final_decision"] == "accepted_with_correction":
            for key, value in json.loads(decision["final_correction"]).items():
                if key != "semantic_notes": expected["sql" if key == "gold_sql" else key] = value
        actual = references[qid].model_dump(mode="json", include=set(expected))
        if canonical_json(actual) != canonical_json(expected):
            raise ValueError("Reviewed reference differs from the adjudicated correction: " + qid)
        if row["complexity"] != question.complexity or structural_complexity(references[qid].sql) != question.complexity:
            raise ValueError("Reference correction changes the frozen structural-complexity design: " + qid)


def reevaluate(config, source: Path, gold_path: Path, questions_path: Path, snapshots: Path, receipt_path: Path, output: Path, *, review_package: Path, adjudication_file: Path):
    if output.exists():
        raise ValueError("Reevaluation output exists; original evidence is never overwritten")
    manifest, rows = audit_run(source)
    if manifest["mode"] not in {"preliminary", "main"}:
        raise ValueError("Reference reevaluation requires a complete 600-trial benchmark")
    receipt = json.loads(receipt_path.read_bytes())
    validate_fixed_evaluation(config, manifest)
    references = load_gold(gold_path)
    if any(r.column_order != "fixed" or r.date_columns for r in references.values()):
        raise ValueError("Legacy reference-only adjudication cannot change the frozen comparison policy")
    if any(r.review_status != "approved" for r in references.values()):
        raise ValueError("All replacement references require semantic approval")
    questions = load_questions(questions_path)
    if (sha256_bytes(questions_path.read_bytes()) != manifest["questions_sha256"] or set(references) != {q.question_id for q in questions}
            or validate_scenario_set(snapshots)["snapshot_sha256"] != manifest["snapshots"]["snapshot_sha256"]
            or sha256_bytes((config.project_root / "prompts/generation.txt").read_bytes()) != manifest["prompt_template_sha256"]
            or config.inference.model_dump(mode="json") != manifest["inference_config"]):
        raise ValueError("Generation inputs changed; a new 600-trial generation run is required")
    decisions = validate_adjudication(manifest, receipt, gold_path, review_package, adjudication_file)
    validate_reference_changes(review_package, decisions, references, questions)
    audit = inspect_database(config)
    if audit["schema_sha256"] != manifest["database_schema_sha256"] or audit["data_sha256"] != manifest["database_data_sha256"]:
        raise ValueError("Database changed; reference-only reevaluation is not allowed")
    tables = frozenset(t["name"] for t in audit["technical_schema"]["tables"])
    gold = {}
    for qid, reference in references.items():
        execution = execute_sql(config, reference.sql, tables)
        if execution.status != "success": raise ValueError("Reviewed gold execution failed: " + qid)
        compare_results(execution.result, execution.result, comparison_spec(reference))
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
            comparison = compare_results(actual, gold[row["question_id"]].result, comparison_spec(reference))
            item.update(execution_accuracy=comparison.execution_accuracy, comparison_reason=comparison.reason)
        else:
            item["execution_accuracy"] = 0
        item.update(source_execution_accuracy=row["execution_accuracy"], gold_result_hash=gold[row["question_id"]].result_sha256,
                    evaluation_status="reviewed_reference_reevaluation", reference_review_status="approved")
        revised.append(item)
    from ..analysis.statistics import paired_analysis
    statistics = paired_analysis(revised, seed=manifest["experiment_config"]["analysis_seed"])
    report = {"evaluation_status": "reviewed_reference_reevaluation", "source_experiment_id": manifest["experiment_id"], "generation_requests": 0,
              "original_generation_mode": manifest["mode"], "public_results_embargo": True,
              "reevaluator_source_sha256": sha256_bytes(Path(__file__).read_bytes()),
              "source_manifest_sha256": sha256_bytes((source / "manifest.json").read_bytes()), "adjudication_receipt_sha256": sha256_bytes(receipt_path.read_bytes()),
              "generation_signature": generation_signature(manifest), "gold_sha256": sha256_bytes(gold_path.read_bytes()),
              "descriptive": descriptive(revised), "paired_analysis": statistics, "original_ledger_unchanged": True}
    for row in report["descriptive"]["by_scenario"]:
        row.update(evaluation_status="reviewed_reference_reevaluation", generation_mode=manifest["mode"])
    publish_artifact(output / "trials.jsonl", b"".join(canonical_json(r) for r in revised))
    publish_artifact(output / "report.json", canonical_json(report))
    publish_artifact(output / "execution-accuracy.csv", csv_bytes(report["descriptive"]["by_scenario"], ["evaluation_status", "generation_mode", "scenario_id", "trials", "correct", "execution_accuracy_percent"]))
    return report
