"""
SQL safety validation.

The adversarial reviewer (src/agents/reviewer.py) checks SQL for *correctness*
(join types, aggregation, filters). This module is the separate *safety* layer:
it blocks SQL that could damage the database, regardless of whether it's
"correct." An LLM can hallucinate a DROP/DELETE; this catches it before
execution.

These are pure functions (string in, verdict out) — which is exactly why they
are the easiest and most valuable part of the codebase to unit-test.
"""
import re
from dataclasses import dataclass

# Statements that must never run against the analytics DB. The agent is
# read-only by design: it answers questions, it never mutates data.
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "CREATE", "REPLACE", "GRANT", "REVOKE", "ATTACH", "COPY",
    "PRAGMA", "EXPORT", "INSTALL", "LOAD",
]


@dataclass
class ValidationResult:
    is_safe: bool
    reason: str | None = None  # why it was rejected (None if safe)


def _strip_sql_comments(sql: str) -> str:
    """Remove -- line comments and /* */ block comments so they can't hide
    a forbidden keyword from the checks."""
    sql = re.sub(r"--[^\n]*", " ", sql)          # line comments
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # block comments
    return sql


def validate_sql(sql: str) -> ValidationResult:
    """Return whether this SQL is safe to execute against the read-only DB.

    Rules:
      1. Must be non-empty.
      2. Must be a single statement (no stacked queries via `;`).
      3. Must start with SELECT or WITH (read-only entry points).
      4. Must contain no forbidden (mutating/DDL) keywords.
    """
    if sql is None or not sql.strip():
        return ValidationResult(False, "Empty query.")

    cleaned = _strip_sql_comments(sql).strip()

    # 2. No stacked statements. Allow a single optional trailing semicolon.
    inner = cleaned.rstrip(";")
    if ";" in inner:
        return ValidationResult(False, "Multiple statements are not allowed.")

    # 3. Read-only entry point: analytics queries start with SELECT or a CTE (WITH).
    first_token = inner.lstrip().split(None, 1)[0].upper() if inner.strip() else ""
    if first_token not in ("SELECT", "WITH"):
        return ValidationResult(
            False, f"Only SELECT/WITH queries allowed (got '{first_token or 'nothing'}')."
        )

    # 4. No forbidden keywords anywhere (word-boundary match, case-insensitive).
    upper = inner.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            return ValidationResult(False, f"Forbidden keyword detected: {kw}.")

    return ValidationResult(True)
