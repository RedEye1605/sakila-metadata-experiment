from itertools import product

import pytest

pytest.importorskip("numpy")
from sakila_experiment.analysis.exact import exact_sign_flip, paired_analysis_v2
from sakila_experiment.analysis.statistics import AnalysisError


@pytest.mark.parametrize("values", [[0, 0, 0], [1, 2, -3], [5, 0, -1, 2], [1] * 7, [-2, -2, 1, 0]])
def test_dp_matches_independent_exhaustive_enumeration(values):
    threshold = abs(sum(values))
    extreme = sum(abs(sum(sign * value for sign, value in zip(signs, values))) >= threshold for signs in product((-1, 1), repeat=len(values)))
    result = exact_sign_flip(values)
    assert result["exact_numerator"] == extreme
    assert result["exact_denominator"] == 2 ** len(values)
    assert result["p_value"] == extreme / 2 ** len(values)


def test_zero_blocks_retained_without_changing_probability():
    original = exact_sign_flip([1] * 7)
    full = exact_sign_flip([1] * 7 + [0] * 23)
    assert original["p_value"] == full["p_value"] == .015625
    assert full["question_blocks"] == 30 and full["discordant_blocks"] == 7
    assert full["exact_denominator"] == 2 ** 30


def test_invalid_floats_and_empty_arrays_do_not_get_silently_rounded():
    for values in ([], [1.0], [True]):
        with pytest.raises(AnalysisError):
            exact_sign_flip(values)


def test_v2_exposes_exact_contrasts_and_keeps_all_tied_questions():
    records = [{"question_id": f"Q{i:03}", "complexity": label, "scenario_id": f"S{s}", "repetition_id": r,
                "execution_accuracy": int(r <= 2)} for i, label in enumerate(("simple", "medium", "complex"), 1)
               for s in range(4) for r in range(1, 6)]
    report = paired_analysis_v2(records, permutations_count=100, bootstrap_count=100)
    assert report["protocol"] == "paired-question-permutation-exact-v2"
    assert all(c["p_value"] == c["p_value_holm"] == 1 and c["exact_denominator"] == 8 for c in report["contrasts"])
