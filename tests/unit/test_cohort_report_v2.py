import pytest

from sakila_experiment.analysis.report import IntegrityError, cohort_descriptives


def test_descriptive_profiles_keep_question_counts_distinct_from_repetitions():
    attributes = {"Q101": {"primary_need": "schema_mapping", "spider_level": "easy", "semantic_family": "identity"},
                  "Q102": {"primary_need": "domain_integration", "spider_level": "hard", "semantic_family": "policy"}}
    rows = [{"question_id": q, "scenario_id": s, "repetition_id": r, "execution_accuracy": int(q == "Q102" and r <= 3)}
            for q in attributes for s in ("S0", "S1", "S2", "S3") for r in range(1, 6)]
    result = cohort_descriptives(rows, attributes)
    domain = [row for row in result["primary_need"] if row["profile"] == "domain_integration"]
    assert len(domain) == 4
    assert all(row["questions"] == 1 and row["trials"] == 5 and row["correct"] == 3 and row["execution_accuracy_percent"] == 60 for row in domain)
    with pytest.raises(IntegrityError, match="coverage"):
        cohort_descriptives(rows, {"Q101": attributes["Q101"]})
