"""
Multi-turn conversation agent with memory.

Extracted from FraudAnalyticsAgent in 05_agent_with_memory.ipynb. Keeps the
full conversation history plus the last SQL/result, so follow-ups like
"just show the top 3" or "break that down by card type" resolve against prior
context.

Dependencies (Anthropic client, DuckDB connection, schema) are injected at
construction, so the class is importable and usable from the Streamlit app or
a CLI without notebook globals.
"""
from anthropic import Anthropic
import duckdb

from src.sql.extract import extract_sql
from src.sql.executor import execute_query
from src.sql.validation import validate_sql

MEMORY_SYSTEM_TEMPLATE = """You are a data analyst for a banking fraud analytics platform.
You help users explore a 13M-row financial transactions database through natural language.

{schema_context}

Rules:
- Always wrap SQL in ```sql ... ``` blocks
- amount can be negative (refunds) — filter amount > 0 for spend analysis
- For fraud rate: use AVG(is_fraud)*100, not SUM
- Always INNER JOIN fraud_labels (never LEFT JOIN)
- Limit results to 20 rows unless user asks for more
- You have memory of the full conversation — use it for follow-up questions

When the user asks a follow-up like "just show top 3", "break that down by X",
"now filter to Y", or "same but for Z" — reference the previous query context
and modify accordingly. Always show what changed.
"""


class FraudAnalyticsAgent:
    """Text-to-SQL agent that remembers the conversation across turns."""

    def __init__(self, client: Anthropic, con: duckdb.DuckDBPyConnection,
                 schema_context: str, model: str = "claude-sonnet-4-5"):
        self.client = client
        self.con = con
        self.model = model
        self.system_prompt = MEMORY_SYSTEM_TEMPLATE.format(schema_context=schema_context)
        self.conversation_history: list[dict] = []
        self.last_sql: str | None = None
        self.last_result: str | None = None
        self.turn_count = 0

    def chat(self, user_message: str) -> dict:
        """Process one turn. Returns a structured dict (no print side effects)."""
        self.turn_count += 1

        # Inject a compact reference to the previous query for follow-ups.
        if self.last_sql and self.last_result:
            context_note = (
                f"\n\n[Previous query for reference:\n```sql\n{self.last_sql}\n```\n"
                f"Result preview: {self.last_result[:300]}]"
            )
            full_message = user_message + context_note
        else:
            full_message = user_message

        self.conversation_history.append({"role": "user", "content": full_message})

        # Step 1: generate
        response = self.client.messages.create(
            model=self.model, max_tokens=1024,
            system=self.system_prompt, messages=self.conversation_history,
        )
        agent_reply = response.content[0].text

        sql = extract_sql(agent_reply)
        if sql is None:
            # No SQL — likely a clarifying question; record and return as-is.
            self.conversation_history.append({"role": "assistant", "content": agent_reply})
            return {"ok": True, "type": "clarification", "answer": agent_reply}

        # Safety check before touching the DB.
        safety = validate_sql(sql)
        if not safety.is_safe:
            self.conversation_history.append({"role": "assistant", "content": agent_reply})
            return {"ok": False, "type": "blocked", "error": safety.reason, "sql": sql}

        # Step 2: execute
        query_result = execute_query(self.con, sql)

        # Step 3: interpret (with the running history for context)
        self.conversation_history.append({"role": "assistant", "content": agent_reply})
        self.conversation_history.append({
            "role": "user",
            "content": (
                f"Query executed. Results:\n{query_result}\n\nPlease summarize the findings "
                "in 2-3 sentences, and if this is a follow-up question, highlight what "
                "changed compared to the previous result."
            ),
        })
        interpretation = self.client.messages.create(
            model=self.model, max_tokens=512,
            system=self.system_prompt, messages=self.conversation_history,
        )
        final_answer = interpretation.content[0].text

        self.conversation_history.append({"role": "assistant", "content": final_answer})
        self.last_sql = sql
        self.last_result = query_result

        return {
            "ok": True, "type": "answer",
            "sql": sql, "result": query_result, "insight": final_answer,
        }

    def reset(self):
        """Start a fresh conversation."""
        self.conversation_history = []
        self.last_sql = None
        self.last_result = None
        self.turn_count = 0
