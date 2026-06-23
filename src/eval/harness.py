"""
Evaluation harness for the fraud analytics agent.

Extracted from 03_eval.ipynb. Runs the 30-question benchmark through the
generate -> (review) -> execute -> interpret flow, scores each answer against
expected substrings, and reports accuracy by difficulty and category. Supports
running with and without the reviewer to quantify its impact.

The 30 questions live in eval_questions.py.
"""
import pandas as pd
from anthropic import Anthropic
import duckdb

from src.agents.generator import generate_sql_reply
from src.agents.reviewer import review_sql
from src.sql.extract import extract_sql
from src.sql.executor import execute_query
from src.eval.eval_questions import EVAL_QUESTIONS


def evaluate_agent(client: Anthropic, con: duckdb.DuckDBPyConnection,
                   schema_context: str, questions: list = EVAL_QUESTIONS,
                   use_reviewer: bool = True,
                   model: str = "claude-sonnet-4-5") -> pd.DataFrame:
    """Run the full eval and return a results DataFrame."""
    results = []
    for i, q in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] {q['id']} — {q['question'][:55]}...")
        try:
            reply = generate_sql_reply(client, schema_context, q["question"], model)
            sql = extract_sql(reply)
            if sql is None:
                results.append({**_base(q), "passed": False, "status": "NO_SQL",
                                "reviewed": False, "issues": "",
                                "original_sql": "", "final_sql": "", "agent_answer": reply[:200]})
                continue

            original_sql, final_sql, reviewed, issues = sql, sql, False, ""
            if use_reviewer:
                review = review_sql(client, schema_context, sql, q["question"], model)
                reviewed = not review["approved"]
                issues = " | ".join(review["issues"]) if review["issues"] else ""
                if not review["approved"]:
                    final_sql = review["fixed_sql"]

            query_result = execute_query(con, final_sql)
            if query_result.startswith("SQL ERROR"):
                results.append({**_base(q), "passed": False, "status": "SQL_ERROR",
                                "reviewed": reviewed, "issues": issues,
                                "original_sql": original_sql, "final_sql": final_sql,
                                "agent_answer": query_result[:200]})
                continue

            interp = client.messages.create(
                model=model, max_tokens=256,
                messages=[{"role": "user",
                           "content": f"Question: {q['question']}\nResult:\n{query_result}\n"
                                      "Summarize in 1-2 sentences."}],
            )
            agent_answer = interp.content[0].text

            haystack = (agent_answer.lower() + query_result.lower())
            passed = any(exp.lower() in haystack for exp in q["expected_answer_contains"])

            results.append({**_base(q), "passed": passed,
                            "status": "PASS" if passed else "FAIL",
                            "reviewed": reviewed, "issues": issues,
                            "original_sql": original_sql, "final_sql": final_sql,
                            "agent_answer": agent_answer[:200]})
        except Exception as e:
            results.append({**_base(q), "passed": False, "status": "ERROR",
                            "reviewed": False, "issues": str(e),
                            "original_sql": "", "final_sql": "", "agent_answer": ""})
    return pd.DataFrame(results)


def _base(q: dict) -> dict:
    return {"id": q["id"], "difficulty": q["difficulty"],
            "category": q["category"], "question": q["question"]}


def print_eval_report(df: pd.DataFrame):
    total = len(df)
    passed = df["passed"].sum()
    print("=" * 55)
    print(f"  Overall Accuracy : {passed}/{total} = {passed/total*100:.1f}%")
    print("\n  By Difficulty:")
    for diff in ["easy", "medium", "hard"]:
        sub = df[df["difficulty"] == diff]
        if len(sub):
            print(f"    {diff:8s}: {sub['passed'].sum()}/{len(sub)} ({sub['passed'].sum()/len(sub)*100:.0f}%)")
    print("\n  By Category:")
    for cat in df["category"].unique():
        sub = df[df["category"] == cat]
        print(f"    {cat:12s}: {sub['passed'].sum()}/{len(sub)} ({sub['passed'].sum()/len(sub)*100:.0f}%)")
    if "reviewed" in df.columns:
        print(f"\n  Reviewer fixed  : {df['reviewed'].sum()} queries")
    print("=" * 55)
