"""Fail-closed MySQL AST policy. Database privileges remain the security backstop."""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import Dialect, ErrorLevel, exp
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.scope import traverse_scope

POLICY_VERSION = "mysql-readonly-v1"
SAFE_FUNCTIONS = frozenset({
    "COUNT", "SUM", "AVG", "MIN", "MAX", "ABS", "ROUND", "FLOOR", "CEIL", "CEILING",
    "COALESCE", "NULLIF", "IF", "CASE", "CONCAT", "CONCAT_WS", "LOWER", "UPPER", "LENGTH",
    "CHAR_LENGTH", "CHARACTER_LENGTH", "SUBSTRING", "SUBSTRING_INDEX", "TRIM", "LTRIM", "RTRIM",
    "REPLACE", "LEFT", "RIGHT", "YEAR", "MONTH", "DAY", "DAY_OF_MONTH", "DAY_OF_WEEK", "DAY_OF_YEAR",
    "EXTRACT", "DATEDIFF", "DATE_DIFF", "TIMESTAMPDIFF", "TIMESTAMP_DIFF", "DATE_ADD", "DATE_SUB",
    "TIME_TO_STR", "TS_OR_DS_TO_DATE", "TS_OR_DS_TO_TIMESTAMP", "CAST", "TRY_CAST",
    "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD", "FIRST_VALUE", "LAST_VALUE", "NTH_VALUE",
    "GROUP_CONCAT", "GREATEST", "LEAST", "MOD", "POWER", "SQRT", "SIGN", "IFNULL", "EXISTS",
    "AND", "OR", "XOR",
})
# Native pure-function alternatives required by the versioned instrument.
# Names are SQLGlot's normalized sql_name, checked against MySQL8.4 docs and
# the pinned parser. Unknown/qualified functions still fail closed. ALL/ANY
# are comparison AST nodes, not scalar functions to blanket-whitelist.
SAFE_FUNCTIONS_V2 = SAFE_FUNCTIONS | frozenset({
    "HOUR", "MINUTE", "SECOND", "DAYNAME", "FIND_IN_SET", "STR_POSITION",
    "REGEXP_LIKE", "STR_TO_DATE", "LAST_DAY",
})
FORBIDDEN_NODES = frozenset({
    "Command", "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "TruncateTable",
    "Into", "Lock", "Hint", "Parameter", "SessionParameter", "PropertyEQ", "Set", "Transaction",
    "Commit", "Rollback", "Execute", "Copy", "LoadData", "Grant", "Revoke", "Use", "Pragma",
})


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    code: str
    sql: str


def extract_sql(content: str) -> str:
    """Remove only whitespace and one whole-response SQL code fence."""
    text = content.strip()
    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].strip().lower() in {"```", "```sql", "```mysql"} and lines[-1].strip() == "```":
        if any(line.strip().startswith("```") for line in lines[1:-1]):
            return text
        return "\n".join(lines[1:-1]).strip()
    return text


def validate_sql(sql: str, tables: frozenset[str], database: str = "sakila", *, policy_version: str = POLICY_VERSION) -> ValidationResult:
    def rejected(code: str) -> ValidationResult:
        return ValidationResult(False, code, sql)

    if policy_version not in {"mysql-readonly-v1", "mysql-readonly-v2"}:
        return rejected("unknown_sql_policy")
    safe_functions = SAFE_FUNCTIONS_V2 if policy_version == "mysql-readonly-v2" else SAFE_FUNCTIONS

    if not sql.strip():
        return rejected("empty_output")
    if len(sql) > 65536 or "\x00" in sql:
        return rejected("invalid_sql_size_or_encoding")
    try:
        tokens = Dialect.get_or_raise("mysql").tokenize(sql)
        if any(comment.lstrip().startswith(("!", "+")) for token in tokens for comment in token.comments):
            return rejected("executable_comment_or_hint")
        statements = [tree for tree in sqlglot.parse(sql, read="mysql", error_level=ErrorLevel.RAISE) if tree is not None]
        if len(statements) != 1:
            return rejected("statement_count")
        tree = statements[0]
        if not isinstance(tree, (exp.Select, exp.SetOperation, exp.Subquery)):
            return rejected("statement_type")
        if not tree.find(exp.Select):
            return rejected("statement_type")
        for node in tree.walk():
            if type(node).__name__ in FORBIDDEN_NODES:
                return rejected("unsafe_construct")
            if isinstance(node, exp.Func):
                name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name().upper()
                if name not in safe_functions:
                    return rejected("function_not_allowed")
                if isinstance(node.parent, exp.Dot):
                    return rejected("qualified_function")
        for scope in traverse_scope(tree):
            for source in scope.sources.values():
                if isinstance(source, exp.Table):
                    if not isinstance(source.this, exp.Identifier):
                        return rejected("table_function")
                    if source.catalog or (source.db and source.db != database) or source.name not in tables:
                        return rejected("table_not_allowed")
        # Reject catalog references even inside scopes the optimizer cannot resolve.
        for table in tree.find_all(exp.Table):
            if table.catalog or (table.db and table.db != database):
                return rejected("table_not_allowed")
    except (SqlglotError, RecursionError, ValueError, TypeError):
        return rejected("parse_error")
    return ValidationResult(True, "accepted", sql)

