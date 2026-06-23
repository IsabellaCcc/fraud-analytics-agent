"""
Streamlit UI for the fraud analytics agent.

Imports the multi-turn memory agent from src/ — all logic lives in modules;
this file only handles the chat UI and display.

Run:  streamlit run app.py
"""
import os

import duckdb
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

from src.schema import load_schema
from src.memory.conversation import FraudAnalyticsAgent

load_dotenv()

st.set_page_config(page_title="Fraud Analytics Agent", page_icon="🏦", layout="wide")
st.title("🏦 Banking Fraud Analytics Agent")
st.caption("Natural-language queries over 13M+ banking transactions · multi-agent + memory")


@st.cache_resource
def get_agent():
    """Build the agent once per session (cached across reruns)."""
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    con = duckdb.connect("./data/fraud_analytics.db", read_only=True)
    schema_context = load_schema()
    return FraudAnalyticsAgent(client, con, schema_context)


agent = get_agent()

# Render prior turns.
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Chat input.
if prompt := st.chat_input("Ask about the fraud data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generating SQL, reviewing, executing..."):
            out = agent.chat(prompt)

        if out["type"] == "answer":
            st.markdown(out["insight"])
            with st.expander("SQL & raw result"):
                st.code(out["sql"], language="sql")
                st.text(out["result"])
            display = out["insight"]
        elif out["type"] == "blocked":
            display = f"⚠️ Query blocked by safety check: {out['error']}"
            st.warning(display)
        else:  # clarification
            display = out["answer"]
            st.markdown(display)

    st.session_state.messages.append({"role": "assistant", "content": display})

with st.sidebar:
    st.header("Database Stats")
    st.metric("Transactions", "13.3M")
    st.metric("Customers", "2,000")
    st.metric("Cards", "6,146")
    st.metric("Fraud Rate", "~0.15%")
    if st.button("Reset conversation"):
        agent.reset()
        st.session_state.messages = []
        st.rerun()
