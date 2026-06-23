# 🏦 Banking Fraud Analytics Agent

A **multi-agent analytics system** that answers questions about 13M+ banking transactions in plain English. A generator agent writes SQL, an **adversarial reviewer agent** critiques and corrects it before execution, a **SQL safety layer** blocks destructive queries, and a **30-question eval harness** measures accuracy across difficulty tiers. Built with the Claude API, DuckDB, and Streamlit.

![Agent Performance](./eval_visualization.png)

This isn't just Text-to-SQL. It's a two-agent system (generator + adversarial reviewer) with conversation memory, a read-only SQL safety layer, and a rigorous evaluation framework — the patterns that matter for production LLM systems: tool use, multi-agent coordination, safety guardrails, and measurable quality.

![demo](./assets/demo.gif)

## Why this is more than Text-to-SQL

| Pattern | How it shows up here |
| ------- | -------------------- |
| **Tool use** | The LLM decides on an action (a SQL query), executes it against a real 13M-row database, and reasons over the result — the core agentic primitive. |
| **Multi-agent coordination** | A second Claude instance acts as an adversarial reviewer, catching GROUP BY errors, NULL-handling bugs, and aggregation mistakes *before* execution. |
| **Safety guardrails** | A read-only validation layer blocks destructive SQL (DROP/DELETE/UPDATE) before it ever reaches the database, independent of the LLM. |
| **Memory** | Multi-turn dialogue: follow-ups like "just show the top 3" or "break that down by card type" resolve against prior context. |
| **Evaluation** | A 30-question benchmark with ground-truth SQL across 6 categories — the rarest and most valuable skill: proving the system actually works. |

## How it works

```
User question (plain English)
        │
        ▼
  Generator agent (Claude)  ──►  proposes SQL
        │
        ▼
  Safety validation  ──►  block destructive SQL (DROP/DELETE/…) before execution
        │
        ▼
  Adversarial reviewer (Claude)  ──►  critiques: GROUP BY? NULLs? aggregation?
        │                                   │
        │ approved                          │ flagged → corrected SQL → re-validated
        ▼                                   ▼
  Execute against DuckDB (13M+ rows, read-only)
        │
        ▼
  Claude interprets results  ──►  natural-language insight (+ memory for follow-ups)
```

## AI Engineering Decisions

The design choices behind the system, and why each one is there:

- **Adversarial reviewer (a second LLM call).** SQL generation is error-prone — an LLM can pick the wrong join type, forget an `amount > 0` filter, or use `SUM` where `AVG` is correct for a rate. Rather than trust one-shot generation, a second Claude instance critiques the SQL *before* execution and returns a corrected version when it finds a problem. Separating generation from evaluation is the core reliability move: the same pattern shows up across production LLM systems, and here it auto-corrects 3–9 queries per eval run.

- **SQL safety layer (deterministic, not the LLM).** The reviewer checks *correctness*; a separate `validate_sql` layer checks *safety*. It rejects anything that isn't a read-only `SELECT`/`WITH`, blocks DDL/DML keywords (DROP, DELETE, UPDATE, …), and refuses stacked statements — so a hallucinated destructive query can never reach the database. This runs on both the generated SQL and the reviewer's fixed SQL, since both are model output. Paired with a **read-only DuckDB connection**, it's defense in depth: even if validation missed something, the connection itself can't mutate data.

- **Conversation memory.** The agent keeps the full dialogue plus the last query and result, so follow-ups like "just show the top 3" or "break that down by card type" resolve against prior context instead of starting fresh. This is what turns a single-shot Text-to-SQL tool into an analytical conversation.

- **Evaluation harness.** Quality is measured, not asserted. A 30-question benchmark with ground-truth SQL spans six categories and three difficulty tiers; each answer is scored against expected results. Running the eval *with and without* the reviewer quantifies the reviewer's actual impact rather than assuming it helps.

- **Modules over notebooks.** Core logic lives in a `src/` package (`agents/`, `sql/`, `memory/`, `eval/`) as single-purpose, importable, testable functions — dependencies (DB connection, API client, schema) are injected, not global. The original notebooks are retained under `notebooks/` as exploration artifacts, but the system runs from modules with a `tests/` suite covering the safety layer.

## Features

- **Natural Language to SQL** — Ask any question about the fraud dataset; the generator agent writes and executes the SQL.
- **Adversarial Reviewer** — A second Claude instance reviews every query before execution, auto-fixing common errors (3–9 queries auto-corrected per eval run).
- **SQL Safety Layer** — Read-only validation blocks destructive SQL before it reaches the database; unit-tested.
- **Conversation Memory** — Multi-turn dialogue; follow-up questions reference previous context automatically.
- **Eval Framework** — 30-question benchmark across 6 categories (basic, aggregation, join, fraud, customer, trend) with ground-truth validation.
- **Streamlit UI** — Interactive web app with real-time reviewer-activity tracking.

## Eval Results

| Metric | Result |
| ------ | ------ |
| Overall Accuracy | 96.7% – 100% across runs |
| Easy Questions | 5/5 (100%) |
| Medium Questions | 10/10 (100%) |
| Hard Questions | 14–15/15 (93–100%) |
| Queries Auto-fixed by Reviewer | 3–9 per run |

The reviewer's auto-fix count is itself a result: it quantifies how often the adversarial step caught a bug the generator would have shipped.

## Limitations

Honest constraints and what a production version would need:

- **Synthetic dataset.** The data is a Kaggle synthetic banking dataset, not real transactions — fraud patterns here are generated, so findings illustrate the system's capability rather than real-world fraud insight.
- **LLM cost per query.** Each question makes multiple Claude calls (generate + review + interpret, more with memory), so cost scales with usage. A production deployment would need caching, cost monitoring, and rate limiting.
- **SQL hallucination risk is reduced, not eliminated.** The adversarial reviewer and safety layer catch many errors, but an LLM can still produce subtly wrong (yet valid and safe) SQL that returns a plausible wrong answer. The eval harness measures this risk; it doesn't remove it.
- **Permission guardrails.** The safety layer enforces read-only access, but a real deployment over sensitive data would also need authentication, per-user authorization, row-level access controls, and audit logging — none of which are in scope for this portfolio project.

## Dataset

[Financial Transactions Dataset](https://www.kaggle.com/datasets/computingvictor/transactions-fraud-datasets) from Kaggle — a synthetic banking dataset covering the 2010s.

| Table | Rows | Description |
| ----- | ---- | ----------- |
| transactions | 13.3M | Core fact table with amount, merchant, payment method |
| cards | 6,146 | Card details per customer |
| users | 2,000 | Customer demographics and income |
| mcc_codes | 109 | Merchant category code descriptions |
| fraud_labels | 8.9M | Binary fraud labels (0.15% fraud rate) |

## Tech Stack

- **Claude API** (claude-sonnet-4-5) — SQL generation, adversarial review, insight interpretation
- **DuckDB** — In-process analytical database for fast queries on 13M+ rows
- **Streamlit** — Web UI
- **Pandas** — Data manipulation and display
- **pytest** — Unit tests for the SQL safety layer

## Setup

### 1. Clone and install

```bash
git clone https://github.com/IsabellaCcc/fraud-analytics-agent.git
cd fraud-analytics-agent
pip install -r requirements.txt   # or: anthropic duckdb pandas streamlit python-dotenv kaggle pytest
```

### 2. Download the dataset

```bash
kaggle datasets download -d computingvictor/transactions-fraud-datasets
unzip transactions-fraud-datasets.zip -d ./data
```

### 3. Configure environment

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your_api_key_here
```

### 4. Build the database

Run `notebooks/01_setup.ipynb` end-to-end. This cleans the raw CSVs and loads all 5 tables into a local DuckDB database at `./data/fraud_analytics.db`.

### 5. Run the app

```bash
streamlit run app.py
```

Open <http://localhost:8501> in your browser.

### 6. Run the tests

```bash
pytest tests/ -v
```

## Example Queries

**Single-turn:**
- *"Which merchant categories have the highest fraud rates?"*
- *"Compare fraud rates for Visa vs Mastercard"*
- *"What is the average transaction amount by card type?"*

**Multi-turn (memory in action):**
- *"Which states have the highest fraud rates?"*
- → *"Just show the top 3 and add absolute fraud counts"*
- → *"For those states, break it down by card type"*
- → *"Now show me fraud by hour of day instead"*
- → *"Filter to late night hours only (10pm to 4am)"*

## Project Structure

```
fraud-analytics-agent/
├── src/
│   ├── pipeline.py             # Orchestration: generate → validate → review → execute → interpret
│   ├── schema.py               # Schema-context loader
│   ├── agents/
│   │   ├── generator.py        # SQL-generation agent
│   │   └── reviewer.py         # Adversarial reviewer agent
│   ├── sql/
│   │   ├── executor.py         # DuckDB execution
│   │   ├── extract.py          # Pull SQL from the model reply
│   │   └── validation.py       # Read-only SQL safety layer
│   ├── memory/
│   │   └── conversation.py     # Multi-turn agent with memory
│   └── eval/
│       ├── eval_questions.py   # 30-question benchmark set
│       └── harness.py          # Eval runner + reporting
├── tests/
│   └── test_validation.py      # Unit tests for the safety layer
├── notebooks/                  # Original exploration notebooks (setup, agent, eval, viz, memory)
├── schema_docs/                # Table schema reference injected into agent prompts
├── app.py                      # Streamlit UI (imports from src/)
└── data/                       # DuckDB database (gitignored)
```
