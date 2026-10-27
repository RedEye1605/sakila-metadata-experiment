"""Static exportable research figures using the standard Matplotlib backend."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..artifacts import publish_artifact


def plot_statistics(statistics: dict, output: Path, *, label: str) -> None:
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10, "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False}):
        fig, ax = plt.subplots(figsize=(6.4, 4.3), layout="constrained")
        for index, row in enumerate(statistics["scenarios"]):
            low, high = row["confidence_interval_95_percent"]
            ax.vlines(index, low, high, color="#246b8e", linewidth=1.5)
            ax.hlines([low, high], index - .07, index + .07, color="#246b8e", linewidth=1.5)
            ax.scatter(index, row["execution_accuracy_percent"], color="#193c50", s=40, zorder=3)
        ax.set(xticks=range(4), xticklabels=[r["scenario_id"] for r in statistics["scenarios"]],
               ylim=(-2, 102), ylabel="Execution Accuracy (%)", xlabel="Kondisi metadata", title=label)
        ax.grid(axis="y", alpha=.2)
        fig.supxlabel("95% paired question bootstrap CI, stratified by complexity", fontsize=8)
        save_figure(fig, output, "execution-accuracy")
        fig, ax = plt.subplots(figsize=(6.4, 4.5), layout="constrained")
        for index, row in enumerate(statistics["contrasts"]):
            low, high = row["confidence_interval_95_pp"]
            ax.hlines(index, low, high, color="#246b8e", linewidth=1.5)
            ax.vlines([low, high], index - .07, index + .07, color="#246b8e", linewidth=1.5)
            ax.scatter(row["difference_pp"], index, color="#193c50", s=35, zorder=3)
        ax.axvline(0, color="#777777", linestyle="--", linewidth=1)
        ax.set(yticks=range(6), yticklabels=[r["contrast"] for r in statistics["contrasts"]],
               xlabel="Perbedaan EX (percentage points)", title=label)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=.2)
        fig.supxlabel("95% pointwise paired bootstrap CI; intervals are not multiplicity-adjusted", fontsize=8)
        save_figure(fig, output, "paired-differences")


def save_figure(figure, output: Path, stem: str) -> None:
    try:
        for extension in ("png", "pdf"):
            buffer = BytesIO()
            metadata = {"CreationDate": None, "ModDate": None} if extension == "pdf" else {}
            figure.savefig(buffer, format=extension, dpi=300, metadata=metadata)
            publish_artifact(output / f"{stem}.{extension}", buffer.getvalue())
    finally:
        plt.close(figure)


def plot_descriptive(description: dict, output: Path, *, label: str) -> None:
    import numpy as np
    scenarios = ("S0", "S1", "S2", "S3")
    colors = ("#335c81", "#468a99", "#b27433")
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10, "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False}):
        fig, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
        for offset, complexity in enumerate(("simple", "medium", "complex")):
            values = [next(r["execution_accuracy_percent"] for r in description["by_complexity"] if r["scenario_id"] == s and r["complexity"] == complexity) for s in scenarios]
            ax.bar(np.arange(4) + (offset - 1) * .24, values, .24, label=complexity, color=colors[offset])
        ax.set(xticks=range(4), xticklabels=scenarios, ylim=(0, 105), ylabel="Execution Accuracy (%)", title=label)
        ax.legend(frameon=False, ncols=3); ax.grid(axis="y", alpha=.15)
        save_figure(fig, output, "complexity")
        questions = sorted({r["question_id"] for r in description["by_question"]})
        matrix = [[next(r["correct"] for r in description["by_question"] if r["question_id"] == q and r["scenario_id"] == s) for s in scenarios] for q in questions]
        fig, ax = plt.subplots(figsize=(5.5, 9), layout="constrained")
        im = ax.imshow(matrix, vmin=0, vmax=5, cmap="Blues", aspect="auto")
        ax.set(xticks=range(4), xticklabels=scenarios, yticks=range(len(questions)), yticklabels=questions, title=label)
        for i, row in enumerate(matrix):
            for j, value in enumerate(row): ax.text(j, i, str(value), ha="center", va="center", fontsize=8, color="white" if value >= 3 else "#172d40")
        fig.colorbar(im, ax=ax, label="Correct repetitions / 5", ticks=range(6))
        save_figure(fig, output, "question-consistency")
        fig, axes = plt.subplots(1, 2, figsize=(9, 4), layout="constrained")
        for ax, key, ylabel in zip(axes, ("input_tokens", "inference_latency_ms"), ("Median input tokens", "Median inference latency (s)"), strict=True):
            values = [r[key]["median"] for r in description["by_scenario"]]
            ax.bar(scenarios, [v / 1000 if key.endswith("_ms") and v is not None else v if v is not None else 0 for v in values], color="#335c81")
            for i, v in enumerate(values):
                if v is None: ax.text(i, 0, "Unavailable", rotation=90, ha="center")
            ax.set(ylabel=ylabel); ax.grid(axis="y", alpha=.15)
        fig.suptitle(label)
        save_figure(fig, output, "supporting-measurements")
