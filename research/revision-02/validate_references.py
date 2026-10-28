"""Compare independent draft references and predeclared semantic mutants.

No inference or approval. Original Sakila is read only; fixture mutation is
restricted by evaluation.fixtures to its separate container, port and secrets.
"""
from __future__ import annotations

import argparse
import json
import importlib.metadata
import platform
from pathlib import Path

from mutations import wrong_variants

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.config import load_config
from sakila_experiment.contracts import load_gold, load_questions
from sakila_experiment.db.execute import execute_sql
from sakila_experiment.db.inspect import inspect_database, verify_fingerprint
from sakila_experiment.evaluation.compare import ComparisonSpec, compare_results
from sakila_experiment.evaluation.fixtures import prepare_fixture
from sakila_experiment.instrument import REFERENCE_VALIDATION_SOURCES, REFERENCE_VALIDATION_PACKAGES

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", action="store_true")
    parser.add_argument("--dataset", choices=("candidates", "pilot"), default="candidates")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/revision02.toml")
    parser.add_argument("--gold-b", type=Path, action="append", help="Independent reference files; default is latest natural-question audit")
    args = parser.parse_args()
    root, output = ROOT, args.output.resolve()
    if output.exists():
        raise FileExistsError("Choose a new reference-validation output directory")
    folder = root / "data/benchmarks/revision-02"
    prefix = args.dataset
    references = load_gold(folder / (prefix + ".gold-a.jsonl"))
    questions = load_questions(folder / (prefix + ".questions.jsonl"))
    independent = {}
    if prefix == "pilot" and not args.gold_b:
        raise ValueError("The changed pilot requires explicit current independent reference files")
    gold_b_files = args.gold_b or [root / "runs/revision-02/audits/natural-questions/gold-b.jsonl"]
    for path in gold_b_files:
        for line in path.read_bytes().splitlines():
            record = json.loads(line)
            independent[record["question_id"]] = record
    baseline = json.loads((root / "runs/database/baseline.json").read_bytes())
    tables = frozenset(table["name"] for table in baseline["technical_schema"]["tables"])
    config = load_config(args.config)
    verify_fingerprint(inspect_database(config), baseline)
    mutations = {qid: wrong_variants(qid, reference.sql) for qid, reference in references.items()}
    publish_artifact(output / "mutations.json", canonical_json(mutations))
    publish_artifact(output / "input-lock.json", canonical_json({
        "questions_sha256": sha256_bytes((folder / (prefix + ".questions.jsonl")).read_bytes()),
        "gold_a_sha256": sha256_bytes((folder / (prefix + ".gold-a.jsonl")).read_bytes()),
        "dataset": prefix,
        "implementation_sha256": {relative: sha256_bytes((root / relative).read_bytes()) for relative in REFERENCE_VALIDATION_SOURCES},
        "package_versions": {name: importlib.metadata.version(name) for name in REFERENCE_VALIDATION_PACKAGES},
        "python_version": platform.python_version(), "mysql_version": baseline["server"]["version"],
        "database_config": config.database.model_dump(mode="json"),
        "database_schema_sha256": baseline["schema_sha256"], "database_data_sha256": baseline["data_sha256"],
        "gold_b_files": [{"path": str(path.resolve().relative_to(root)), "sha256": sha256_bytes(path.read_bytes())} for path in gold_b_files],
        "mutation_definition_sha256": sha256_bytes((root / "research/revision-02/mutations.py").read_bytes()),
        "fixture_definition_sha256": sha256_bytes((root / "research/revision-02/fixture_cases.json").read_bytes()),
        "generation_requests": 0, "human_review_complete": False}))
    cases = ["baseline"]
    if args.fixtures:
        cases += [case["fixture_id"] for case in json.loads((root / "research/revision-02/fixture_cases.json").read_bytes())["cases"]]
    records = []
    for case in cases:
        selected = config
        if case != "baseline":
            selected, _ = prepare_fixture(root, case, output / case / "fixture.json")
            selected = selected.model_copy(update={"database": selected.database.model_copy(update={
                "sql_policy_version": config.database.sql_policy_version, "time_names_locale": config.database.time_names_locale})})
        case_records = []
        for question in questions:
            qid = question.question_id
            reference = references[qid]
            spec = ComparisonSpec(reference.column_count, reference.ordered, reference.approximate_columns, date_columns=reference.date_columns)
            # A's correlated Q136 exceeded the unchanged 10s policy in initial
            # preflight. Preserve it as an ineligible draft; use independent B
            # solely to examine its requirements without repeatedly timing out.
            a = execute_sql(selected, reference.sql, tables) if qid != "Q136" else None
            b = execute_sql(selected, independent[qid]["sql"], tables)
            record = {"fixture_id": case, "question_id": qid,
                      "author_a_status": a.status if a else "initial_deadline_ineligible",
                      "author_b_status": b.status, "reference_agreement": None,
                      "author_a_error": a.error_code if a else 3024,
                      "author_b_error": b.error_code, "mutations": []}
            record.update(author_a_validation_code=a.validation_code if a else "initial_deadline_ineligible",
                          author_b_validation_code=b.validation_code)
            for author, result in [("a", a), ("b", b)]:
                if result and result.result is not None:
                    publish_artifact(output / case / f"{qid}-{author}.json", canonical_json(result.result.encoded()))
            if a and a.result and b.result:
                record["reference_agreement"] = bool(compare_results(a.result, b.result, spec).execution_accuracy)
            expected = a if a and a.result else b
            if expected.result is None:
                record["evaluation_status"] = "reference_execution_blocked"
            else:
                record["reference_row_count"] = len(expected.result.rows)
                for mutation in mutations[qid]:
                    result = execute_sql(selected, mutation["sql"], tables)
                    killed = bool(result.result is not None and not compare_results(result.result, expected.result, spec).execution_accuracy)
                    record["mutations"].append({"mutation_id": mutation["mutation_id"], "execution_status": result.status,
                                                "semantic_difference_observed": killed, "error_code": result.error_code})
            case_records.append(record)
        records.extend(case_records)
        publish_artifact(output / case / "comparisons.json", canonical_json(case_records))
        print(json.dumps({"fixture_id": case, "reference_pairs": len(case_records),
                          "disagreements": [r["question_id"] for r in case_records if r["reference_agreement"] is False],
                          "execution_issues": [r["question_id"] for r in case_records if r["author_b_status"] != "success" or r["author_a_status"] not in {"success", "initial_deadline_ineligible"}]}), flush=True)
    summary = []
    for question in questions:
        rows = [row for row in records if row["question_id"] == question.question_id]
        mutation_ids = [row["mutation_id"] for row in mutations[question.question_id]]
        witnesses = {mutation: [row["fixture_id"] for row in rows for result in row["mutations"]
                                if result["mutation_id"] == mutation and result["semantic_difference_observed"]]
                     for mutation in mutation_ids}
        summary.append({"question_id": question.question_id, "reference_agreement_all_checked": all(r["reference_agreement"] is True for r in rows),
                        "witnesses": witnesses, "all_predeclared_mutants_distinguished": all(witnesses.values()),
                        "baseline_empty": rows[0].get("reference_row_count") == 0,
                        "reference_execution_valid": all(r["author_a_status"] == r["author_b_status"] == "success" for r in rows)})
    verify_fingerprint(inspect_database(config), baseline)
    publish_artifact(output / "summary.json", canonical_json({"status": "reference_and_witness_checks_complete", "cases": cases,
        "records": summary, "generation_requests": 0, "primary_database_unchanged": True, "human_review_complete": False,
        "limits": "Agreement of AI-authored references and finite witnesses is engineering evidence, not semantic proof or human approval."}))
    print(json.dumps({"status": "reference_and_witness_checks_complete", "cases": len(cases), "question_candidates": len(summary),
                      "all_mutants_distinguished": sum(r["all_predeclared_mutants_distinguished"] for r in summary), "generation_requests": 0}), flush=True)


if __name__ == "__main__":
    main()
