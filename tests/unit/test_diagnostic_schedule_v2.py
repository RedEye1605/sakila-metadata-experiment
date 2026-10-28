from collections import Counter
from dataclasses import asdict

import pytest

from sakila_experiment.config import ExperimentConfig
from sakila_experiment.contracts import DatasetError, Question
from sakila_experiment.experiment.diagnostics import VARIANTS, diagnostic_schedule


def questions():
    return tuple(Question(question_id=f"P{i:03}", question=f"Pertanyaan diagnostik nomor {i}?", complexity="simple") for i in range(101, 113))


def test_diagnostic_has_180_independent_assignments_with_separate_variant_identity():
    settings = ExperimentConfig(order_seed=2026102801, inference_seed_base=2026102803)
    result = diagnostic_schedule(questions(), settings)
    assert result == diagnostic_schedule(questions(), settings)
    assert len({row.trial_id for row in result}) == len(result) == 180
    assert Counter(row.variant_id for row in result) == {variant: 36 for variant in VARIANTS}
    for repetition in range(1, 4):
        rows = [row for row in result if row.repetition_id == repetition]
        assert len(rows) == 60 and Counter(row.variant_id for row in rows) == {variant: 12 for variant in VARIANTS}
        for question in questions():
            block = [row for row in rows if row.question_id == question.question_id]
            assert len({row.inference_seed for row in block}) == 1
    assert set(asdict(result[0])) >= {"variant_id", "scenario_id", "trial_id", "question_id"}
    assert not any(row.scenario_id in {"S0", "S1", "S2", "S3"} for row in result)


def test_diagnostic_never_accepts_main_or_duplicate_ids():
    items = list(questions())
    items[0] = items[1]
    with pytest.raises(DatasetError):
        diagnostic_schedule(tuple(items), ExperimentConfig())
    with pytest.raises(DatasetError):
        diagnostic_schedule(questions()[:9], ExperimentConfig())
