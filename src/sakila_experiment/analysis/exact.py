"""Exact paired sign-flip distribution for revision-02's discrete scores.

All question blocks, including zeros, remain in the probability denominator.
This does not relax the paired-swap invariance assumption under the null.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations

from .statistics import AnalysisError, holm_adjust, paired_analysis, question_counts


def exact_sign_flip(differences: list[int]) -> dict:
    if not differences or any(type(value) is not int for value in differences):
        raise AnalysisError("Exact differences must be a nonempty integer list")
    if len(differences) > 1000 or sum(abs(value) for value in differences) > 10000:
        raise AnalysisError("Exact distribution exceeds the declared bounded calculation")
    distribution = Counter({0: 1})
    for difference in differences:
        updated = Counter()
        for total, multiplicity in distribution.items():
            updated[total + difference] += multiplicity
            updated[total - difference] += multiplicity
        distribution = updated
    threshold = abs(sum(differences))
    denominator = 2 ** len(differences)
    numerator = sum(count for total, count in distribution.items() if abs(total) >= threshold)
    if sum(distribution.values()) != denominator:
        raise AnalysisError("Exact distribution probability mass is inconsistent")
    return {"p_value": numerator / denominator, "exact_numerator": numerator, "exact_denominator": denominator,
            "question_blocks": len(differences), "discordant_blocks": sum(value != 0 for value in differences),
            "absolute_sum_statistic": threshold, "method": "two-sided exact whole-question sign flips, inclusive tail"}


def paired_analysis_v2(records: list[dict], *, seed: int = 2026102802,
                       permutations_count: int = 100000, bootstrap_count: int = 10000) -> dict:
    report = paired_analysis(records, seed=seed, permutations_count=permutations_count, bootstrap_count=bootstrap_count)
    _, counts, _ = question_counts(records)
    for contrast, (left, right) in zip(report["contrasts"], combinations(range(4), 2), strict=True):
        exact = exact_sign_flip([int(value) for value in counts[:, right] - counts[:, left]])
        contrast.pop("p_value_holm")
        contrast["monte_carlo_sensitivity_p_value"] = contrast.pop("p_value")
        contrast.update(exact)
    for contrast, adjusted in zip(report["contrasts"], holm_adjust([c["p_value"] for c in report["contrasts"]]), strict=True):
        contrast["p_value_holm"] = adjusted
    report["protocol"] = "paired-question-permutation-exact-v2"
    report["limitations"].append("Exact sign-flip inference assumes paired-swap invariance, not merely equal means. Review remains draft; inference is conditional/exploratory.")
    return report
