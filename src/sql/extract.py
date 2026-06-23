"""
Extract a SQL statement from an LLM reply.

The generator wraps SQL in ```sql ... ``` fences; this pulls it back out.
Factored into its own function because the same regex was duplicated across
the basic agent and the reviewer loop.
"""
import re


def extract_sql(text: str) -> str | None:
    """Return the SQL inside a ```sql ... ``` block, or None if absent."""
    match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1).strip() if match else None
