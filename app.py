import streamlit as st
import duckdb
import anthropic
import re
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from dotenv import load_dotenv
matplotlib.use('Agg')
load_dotenv()

# ── Page Setting ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Fraud Analytics Agent",
    page_icon="🏦",
    layout="wide"
)

# ── Initialization ────────────────────────────────────────────────────
@st.cache_resource
def get_db():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'fraud_analytics.db')
    return duckdb.connect(db_path)

@st.cache_resource
def get_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

@st.cache_data
def get_schema():
    schema_path = os.path.join(os.path.dirname(__file__), 'schema_docs', 'schema.md')
    with open(schema_path, 'r') as f:
        return f.read()

con    = get_db()
client = get_client()
schema = get_schema()

# ── Tools Function ──────────────────────────────────────────────────
def run_query(sql: str):
    try:
        result = con.execute(sql).df()
        return result, None
    except Exception as e:
        return None, str(e)

def extract_sql(text: str):
    match = re.search(r'```sql\s*(.*?)\s*```', text, re.DOTALL)
    return match.group(1).strip() if match else None

SYSTEM_PROMPT = f"""You are a data analyst for a banking fraud analytics platform.
You help users explore a 13M-row financial transactions database through natural language.

{schema}

Rules:
- Always wrap SQL in ```sql ... ``` blocks
- amount can be negative (refunds) — filter amount > 0 for spend analysis
- For fraud rate: use AVG(is_fraud)*100, not SUM
- Always INNER JOIN fraud_labels (never LEFT JOIN)
- Limit results to 20 rows unless user asks for more
- You have memory of the full conversation — use it for follow-up questions
- When answering follow-ups like "just show top 3", "break that down by X",
  "filter to Y" — reference previous query and explain what changed
"""

# ── Session State Initialization ──────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []          # Show used chat history
if 'api_history' not in st.session_state:
    st.session_state.api_history = []       # Complete history sent to API
if 'last_sql' not in st.session_state:
    st.session_state.last_sql = None
if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'session_queries' not in st.session_state:
    st.session_state.session_queries = 0
if 'session_fixed' not in st.session_state:
    st.session_state.session_fixed = 0

# ── Main  Interface────────────────────────────────────────────────────
st.title("🏦 Banking Fraud Analytics Agent")
st.caption("Natural language queries on 13M+ banking transactions · Powered by Claude")

# Two columns layout
col_chat, col_info = st.columns([2, 1])

with col_info:
    # Database Stats
    st.subheader("📊 Database Stats")
    stats = {
        "Transactions": "13.3M",
        "Customers": "2,000",
        "Cards": "6,146",
        "Fraud Labels": "8.9M",
        "Fraud Rate": "~0.15%"
    }
    for k, v in stats.items():
        st.metric(k, v)

    st.divider()

    # Example Questions
    st.subheader("💡 Try asking...")
    examples = [
        "Which merchant categories have the highest fraud rates?",
        "Compare fraud rates for Visa vs Mastercard",
        "What's the average transaction amount by card type?",
        "Which hours of day see the most fraud?",
        "Do older customers have higher credit scores?",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state.pending_input = ex

    st.divider()

    # Eval Result
    st.subheader("🎯 Agent Performance")
    # Eval benchmark（static）
    st.metric("Benchmark Accuracy", "100%", "30-question eval set")

    # Session real time data
    q = st.session_state.session_queries
    f = st.session_state.session_fixed
    fix_rate = f"{f/q*100:.0f}%" if q > 0 else "—"

    st.metric("This Session", f"{q} queries", "since last reset")
    st.metric("Reviewer Fix Rate", fix_rate, 
          f"{f} of {q} queries fixed" if q > 0 else "no queries yet")

    st.divider()

    # Reset Button
    if st.button("🔄 New Conversation", use_container_width=True, type="secondary"):
        st.session_state.messages    = []
        st.session_state.api_history = []
        st.session_state.last_sql    = None
        st.session_state.last_result = None
        st.rerun()

with col_chat:
    # Render historical messages
    for msg in st.session_state.messages:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'].replace('$', '\\$'))
            if msg.get('was_fixed'):
                with st.expander("🔧 Reviewer fixed this query"):
                    for issue in msg.get('fix_issues', []):
                        st.caption(f"• {issue}")
            if 'sql' in msg:
                with st.expander("View SQL"):
                    st.code(msg['sql'], language='sql')
            if 'dataframe' in msg:
                st.dataframe(msg['dataframe'], use_container_width=True)

    # Click to handle the sample problem
    default_input = st.session_state.pop('pending_input', '')

    # Input box
    user_input = st.chat_input("Ask anything about the fraud data...")

    # If there are pending input from button, use it
    if default_input and not user_input:
        user_input = default_input

    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        full_message = user_input
        if st.session_state.last_sql and st.session_state.last_result is not None:
            result_preview = st.session_state.last_result.head(3).to_string(index=False)
            full_message += f"\n\n[Previous query:\n```sql\n{st.session_state.last_sql}\n```\nResult preview:\n{result_preview}]"

        st.session_state.api_history.append({"role": "user", "content": full_message})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):

                # Step 1: Generate SQL
                response = client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    messages=st.session_state.api_history
                )
                agent_reply = response.content[0].text
                sql = extract_sql(agent_reply)

                if not sql:
                    st.markdown(agent_reply)
                    st.session_state.messages.append({"role": "assistant", "content": agent_reply})
                    st.session_state.api_history.append({"role": "assistant", "content": agent_reply})

                else:
                    # Step 2: Adversarial Review
                    reviewer_prompt = f"""You are an adversarial SQL reviewer for a DuckDB banking database.

{schema}

Review this SQL query for the following question:
QUESTION: {user_input}
SQL:
```sql
{sql}
```

Check for these issues:
1. GROUP BY errors — all non-aggregated SELECT columns must appear in GROUP BY.
   CRITICAL: column aliases defined in SELECT (like fraud_rate_pct) cannot be 
   referenced in ORDER BY in DuckDB — use the full expression instead.
   Example wrong:  ORDER BY fraud_rate_pct DESC
   Example correct: ORDER BY AVG(fl.is_fraud)*100 DESC
   Also check CTEs — columns from CTEs used in ORDER BY must exist in the CTE's SELECT.
2. Column qualification — use table aliases (t.amount, fl.is_fraud, not just amount)
3. Wrong join type — INNER JOIN for fraud_labels, never LEFT JOIN
4. Missing amount filter — amount > 0 for spend analysis
5. Aggregation logic — AVG(is_fraud)*100 for fraud rate, not SUM
6. NULL handling — NULLIF for division, IS NOT NULL where needed
7. CASE WHEN columns must be in GROUP BY or wrapped in aggregation

Respond in this exact JSON format:
{{"approved": true or false, "issues": ["issue 1", "issue 2"], "fixed_sql": "corrected SQL or same SQL if no issues"}}"""

                    review_response = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=1024,
                        messages=[{"role": "user", "content": reviewer_prompt}]
                    )

                    import json
                    review_text = review_response.content[0].text
                    json_match = re.search(r'\{.*\}', review_text, re.DOTALL)
                    was_fixed = False
                    fix_issues = []

                    if json_match:
                        try:
                            review = json.loads(json_match.group())
                            if not review.get('approved', True):
                                sql = review.get('fixed_sql', sql)
                                was_fixed = True
                                fix_issues = review.get('issues', [])

                        except:
                            pass
                    
                    st.session_state.session_queries += 1
                    if was_fixed:
                        st.session_state.session_fixed += 1

                    # Step 3: Run SQL
                    df, error = run_query(sql)

                    if error:
                        err_msg = f"SQL error: {error}"
                        st.error(err_msg)
                        st.session_state.messages.append({"role": "assistant", "content": err_msg})
                        st.session_state.api_history.append({"role": "assistant", "content": err_msg})

                    else:
                        # Step 4: Generate insight
                        result_str = df.head(20).to_string(index=False)
                        st.session_state.api_history.append({"role": "assistant", "content": agent_reply})
                        st.session_state.api_history.append({
                            "role": "user",
                            "content": f"Query result:\n{result_str}\n\nSummarize in 2-3 sentences. If follow-up, note what changed."
                        })

                        interp = client.messages.create(
                            model="claude-sonnet-4-5",
                            max_tokens=512,
                            system=SYSTEM_PROMPT,
                            messages=st.session_state.api_history
                        )
                        insight = interp.content[0].text

                        # Render Result
                        cleaned_insight = insight.replace('$', '\\$')
                        st.markdown(cleaned_insight)

                        # If reviewer fixed the query，show the tip
                        if was_fixed:
                            with st.expander("🔧 Reviewer fixed this query"):
                                for issue in fix_issues:
                                    st.caption(f"• {issue}")

                        with st.expander("View SQL"):
                            st.code(sql, language='sql')

                        st.dataframe(df.head(20), use_container_width=True)

                        # Update state
                        st.session_state.api_history.append({"role": "assistant", "content": insight})
                        st.session_state.last_sql    = sql
                        st.session_state.last_result = df

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": insight,
                            "sql": sql,
                            "dataframe": df.head(20),
                            "was_fixed": was_fixed,
                            "fix_issues": fix_issues
                        })
