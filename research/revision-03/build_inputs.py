"""Publish a versioned natural-language draft, never choose by model scores."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.contracts import load_gold, load_questions
from sakila_experiment.evaluation.structure import profile_sql

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authoring-directory", type=Path, default=ROOT / "runs/revision-03/question-authoring-02")
    args = parser.parse_args()
    author = args.authoring_directory.resolve()
    output = ROOT / "data/benchmarks/revision-03"
    questions = [q.model_dump(mode="json") for q in load_questions(author / "questions.jsonl")]
    gold = load_gold(author / "gold.jsonl")
    contracts = [json.loads(line) for line in (author / "contracts.jsonl").read_bytes().splitlines() if line.strip()]
    # Fresh blind review identified an observed-pairs versus Cartesian-product
    # ambiguity. Express the requested relationship, never a join recipe.
    wording = "Tampilkan nomor, nama depan, dan nama belakang pemeran beserta nomor dan nama setiap kategori film yang pernah dibintanginya."
    for question in questions:
        if question["question_id"] == "Q154":
            question["question"] = wording
    for contract in contracts:
        # New independent interpretation must replace these before freezing.
        contract["independent_review_artifacts"] = []
        contract["construction_status"] = "draft"
    for name, records in (("questions", questions), ("gold", [g.model_dump(mode="json") for g in gold.values()]), ("contracts", contracts)):
        content = b"".join(canonical_json(row) for row in records)
        publish_artifact(output / (name + ".jsonl"), content)
        alias = {"questions": "candidates.questions.jsonl", "gold": "candidates.gold-a.jsonl", "contracts": "candidates.contracts.jsonl"}[name]
        publish_artifact(output / alias, content)
    publish_artifact(ROOT / "prompts/generation-v3.txt", (author / "generation-instruction.txt").read_bytes())
    profiles = [{"question_id": q["question_id"], **profile_sql(gold[q["question_id"]].sql).document(),
                 "primary_need": next(c["primary_need"] for c in contracts if c["question_id"] == q["question_id"])} for q in questions]
    publish_artifact(output / "profiles.json", canonical_json(profiles))
    spec = importlib.util.spec_from_file_location("legacy_semantic_mutants", ROOT / "research/revision-02/mutations.py")
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    mutations = {}
    for qid, reference in gold.items():
        sql = reference.sql
        if qid == "Q133":
            variants = [{"mutation_id": qid + "-wrong-primary", "sql": legacy.replace_expression(sql, "c.active=0", "c.active=1"),
                         "kind": "wrong_customer_population", "origin": "requirement-defined, before revision-03 generation"}]
        elif qid == "Q148":
            variants = [{"mutation_id": qid + "-wrong-primary", "sql": legacy.replace_expression(sql,
                         "COUNT(CASE WHEN i.inventory_id IS NOT NULL AND r.rental_id IS NULL THEN i.inventory_id END)", "COUNT(i.inventory_id)"),
                         "kind": "ignores_availability", "origin": "source-rule-defined, before revision-03 generation"}]
        else:
            variants = legacy.wrong_variants(qid, sql)
        changes = {"Q128": [("reverse-ranking", "ORDER BY rental_rate DESC", "ORDER BY rental_rate ASC"),
                              ("reverse-ties", "film_id ASC", "film_id DESC")],
                   "Q141": [("wrong-k", "LIMIT 1", "LIMIT 2"), ("reverse-ties", "s.staff_id ASC", "s.staff_id DESC")],
                   "Q152": [("wrong-k", "LIMIT 10", "LIMIT 9"),
                              ("reverse-ranking", "ORDER BY COUNT(DISTINCT fc.category_id) DESC", "ORDER BY COUNT(DISTINCT fc.category_id) ASC"),
                              ("reverse-ties", "c.customer_id ASC", "c.customer_id DESC")]}
        for label, before, after in changes.get(qid, []):
            variants.append({"mutation_id": qid + "-" + label, "sql": legacy.replace_expression(sql, before, after),
                             "kind": "ordering_or_top_k_contract", "origin": "requirement-defined before revision-03 generation"})
        mutations[qid] = variants
    publish_artifact(output / "mutations.json", canonical_json(mutations))
    provenance = {"status": "AI_assisted_draft", "human_review_complete": False, "generation_requests": 0,
                  "source_authoring": {name: sha256_bytes((author / name).read_bytes()) for name in ("questions.jsonl", "gold.jsonl", "contracts.jsonl", "generation-instruction.txt", "intent-reference-lock.json")},
                  "reason": "User requires natural questions without output footers, column-order invariant EX and genuine ordering/top-k coverage.",
                  "q154_amendment": {"question": wording, "reason": "Blind reviewer found observed-pairs versus full-grid ambiguity; relationship now explicit in business language."},
                  "selection_basis": "Preserve existing30 IDs, structural balance and six sourced domain tasks; three ranking scope changes based on missing capability coverage, not EX.",
                  "pending": ["independent reference lock", "baseline+8 fixture reference/witness checks", "human review", "context/source/runtime freeze"]}
    publish_artifact(output / "provenance.json", canonical_json(provenance))
    print(json.dumps({"status": "versioned_draft_written", "questions": len(questions), "generation_requests": 0}))


if __name__ == "__main__":
    main()
