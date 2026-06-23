"""
Generator agent: turns a natural-language question into SQL.

Extracted from ask_agent_v2 in the notebook. The Anthropic client and the
schema context are passed in as arguments (no module globals), so this is
importable, swappable, and testable.
"""
from anthropic import Anthropic

GENERATOR_SYSTEM_TEMPLATE = """You are a data analyst for a banking fraud analytics platform.
You have access to a DuckDB database. Given a user question, write SQL to answer it.

{schema_context}

Rules:
- Always wrap SQL in ```sql ... ``` blocks
- amount can be negative (refunds) — filter amount > 0 for spend analysis
- For fraud rate: use AVG(is_fraud)*100, not SUM
- Always INNER JOIN fraud_labels (never LEFT JOIN)
"""


def generate_sql_reply(client: Anthropic, schema_context: str, question: str,
                       model: str = "claude-sonnet-4-5") -> str:
    """Ask the model to produce a reply containing a ```sql``` block."""
    system_prompt = GENERATOR_SYSTEM_TEMPLATE.format(schema_context=schema_context)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text
