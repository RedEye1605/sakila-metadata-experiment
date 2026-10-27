import copy

import pytest

np = pytest.importorskip("numpy", reason="Install the locked analysis group to test paired analysis")
from sakila_experiment.analysis.statistics import AnalysisError, holm_adjust, paired_analysis, question_counts


def synthetic_records(equal=False):
    records = []
    for q, complexity in enumerate(("simple", "medium", "complex"), 1):
        for scenario in range(4):
            for repetition in range(1, 6):
                records.append({"question_id": f"Q{q:03}", "scenario_id": f"S{scenario}", "repetition_id": repetition,
                                "complexity": complexity, "execution_accuracy": int(repetition <= (2 if equal else scenario + 1))})
    return records


def test_tied_discrete_blocks_retain_questions_and_return_p_one():
    report = paired_analysis(synthetic_records(equal=True), permutations_count=100, bootstrap_count=100)
    assert report["question_count"] == 3
    assert report["omnibus"]["p_value"] == 1
    assert all(r["p_value"] == r["p_value_holm"] == 1 and r["difference_pp"] == 0 for r in report["contrasts"])


def test_paired_effect_sizes_direction_and_reproducible_resampling():
    first = paired_analysis(synthetic_records(), seed=123, permutations_count=1000, bootstrap_count=100)
    assert first == paired_analysis(synthetic_records(), seed=123, permutations_count=1000, bootstrap_count=100)
    contrast = next(row for row in first["contrasts"] if row["contrast"] == "S3 - S0")
    assert contrast["difference_pp"] == 60
    assert contrast["confidence_interval_95_pp"] == pytest.approx([60, 60])
    assert all(0 < r["p_value"] <= r["p_value_holm"] <= 1 for r in first["contrasts"])


def test_missing_duplicate_and_infrastructure_rows_are_rejected():
    records = synthetic_records()
    with pytest.raises(AnalysisError, match="all repetitions"):
        question_counts(records[:-1])
    with pytest.raises(AnalysisError, match="Duplicate"):
        question_counts(records + [records[0]])
    invalid = copy.deepcopy(records)
    invalid[0]["execution_accuracy"] = None
    with pytest.raises(AnalysisError, match="infrastructure"):
        question_counts(invalid)


def test_holm_known_example_not_six_independent_unadjusted_decisions():
    assert holm_adjust([.01, .04, .03]) == pytest.approx([.03, .06, .06])


def test_bootstrap_resamples_whole_paired_questions_not_independent_conditions():
    records = []
    for q in range(6):
        for scenario in range(4):
            for repetition in range(1, 6):
                records.append({"question_id": f"Q{q + 1:03}", "scenario_id": f"S{scenario}", "repetition_id": repetition,
                                "complexity": ("simple", "medium", "complex")[q // 2], "execution_accuracy": q % 2})
    report = paired_analysis(records, permutations_count=100, bootstrap_count=1000)
    assert report["scenarios"][0]["confidence_interval_95_percent"][0] < report["scenarios"][0]["confidence_interval_95_percent"][1]
    assert all(row["confidence_interval_95_pp"] == [0, 0] for row in report["contrasts"])
