import pytest

from sakila_experiment.analysis.diagnostics import diagnostic_analysis
from sakila_experiment.experiment.diagnostics import VARIANTS


def test_diagnostic_keeps_ties_and_clusters_questions_without_p_values():
    records = [{"question_id": f"P{q:03}", "scenario_id": v, "repetition_id": r,
                "execution_accuracy": int(v == "B" and q % 2 == 0)}
               for q in range(101, 113) for v in VARIANTS for r in range(1, 4)]
    result = diagnostic_analysis(records, bootstrap_count=1000)
    assert [row["difference_pp"] for row in result["contrasts"]] == [50, 0, -50, -50]
    assert result["question_blocks"] == 12
    assert all("p_value" not in row and len(row["question_differences_pp"]) == 12 for row in result["contrasts"])
    assert diagnostic_analysis(records, bootstrap_count=1000) == result
    with pytest.raises(ValueError, match="complete"):
        diagnostic_analysis(records[:-1])
