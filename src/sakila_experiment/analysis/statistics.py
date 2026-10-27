"""Prespecified question-block permutation tests and paired bootstrap.

This module never selects tests or sampling settings based on significance.
NumPy is installed through the locked optional analysis dependency group.
"""

from __future__ import annotations

from itertools import combinations, permutations

import numpy as np

SCENARIOS = ("S0", "S1", "S2", "S3")


class AnalysisError(ValueError):
    pass


def question_counts(records: list[dict], *, repetitions: int = 5):
    grouped, seen, complexity = {}, set(), {}
    for row in records:
        q, s, r = row["question_id"], row["scenario_id"], row["repetition_id"]
        if s not in SCENARIOS or type(r) is not int or not 1 <= r <= repetitions:
            raise AnalysisError("Unknown scenario or repetition")
        if (q, s, r) in seen:
            raise AnalysisError("Duplicate paired observation")
        value = row["execution_accuracy"]
        if type(value) is not int or value not in (0, 1):
            raise AnalysisError("Incomplete/infrastructure outcomes cannot enter paired analysis")
        if q in complexity and complexity[q] != row["complexity"]:
            raise AnalysisError("Question complexity changed across observations")
        complexity[q] = row["complexity"]
        seen.add((q, s, r))
        grouped.setdefault(q, {scenario: [] for scenario in SCENARIOS})[s].append(value)
    if not grouped or any(len(values) != repetitions for row in grouped.values() for values in row.values()):
        raise AnalysisError("Every question requires all four conditions and all repetitions")
    ids = sorted(grouped)
    counts = np.array([[sum(grouped[q][s]) for s in SCENARIOS] for q in ids], dtype=np.int64)
    return ids, counts, [complexity[q] for q in ids]


def holm_adjust(p_values: list[float]) -> list[float]:
    if not p_values or any(not 0 <= p <= 1 for p in p_values):
        raise AnalysisError("Invalid p-values")
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, index in enumerate(sorted(range(len(p_values)), key=p_values.__getitem__)):
        previous = max(previous, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = previous
    return adjusted


def paired_analysis(records: list[dict], *, seed: int = 20261029, permutations_count: int = 100000,
                    bootstrap_count: int = 10000, repetitions: int = 5) -> dict:
    if permutations_count < 1 or bootstrap_count < 2 or seed < 0:
        raise AnalysisError("Invalid fixed resampling configuration")
    ids, counts, labels = question_counts(records, repetitions=repetitions)
    if set(labels) != {"simple", "medium", "complex"}:
        raise AnalysisError("Stratified bootstrap requires all three complexity groups")
    n = len(ids)
    totals = counts.sum(axis=0)
    grand = totals.sum()
    # Integer statistic is a constant multiple of the planned mean-deviation
    # statistic, avoiding floating-point boundary errors in permutation counts.
    observed = int(((4 * totals - grand) ** 2).sum())
    catalog = np.array(list(permutations(range(4))), dtype=np.int64)
    generator = np.random.Generator(np.random.PCG64DXSM([seed, 0]))
    exceed = 0
    for offset in range(0, permutations_count, 1000):
        size = min(1000, permutations_count - offset)
        codes = catalog[generator.integers(0, 24, size=(size, n))]
        permuted = counts[np.arange(n)[None, :, None], codes]
        simulated = ((4 * permuted.sum(axis=1) - grand) ** 2).sum(axis=1)
        exceed += int(np.count_nonzero(simulated >= observed))
    contrasts = []
    for index, (left, right) in enumerate(combinations(range(4), 2)):
        differences = counts[:, right] - counts[:, left]
        statistic = abs(int(differences.sum()))
        generator = np.random.Generator(np.random.PCG64DXSM([seed, 1, index]))
        extreme = 0
        for offset in range(0, permutations_count, 1000):
            size = min(1000, permutations_count - offset)
            signs = 2 * generator.integers(0, 2, size=(size, n)) - 1
            extreme += int(np.count_nonzero(np.abs((signs * differences).sum(axis=1)) >= statistic))
        contrasts.append({"contrast": f"{SCENARIOS[right]} - {SCENARIOS[left]}", "left": SCENARIOS[left], "right": SCENARIOS[right],
                          "difference_pp": float(differences.mean() / repetitions * 100),
                          "p_value": (extreme + 1) / (permutations_count + 1)})
    for row, adjusted in zip(contrasts, holm_adjust([r["p_value"] for r in contrasts]), strict=True):
        row["p_value_holm"] = adjusted
    generator = np.random.Generator(np.random.PCG64DXSM([seed, 2]))
    sampled_indices = []
    for label in ("simple", "medium", "complex"):
        members = np.array([i for i, value in enumerate(labels) if value == label])
        sampled_indices.append(members[generator.integers(0, len(members), size=(bootstrap_count, len(members)))])
    samples = counts[np.concatenate(sampled_indices, axis=1)].mean(axis=1) / repetitions * 100
    intervals = np.quantile(samples, [0.025, 0.975], axis=0, method="linear")
    for row, (left, right) in zip(contrasts, combinations(range(4), 2), strict=True):
        row["confidence_interval_95_pp"] = np.quantile(samples[:, right] - samples[:, left], [0.025, 0.975], method="linear").tolist()
    return {"protocol": "paired-question-permutation-v1", "question_count": n, "question_ids": ids,
            "repetitions": repetitions, "seed": seed, "rng": "PCG64DXSM", "numpy_version": np.__version__,
            "permutations": permutations_count, "bootstrap_resamples": bootstrap_count, "alpha": 0.05,
            "omnibus": {"statistic": observed / (16 * n * n * repetitions * repetitions),
                         "integer_comparison_statistic": observed, "p_value": (exceed + 1) / (permutations_count + 1)},
            "scenarios": [{"scenario_id": s, "execution_accuracy_percent": float(totals[i] / (n * repetitions) * 100),
                           "confidence_interval_95_percent": intervals[:, i].tolist()} for i, s in enumerate(SCENARIOS)],
            "contrasts": contrasts, "interval_method": "paired question percentile bootstrap stratified by complexity; 95% pointwise, not simultaneous",
            "limitations": ["Exchangeability of condition labels under the null is an analysis assumption.",
                            "Question bootstrap describes this selected benchmark; it does not establish representativeness of all Text-to-SQL tasks.",
                            "Nonsignificance is not evidence of equivalence."]}
