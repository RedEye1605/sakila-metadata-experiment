"""Planned descriptive paired contrasts for the separate 180-request study."""
from __future__ import annotations

from collections import Counter

import numpy as np

from ..experiment.diagnostics import VARIANTS


def diagnostic_analysis(records, *, seed=2026102802, bootstrap_count=10000):
    ids = sorted({row["question_id"] for row in records})
    cells = Counter((r["question_id"], r["scenario_id"], r["repetition_id"]) for r in records)
    expected = {(q, v, r) for q in ids for v in VARIANTS for r in range(1, 4)}
    if len(ids) != 12 or len(records) != 180 or cells.keys() != expected or set(cells.values()) != {1}:
        raise ValueError("Diagnostic analysis requires the complete paired12-by5-by3 design")
    scores = {(q, v): sum(r["execution_accuracy"] for r in records if r["question_id"] == q and r["scenario_id"] == v) / 3 for q in ids for v in VARIANTS}
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    sampled = generator.integers(0, len(ids), size=(bootstrap_count, len(ids)))
    contrasts = []
    for right, left in (("B", "A"), ("C", "A"), ("B-order1", "B"), ("B-order2", "B")):
        differences = np.array([scores[q, right] - scores[q, left] for q in ids]) * 100
        contrasts.append({"contrast": right + " minus " + left, "difference_pp": float(differences.mean()),
                          "question_differences_pp": dict(zip(ids, differences.tolist(), strict=True)),
                          "pointwise_bootstrap_interval_95_pp": np.quantile(differences[sampled].mean(axis=1), [.025, .975]).tolist()})
    return {"question_blocks": 12, "repetitions": 3, "contrasts": contrasts, "seed": seed,
            "bootstrap_count": bootstrap_count, "method": "descriptive whole-question paired percentile bootstrap; no significance tests",
            "limits": "Twelve fixed pilot questions; composition sensitivity is conditional on these inputs. Repetition and ordering can alter salience. No pure-length isolation or proof of a mechanism."}
