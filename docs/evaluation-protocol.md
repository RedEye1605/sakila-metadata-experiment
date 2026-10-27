# EX comparison protocol v1 — pending benchmark freeze

- Reference result comes from reviewed gold SQL on the same frozen database.
- Same column count, columns compared by requested position; aliases ignored.
- Unordered questions compare multisets of whole rows, preserving duplicates.
- Ordered questions compare row sequences. Questions specify deterministic tie breaking for ranking/LIMIT.
- NULL is distinct from empty string, zero, and the text NULL.
- Integers and Decimals compare exactly as rational numeric values. Integral float 1.0 equals 1; text 1 does not equal numeric 1. No universal rounding.
- Approximation is opt-in by zero-based column indices; atol=1e-9 and rtol=1e-12 by default. Unordered approximate rows require perfect bipartite matching; greedy matching is invalid. Gold preflight must satisfy the matching budget.
- Dates and datetimes preserve granularity. Aware datetimes normalize to UTC; naive datetimes remain distinct from aware instants. Binary values are losslessly encoded.
- Empty result sets can match under the same column contract. Draft gold validation rejects unintentional empty reference results.
- Hashes are audit evidence, not a replacement for comparison.
- Safety/SQL syntax errors, controlled query deadlines, wrong results, and result resource limits are model failures (EX=0). Connection/service/configuration/evaluator failures are infrastructure issues (EX=null).
- Mechanical extraction removes only whitespace and one enclosing SQL Markdown fence. Never select a query fragment, rewrite identifiers, add clauses, or feed execution errors back to the model.
- Full generated/reference results and their typed representation remain available for audit.

Agreement on one fixed database does not establish general semantic equivalence. Human semantic review of gold is separate from successful execution and self-comparison.

