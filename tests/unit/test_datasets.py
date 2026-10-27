from collections import Counter
from pathlib import Path

from sakila_experiment.contracts import load_gold, load_questions
from sakila_experiment.evaluation.gold import structural_complexity

ROOT = Path(__file__).resolve().parents[2]


def test_draft_datasets_are_separate_balanced_and_follow_the_rubric():
    main = load_questions(ROOT / "data/public/main.questions.jsonl")
    pilot = load_questions(ROOT / "data/pilot/questions.jsonl")
    assert Counter(q.complexity for q in main) == {"simple": 10, "medium": 10, "complex": 10}
    assert Counter(q.complexity for q in pilot) == {"simple": 3, "medium": 3, "complex": 3}
    assert not {q.question_id for q in main} & {q.question_id for q in pilot}
    assert not {q.question.casefold() for q in main} & {q.question.casefold() for q in pilot}
    for questions, filename in ((main, "data/private/main.gold.jsonl"), (pilot, "data/pilot/gold.jsonl")):
        references = load_gold(ROOT / filename)
        assert {q.question_id for q in questions} == references.keys()
        for question in questions:
            reference = references[question.question_id]
            assert reference.review_status == "draft"
            assert structural_complexity(reference.sql) == question.complexity

