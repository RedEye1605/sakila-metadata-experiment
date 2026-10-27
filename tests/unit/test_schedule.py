from collections import Counter, defaultdict

import pytest

from sakila_experiment.config import ExperimentConfig
from sakila_experiment.contracts import DatasetError, Question
from sakila_experiment.experiment.schedule import build_schedule


def questions():
    return tuple(Question(question_id=f"Q{i+1:03d}", question=f"Pertanyaan fixture terpisah nomor {i+1}.", complexity=("simple", "medium", "complex")[i // 10]) for i in range(30))


def test_main_plan_is_complete_balanced_and_reproducible():
    config = ExperimentConfig()
    plan = build_schedule(questions(), config)
    assert plan == build_schedule(tuple(reversed(questions())), config)
    assert len(plan) == len({t.trial_id for t in plan}) == 600
    assert Counter(t.scenario_id for t in plan) == {s: 150 for s in config.scenario_ids}
    assert Counter(t.complexity for t in plan) == {c: 200 for c in ("simple", "medium", "complex")}
    for repetition in range(1, 6):
        block = [t for t in plan if t.repetition_id == repetition]
        assert Counter(t.scenario_id for t in block) == {s: 30 for s in config.scenario_ids}
    seeds = defaultdict(set)
    for trial in plan:
        seeds[(trial.question_id, trial.repetition_id)].add(trial.inference_seed)
        assert 0 <= trial.inference_seed < 2147483647
    assert all(len(values) == 1 for values in seeds.values())


def test_order_seed_changes_order_but_not_assignments_or_inference_seeds():
    first = build_schedule(questions(), ExperimentConfig())
    second = build_schedule(questions(), ExperimentConfig(order_seed=9))
    assert [t.trial_id for t in first] != [t.trial_id for t in second]
    assert {t.trial_id: t.inference_seed for t in first} == {t.trial_id: t.inference_seed for t in second}


def test_pilot_and_main_question_ids_cannot_be_mixed():
    with pytest.raises(DatasetError):
        build_schedule(questions(), ExperimentConfig(), pilot=True)
    pilot = (Question(question_id="P001", question="Berapa banyak film pada fixture pilot?", complexity="simple"),)
    assert len(build_schedule(pilot, ExperimentConfig(), pilot=True)) == 4
    with pytest.raises(DatasetError):
        build_schedule(pilot, ExperimentConfig())


def test_generation_contract_excludes_metadata_hints_and_gold():
    question = questions()[0]
    assert question.generation_input().model_dump() == {"question": question.question}

