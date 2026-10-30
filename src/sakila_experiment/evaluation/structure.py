"""Versioned Spider-component profiles for canonical MySQL references.

This is an explicit MySQL AST adapter, not the original SQLite parser. It never
rewrites SQL for execution. Unsupported structures fail closed. Original v1
labels remain in evaluation.gold for reproduction of preliminary-01.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

RUBRIC_VERSION = "spider-components-mysql-v2"
UPSTREAM_COMMIT = "cccfe7bc99c4f5b7229890bbff75bfed50f2b008"


class UnsupportedStructure(ValueError):
    """Reference needs explicit review rather than a guessed complexity label."""


@dataclass(frozen=True)
class StructuralProfile:
    component1: int
    component2: int
    others: int
    spider_level: str
    complexity: str
    features: dict
    adaptations: tuple[str, ...] = ()
    rubric_version: str = RUBRIC_VERSION
    upstream_commit: str = UPSTREAM_COMMIT

    def document(self) -> dict:
        return asdict(self)


def hardness(c1: int, c2: int, other: int) -> str:
    """Ordered boundaries from the pinned upstream eval_hardness function."""
    if any(type(n) is not int or n < 0 for n in (c1, c2, other)):
        raise UnsupportedStructure("Component counts must be nonnegative integers")
    if c1 <= 1 and other == 0 and c2 == 0:
        return "easy"
    if (other <= 2 and c1 <= 1 and c2 == 0) or (c1 <= 2 and other < 2 and c2 == 0):
        return "medium"
    if ((other > 2 and c1 <= 2 and c2 == 0)
            or (2 < c1 <= 3 and other <= 2 and c2 == 0)
            or (c1 <= 1 and other == 0 and c2 <= 1)):
        return "hard"
    return "extra"


def _local_nodes(node):
    if node is None:
        return ()
    return node.walk(prune=lambda child: isinstance(child, (exp.Select, exp.SetOperation)))


def _conditions(node):
    """Flatten boolean connective nodes, retaining predicates and NOT flags."""
    if node is None:
        return []
    if isinstance(node, (exp.Where, exp.Having, exp.Paren)):
        return _conditions(node.this)
    if isinstance(node, (exp.And, exp.Or)):
        return _conditions(node.this) + _conditions(node.expression)
    return [node]


def profile_sql(sql: str) -> StructuralProfile:
    try:
        statements = [tree for tree in parse(sql, read="mysql") if tree is not None]
    except ParseError as exc:
        raise UnsupportedStructure("Reference SQL does not parse as MySQL") from exc
    if len(statements) != 1:
        raise UnsupportedStructure("Exactly one reference statement is required")
    tree = statements[0]
    if tree.find(exp.CTE, exp.Window):
        raise UnsupportedStructure("CTE/window references require an alternative canonical reference; generated SQL remains allowed")
    return _profile(tree)


def _profile(tree) -> StructuralProfile:
    operations = []
    while isinstance(tree, exp.SetOperation):
        if tree.args.get("order") or tree.args.get("limit"):
            raise UnsupportedStructure("Global set-operation order/limit is outside the adapter")
        if tree.args.get("distinct") is False:
            raise UnsupportedStructure("ALL set operations are outside the upstream subset")
        operations.append(tree.expression)
        tree = tree.this
    if not isinstance(tree, exp.Select):
        raise UnsupportedStructure("Canonical reference must be a SELECT query")
    source = tree.args.get("from_")
    joins = tree.args.get("joins") or []
    sources = ([source.this] if source else []) + [join.this for join in joins]
    if any(not isinstance(item, exp.Table) for item in sources):
        raise UnsupportedStructure("Derived FROM tables are not counted by the original hardness routine")
    for projection in tree.expressions:
        if projection.find(exp.Select, exp.Subquery, exp.SetOperation):
            raise UnsupportedStructure("Subqueries in SELECT projections are outside the upstream subset")
    where, having = tree.args.get("where"), tree.args.get("having")
    group, order, limit = tree.args.get("group"), tree.args.get("order"), tree.args.get("limit")
    clauses = [join.args.get("on") for join in joins] + [where, having]
    nodes = [node for clause in clauses for node in _local_nodes(clause)]
    nested = [node for node in nodes if isinstance(node, exp.Select)]
    nested.extend(operations)
    # Validate child scopes; their internal components do not inflate this scope.
    for child in nested:
        _profile(child)
    or_count = sum(isinstance(node, exp.Or) for node in nodes)
    like_count = sum(isinstance(node, exp.Like) for node in nodes)
    c1 = sum(bool(item) for item in (where, group, order, limit)) + max(0, len(sources) - 1) + or_count + like_count
    where_predicates = _conditions(where)
    having_predicates = _conditions(having)
    projection_aggs = []
    adaptations = set()
    for projection in tree.expressions:
        expression = projection.unalias()
        aggregates = list(expression.find_all(exp.AggFunc))
        if len(aggregates) > 1:
            raise UnsupportedStructure("Multiple aggregates within one projection need canonical review")
        projection_aggs.extend(aggregates)
        if aggregates and not isinstance(expression, exp.AggFunc):
            adaptations.add("aggregate_inside_scalar_expression")
    order_aggs = [node for node in _local_nodes(order) if isinstance(node, exp.AggFunc)]
    # Upstream count_agg reads index zero of WHERE/HAVING condition tuples,
    # which is the NOT flag, not their aggregate. Preserve and disclose it.
    negated_predicates = sum(isinstance(item, exp.Not) for item in where_predicates + having_predicates)
    if negated_predicates:
        adaptations.add("upstream_negated_condition_aggregation_quirk_preserved")
    aggregate_count = len(projection_aggs) + len(order_aggs) + negated_predicates
    group_count = len(group.expressions) if group else 0
    other_flags = {
        "multiple_aggregates": aggregate_count > 1,
        "multiple_select_expressions": len(tree.expressions) > 1,
        "multiple_where_predicates": len(where_predicates) > 1,
        "multiple_group_expressions": group_count > 1,
    }
    scalar_types = sorted({type(node).__name__ for node in tree.walk()
                           if isinstance(node, exp.Func) and not isinstance(node, exp.AggFunc)})
    if scalar_types:
        adaptations.add("mysql_scalar_functions_counted_within_existing_clause_components")
    c2, other = len(nested), sum(other_flags.values())
    level = hardness(c1, c2, other)
    features = {"tables_in_root_scope": len(sources), "join_components": max(0, len(sources) - 1),
                "where": bool(where), "group": bool(group), "order": bool(order), "limit": bool(limit),
                "or_occurrences": or_count, "like_occurrences": like_count,
                "nested_or_set_branches_in_root": c2, "select_expressions": len(tree.expressions),
                "where_predicates": len(where_predicates), "group_expressions": group_count,
                "upstream_aggregate_components": aggregate_count, "other_flags": other_flags,
                "mysql_scalar_function_types": scalar_types}
    return StructuralProfile(c1, c2, other, level, {"easy": "simple", "medium": "medium", "hard": "complex", "extra": "complex"}[level],
                             features, tuple(sorted(adaptations)))
