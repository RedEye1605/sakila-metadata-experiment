from collections import Counter
import json
from pathlib import Path
import re

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.contracts import load_gold, load_questions
from sakila_experiment.evaluation.structure import profile_sql
from sakila_experiment.generation.prompt import build_prompt
from sakila_experiment.instrument import BenchmarkManifest, SemanticContract

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data/benchmarks/revision-03/final-02"


def test_revised_questions_are_natural_and_cover_ordering_with_balanced_complexity():
    questions, gold = load_questions(DATA / "questions.jsonl"), load_gold(DATA / "gold.jsonl")
    assert len(questions) == len(gold) == 30
    assert Counter(q.complexity for q in questions) == {"simple": 10, "medium": 10, "complex": 10}
    profiles = {q.question_id: profile_sql(gold[q.question_id].sql) for q in questions}
    assert Counter(p.spider_level for p in profiles.values()) == {"easy": 10, "medium": 10, "hard": 5, "extra": 5}
    assert {qid for qid, p in profiles.items() if p.features["order"]} == {"Q128", "Q141", "Q152"}
    assert {qid for qid, p in profiles.items() if p.features["limit"]} == {"Q141", "Q152"}
    for q in questions:
        assert not re.search(r"\b(?:keluaran|select|join|having|limit)\b|\b(?:group|order)\s+by\b|[a-z]+_[a-z]+", q.question, re.I)
        assert gold[q.question_id].column_order == "permutation"
        assert gold[q.question_id].review_status == "draft"
        assert gold[q.question_id].ordered == bool(profiles[q.question_id].features["order"])


def test_actual_prompt_construction_excludes_gold_ids_and_private_output_contracts():
    questions, gold = load_questions(DATA / "questions.jsonl"), load_gold(DATA / "gold.jsonl")
    payload = {"technical_schema": {"tables": []}, "descriptions": [], "business_context": []}
    digest = sha256_bytes(canonical_json(payload))
    for question in questions:
        artifact = build_prompt(question.generation_input(), payload, digest, ROOT / "prompts/generation-v3.txt")
        messages = artifact.chat_messages()
        encoded = json.dumps(messages, ensure_ascii=False)
        assert question.question in messages[1]["content"]
        assert question.question_id not in encoded and gold[question.question_id].sql not in encoded
        assert "schema_references" not in encoded and "column_count" not in encoded
        assert "Return columns in the sequence" not in encoded and "Keluaran" not in encoded


def test_contracts_and_manifest_explicitly_bind_new_policy_without_human_approval():
    manifest = BenchmarkManifest.model_validate_json((DATA / "manifest.json").read_bytes())
    assert manifest.result_comparison == "ex-results-v3-column-permutation"
    assert manifest.human_review_status == "pending" and manifest.main_experiment_allowed is False
    contracts = [SemanticContract.model_validate_json(line) for line in (DATA / "contracts.jsonl").read_bytes().splitlines()]
    assert len(contracts) == 30 and all(c.independent_review_artifacts for c in contracts)
    assert Counter(c.primary_need for c in contracts) == {"schema_mapping": 10, "local_semantics": 14, "domain_integration": 6}
    assert all(c.human_review_status == "pending" for c in contracts)
