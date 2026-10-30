"""Create parity fixtures with the hash-verified upstream component routines.

Run once when deliberately updating the source lock; unit tests use the frozen
JSON and never download/import the upstream evaluator or its SQLite parser.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    lock = json.loads((ROOT / "research/revision-02/spider-source-lock.json").read_bytes())
    source = (ROOT / "runs/revision-02/sources/spider/evaluation.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != lock["files"][0]["sha256"]:
        raise ValueError("Upstream source hash mismatch")
    parsed = ast.parse(source)
    names = {"has_agg", "count_agg", "get_nestedSQL", "count_component1", "count_component2", "count_others"}
    body = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in names]
    evaluator = next(node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name == "Evaluator")
    body.append(next(node for node in evaluator.body if isinstance(node, ast.FunctionDef) and node.name == "eval_hardness"))
    namespace = {"AGG_OPS": ("none", "max", "min", "count", "sum", "avg"),
                 "WHERE_OPS": ("not", "between", "=", ">", "<", ">=", "<=", "!=", "in", "like", "is", "exists")}
    exec(compile(ast.Module(body=body, type_ignores=[]), "hash-verified-spider-routines", "exec"), namespace)

    def query(*, selections=1, aggs=0, tables=1, where=0, group=0, order=False, limit=False,
              ors=0, likes=0, negated=0, nested=0, union=False, order_agg=False):
        col = (0, "column", False)
        result = {"select": (False, [(3 if i < aggs else 0, (0, col, None)) for i in range(selections)]),
                  "from": {"table_units": [("table_unit", i) for i in range(tables)], "conds": []},
                  "where": [], "groupBy": [col] * group, "orderBy": ("asc", [(0, (4 if order_agg else 0, "column", False), None)]) if order else [],
                  "limit": 5 if limit else None, "having": [], "intersect": None, "except": None, "union": None}
        for i in range(where):
            if i:
                result["where"].append("or" if i <= ors else "and")
            result["where"].append((i < negated, 9 if i < likes else 2, (0, col, None), query() if i < nested else 1, None))
        if union:
            result["union"] = query()
        return result

    cases = [
        ("simple_projection", "SELECT film_id FROM film", query()),
        ("one_filter_aggregate", "SELECT COUNT(*) FROM film WHERE length > 120", query(aggs=1, where=1)),
        ("multiple_columns", "SELECT film_id,title FROM film", query(selections=2)),
        ("two_filters", "SELECT film_id FROM film WHERE length>120 AND rental_rate>2", query(where=2)),
        ("or_component", "SELECT film_id FROM film WHERE length>120 OR rental_rate>2", query(where=2, ors=1)),
        ("like_component", "SELECT film_id FROM film WHERE title LIKE 'A%'", query(where=1, likes=1)),
        ("group_join_medium", "SELECT c.category_id,COUNT(fc.film_id) FROM category c JOIN film_category fc ON c.category_id=fc.category_id GROUP BY c.category_id", query(selections=2, aggs=1, tables=2, group=1)),
        ("group_two_columns_edge", "SELECT c.category_id,c.name,COUNT(fc.film_id) FROM category c JOIN film_category fc ON c.category_id=fc.category_id GROUP BY c.category_id,c.name", query(selections=3, aggs=1, tables=2, group=2)),
        ("order_limit", "SELECT film_id FROM film ORDER BY film_id LIMIT 5", query(order=True, limit=True)),
        ("three_components", "SELECT film_id FROM film WHERE length>120 ORDER BY film_id LIMIT 5", query(where=1, order=True, limit=True)),
        ("four_components", "SELECT f.film_id FROM film f JOIN inventory i ON f.film_id=i.film_id WHERE f.length>120 ORDER BY f.film_id LIMIT 5", query(tables=2, where=1, order=True, limit=True)),
        ("nested_simple_outer", "SELECT film_id FROM film WHERE rental_rate > (SELECT AVG(rental_rate) FROM film)", query(where=1, nested=1)),
        ("nested_multiple_projection", "SELECT film_id,title FROM film WHERE rental_rate > (SELECT AVG(rental_rate) FROM film)", query(selections=2, where=1, nested=1)),
        ("two_nested", "SELECT film_id FROM film WHERE length>(SELECT AVG(length) FROM film) AND rental_rate>(SELECT AVG(rental_rate) FROM film)", query(where=2, nested=2)),
        ("union", "SELECT film_id FROM film UNION SELECT film_id FROM inventory", query(union=True)),
        ("multiple_aggregates", "SELECT MIN(length),MAX(length) FROM film", query(selections=2, aggs=2)),
        ("not_flag_quirk", "SELECT COUNT(*) FROM film WHERE NOT length=120", query(aggs=1, where=1, negated=1)),
        ("ordered_aggregate", "SELECT customer_id,SUM(amount) FROM payment GROUP BY customer_id ORDER BY SUM(amount)", query(selections=2, aggs=1, group=1, order=True, order_agg=True)),
        ("three_other_flags", "SELECT customer_id,staff_id,SUM(amount),MAX(amount) FROM payment WHERE amount>1 AND staff_id=1 GROUP BY customer_id,staff_id", query(selections=4, aggs=2, where=2, group=2)),
    ]
    records = []
    for name, sql, ir in cases:
        records.append({"name": name, "sql": sql, "upstream_ir": ir,
                        "component1": namespace["count_component1"](ir), "component2": namespace["count_component2"](ir),
                        "others": namespace["count_others"](ir), "spider_level": namespace["eval_hardness"](None, ir)})
    path = ROOT / "tests/fixtures/spider-components-v2.json"
    path.write_text(json.dumps({"source_commit": lock["commit"], "source_sha256": lock["files"][0]["sha256"],
                                "method": "Manually paired SQL/Spider IR; expected counts and labels evaluated by hash-verified upstream routines, not the MySQL adapter.",
                                "cases": records}, indent=2) + "\n")
    print(json.dumps({"fixtures": len(records), "path": str(path.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
