"""Execute and package draft reference results for independent human review."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sqlglot import exp, parse_one

from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from ..config import AppConfig
from ..contracts import DatasetError, load_gold, load_questions
from ..db.execute import execute_sql
from ..db.inspect import inspect_database
from .compare import compare_results, comparison_spec


def structural_complexity(sql: str) -> str:
    tree = parse_one(sql, read="mysql")
    if len(list(tree.find_all(exp.Select))) > 1 or tree.find(exp.CTE, exp.Window, exp.SetOperation) or len(list(tree.find_all(exp.Join))) >= 3:
        return "complex"
    if tree.find(exp.Join, exp.Group, exp.Having):
        return "medium"
    return "simple"


def validate_gold_dataset(config: AppConfig, questions_path: Path, gold_path: Path, output_directory: Path) -> dict:
    questions = load_questions(questions_path)
    references = load_gold(gold_path)
    if {q.question_id for q in questions} != references.keys():
        raise DatasetError("Question/reference IDs differ")
    audit = inspect_database(config)
    tables = frozenset(table["name"] for table in audit["technical_schema"]["tables"])
    records = []
    markdown = ["# Draft benchmark review", "", "Human semantic review is pending. Successful execution and self-comparison are engineering checks, not proof of gold correctness. No LLM generation has been executed.", ""]
    for question in questions:
        reference = references[question.question_id]
        if config.benchmark_manifest:
            from .structure import profile_sql
            classification = profile_sql(reference.sql).complexity
        else:
            classification = structural_complexity(reference.sql)
        if classification != question.complexity:
            raise DatasetError(f"{question.question_id}: gold structure does not match the complexity rubric")
        if any(name.split(".", 1)[0] not in tables for name in question.schema_references):
            raise DatasetError(f"{question.question_id}: unknown schema reference")
        execution = execute_sql(config, reference.sql, tables)
        if execution.status != "success":
            raise DatasetError(f"{question.question_id}: gold execution failed ({execution.validation_code}; {execution.error_code})")
        spec = comparison_spec(reference)
        if compare_results(execution.result, execution.result, spec).execution_accuracy != 1:
            raise DatasetError(f"{question.question_id}: evaluator self-check failed")
        if not execution.result.rows:
            raise DatasetError(f"{question.question_id}: empty draft gold requires an explicit reviewed justification")
        publish_artifact(output_directory / f"{question.question_id}.result.json", canonical_json(execution.result.encoded()))
        record = {"question_id": question.question_id, "complexity": classification, "row_count": len(execution.result.rows), "column_count": len(execution.result.columns), "result_sha256": execution.result_sha256, "sql_execution_latency_ms": execution.latency_ms, "review_status": reference.review_status}
        records.append(record)
        markdown.extend([f"## {question.question_id} — {classification}", "", question.question, "", "```sql", reference.sql, "```", "", f"Executed rows: {record['row_count']}; columns: {record['column_count']}; review: {reference.review_status}.", "", "Reviewer checks: meaning, requested columns/order, aggregation grain, duplicate handling, NULL handling, tie breaking, metadata independence.", ""])
    report = {"status": "draft_gold_execution_validated", "human_review_complete": all(r.review_status == "approved" for r in references.values()), "question_count": len(questions), "questions_sha256": sha256_bytes(questions_path.read_bytes()), "gold_sha256": sha256_bytes(gold_path.read_bytes()), "database_schema_sha256": audit["schema_sha256"], "database_data_sha256": audit["data_sha256"], "llm_generation_trials": 0, "records": records}
    publish_artifact(output_directory / "validation.json", canonical_json(report))
    publish_artifact(output_directory / "review.md", "\n".join(markdown).encode())
    return report

