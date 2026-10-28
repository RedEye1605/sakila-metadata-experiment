import json
from pathlib import Path

import pytest

from sakila_experiment.evaluation.structure import UnsupportedStructure, hardness, profile_sql

FIXTURES = json.loads((Path(__file__).parents[1] / "fixtures/spider-components-v2.json").read_bytes())


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=lambda c: c["name"])
def test_mysql_profile_matches_frozen_upstream_components(case):
    profile = profile_sql(case["sql"])
    assert (profile.component1, profile.component2, profile.others, profile.spider_level) == (
        case["component1"], case["component2"], case["others"], case["spider_level"])
    assert profile.upstream_commit == FIXTURES["source_commit"]


@pytest.mark.parametrize("sql", [
    "SELECT x FROM (SELECT film_id AS x FROM film) a",
    "WITH x AS (SELECT * FROM film) SELECT film_id FROM x",
    "SELECT ROW_NUMBER() OVER (ORDER BY film_id) FROM film",
    "SELECT (SELECT COUNT(*) FROM film)",
    "SELECT * FROM film; SELECT * FROM actor",
    "DELETE FROM film", "SELECT film_id FROM film UNION ALL SELECT film_id FROM inventory",
])
def test_unsupported_structures_do_not_get_fabricated_labels(sql):
    with pytest.raises(UnsupportedStructure):
        profile_sql(sql)


def test_alias_formatting_and_nested_internal_clauses_do_not_inflate_root():
    base = profile_sql("SELECT film_id FROM film WHERE length>(SELECT AVG(length) FROM film)")
    aliased = profile_sql(" SELECT f.film_id AS identifier FROM film AS f WHERE f.length > (SELECT AVG(a.length) FROM film a WHERE a.length>10) ")
    assert (base.component1, base.component2, base.others) == (aliased.component1, aliased.component2, aliased.others)


def test_scalar_rounding_wrapper_is_disclosed():
    profile = profile_sql("SELECT ROUND(AVG(amount),4) FROM payment")
    assert profile.complexity == "simple"
    assert "aggregate_inside_scalar_expression" in profile.adaptations


def test_boundaries_are_ordered_including_nonintuitive_upstream_edge():
    assert hardness(2, 0, 2) == "extra"
    assert hardness(2, 0, 3) == "hard"
    with pytest.raises(UnsupportedStructure):
        hardness(True, 0, 0)
