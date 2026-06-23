"""
End-to-end pipeline: question -> grounded answer.

Orchestrates the modules, extracted from ask_agent_v2. The full flow:

  1. GENERATE  — generator agent writes SQL (src.agents.generator)
  2. EXTRACT   — pull the SQL out of the reply (src.sql.extract)
  3. VALIDATE  — SAFETY check: block destructive SQL (src.sql.validation)  <-- new layer
  4. REVIEW    — adversarial reviewer critiques correctness (src.agents.reviewer)
  5. EXECUTE   — run the final SQL on DuckDB (src.sql.executor)
  6. INTERPRET — model summarizes the result in plain English

Returns a structured dict so callers (Streamlit, tests, CLI) decide how to
display it — no print() side effects inside the core logic.
"""
from anthropic import Anthropic
import duckdb

from src.agents.generator import generate_sql_reply, GENERATOR_SYSTEM_TEMPLATE
from src.agents.reviewer import review_sql
from src.sql.extract import extract_sql
from src.sql.validation import validate_sql
from src.sql.executor import execute_query


def answer_question(client: Anthropic, con: duckdb.DuckDBPyConnection,
                    schema_context: str, question: str,
                    model: str = "claude-sonnet-4-5") -> dict:
    """Run the full generate -> validate -> review -> execute -> interpret flow."""
    # 1. Generate
    reply = generate_sql_reply(client, schema_context, question, model)

    # 2. Extract
    sql = extract_sql(reply)
    if sql is None:
        return {"ok": False, "stage": "extract", "error": "No SQL produced.", "reply": reply}

    # 3. SAFETY validation (before anything touches the DB)
    safety = validate_sql(sql)
    if not safety.is_safe:
        return {"ok": False, "stage": "validation", "error": safety.reason, "sql": sql}

    # 4. Correctness review (adversarial reviewer)
    review = review_sql(client, schema_context, sql, question, model)
    final_sql = sql if review["approved"] else review["fixed_sql"]

    # 4b. Re-validate the reviewer's fixed SQL — it's still model output.
    if not review["approved"]:
        safety2 = validate_sql(final_sql)
        if not safety2.is_safe:
            return {"ok": False, "stage": "validation_fixed", "error": safety2.reason, "sql": final_sql}

    # 5. Execute
    result = execute_query(con, final_sql)

    # 6. Interpret
    system_prompt = GENERATOR_SYSTEM_TEMPLATE.format(schema_context=schema_context)
    interpretation = client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=[
            {"role": "user", "content": question},
            {"role": "assistant", "content": reply},
            {"role": "user", "content": f"Query result:\n{result}\n\nSummarize findings in 2-3 sentences."},
        ],
    )
    insight = interpretation.content[0].text

    return {
        "ok": True,
        "question": question,
        "sql": sql,
        "final_sql": final_sql,
        "review": review,
        "result": result,
        "insight": insight,
    }
