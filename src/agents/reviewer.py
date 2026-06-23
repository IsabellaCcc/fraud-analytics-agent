"""
Adversarial reviewer agent.

Extracted from review_sql in the notebook. A second model call that critiques
the generated SQL for *correctness* problems (join type, missing filters,
aggregation errors) before execution — the adversarial-reviewer pattern.

This is correctness review; it is distinct from src.sql.validation, which is
the SAFETY layer (blocking destructive SQL). Both run before execution.
"""
import json
import re

from anthropic import Anthropic

REVIEWER_TEMPLATE = """You are an adversarial SQL reviewer for a banking fraud analytics database.
Your job is to find problems in SQL queries before they return wrong answers.

{schema_context}

Review this SQL query for the following question:
QUESTION: {question}
SQL:
```sql
{sql}
```

Check for these issues:
1. **Wrong join type** — should use INNER JOIN when fraud_labels is involved (not LEFT JOIN)
2. **Missing amount filter** — spend analysis should have `amount > 0` to exclude refunds
3. **Aggregation errors** — AVG(is_fraud) for fraud rate, not SUM
4. **Wrong table used** — e.g. using raw transactions when fraud_labels join is needed
5. **NULL handling** — merchant_state includes international codes, may need filtering
6. **Ambiguous column** — check all column names exist in the schema

Respond in this exact JSON format:
{{
  "approved": true or false,
  "issues": ["issue 1", "issue 2"],
  "fixed_sql": "corrected SQL here, or same SQL if no issues",
  "confidence": "high/medium/low"
}}

Be strict. If there are any issues, set approved to false and provide fixed_sql."""


def review_sql(client: Anthropic, schema_context: str, sql: str, question: str,
               model: str = "claude-sonnet-4-5") -> dict:
    """Return the reviewer's verdict: {approved, issues, fixed_sql, confidence}.

    Falls back to approving the original SQL if the JSON can't be parsed, so a
    malformed reviewer response never blocks a legitimate query.
    """
    prompt = REVIEWER_TEMPLATE.format(
        schema_context=schema_context, question=question, sql=sql
    )
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text

    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Parse failure -> default to approving the original (fail open).
    return {"approved": True, "issues": [], "fixed_sql": sql, "confidence": "low"}
