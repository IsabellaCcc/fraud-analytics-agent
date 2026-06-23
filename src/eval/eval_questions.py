"""The 30-question evaluation set, covering varying difficulty and business scenarios.

Extracted verbatim from 03_eval.ipynb. Each item maps a question to a ground-truth
SQL and the substrings a correct answer should contain.
"""

# An evaluation set consisting of 30 questions, covering varying levels of difficulty and business scenarios.
EVAL_QUESTIONS = [
    # ── Basic Single Table ──────────────────────────────────────────────
    {
        "id": "E01",
        "difficulty": "easy",
        "category": "basic",
        "question": "How many total transactions are in the dataset?",
        "ground_truth_sql": "SELECT COUNT(*) AS total FROM transactions",
        "expected_answer_contains": ["13305915", "13,305,915"]
    },
    {
        "id": "E02",
        "difficulty": "easy",
        "category": "basic",
        "question": "How many unique customers are there?",
        "ground_truth_sql": "SELECT COUNT(DISTINCT id) AS unique_customers FROM users",
        "expected_answer_contains": ["2000", "2,000"]
    },
    {
        "id": "E03",
        "difficulty": "easy",
        "category": "basic",
        "question": "What is the overall fraud rate as a percentage?",
        "ground_truth_sql": "SELECT ROUND(AVG(is_fraud)*100, 4) AS fraud_rate_pct FROM fraud_labels",
        "expected_answer_contains": ["0.14", "0.15"]
    },
    {
        "id": "E04",
        "difficulty": "easy",
        "category": "basic",
        "question": "What are the different card brands available?",
        "ground_truth_sql": "SELECT DISTINCT card_brand FROM cards ORDER BY card_brand",
        "expected_answer_contains": ["Visa", "Mastercard", "Amex", "Discover"]
    },
    {
        "id": "E05",
        "difficulty": "easy",
        "category": "basic",
        "question": "What payment methods are used in transactions?",
        "ground_truth_sql": "SELECT DISTINCT use_chip FROM transactions",
        "expected_answer_contains": ["Swipe", "Chip", "Online"]
    },

    # ── Aggregate Analysis ──────────────────────────────────────────────
    {
        "id": "E06",
        "difficulty": "medium",
        "category": "aggregation",
        "question": "What is the average credit score of customers?",
        "ground_truth_sql": "SELECT ROUND(AVG(credit_score), 1) AS avg_credit_score FROM users",
        "expected_answer_contains": ["6", "7"]  # 600-799 range
    },
    {
        "id": "E07",
        "difficulty": "medium",
        "category": "aggregation",
        "question": "What is the total number of fraudulent transactions?",
        "ground_truth_sql": "SELECT SUM(is_fraud) AS total_fraud FROM fraud_labels",
        "expected_answer_contains": ["13332", "13,332"]
    },
    {
        "id": "E08",
        "difficulty": "medium",
        "category": "aggregation",
        "question": "Which year had the most transactions?",
        "ground_truth_sql": """
            SELECT YEAR(CAST(date AS TIMESTAMP)) AS year, COUNT(*) AS txn_count
            FROM transactions
            GROUP BY year ORDER BY txn_count DESC LIMIT 1
        """,
        "expected_answer_contains": ["201"]  # 2010s
    },
    {
        "id": "E09",
        "difficulty": "medium",
        "category": "aggregation",
        "question": "What percentage of cards have been found on the dark web?",
        "ground_truth_sql": """
            SELECT ROUND(SUM(CASE WHEN card_on_dark_web='Yes' THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS pct
            FROM cards
        """,
        "expected_answer_contains": ["%", "percent", "pct", "."]
    },
    {
        "id": "E10",
        "difficulty": "medium",
        "category": "aggregation",
        "question": "What is the average number of credit cards per customer?",
        "ground_truth_sql": "SELECT ROUND(AVG(num_credit_cards), 2) FROM users",
        "expected_answer_contains": ["2", "3", "4"]
    },

    # ── Multiple Tables JOIN ──────────────────────────────────────────────
    {
        "id": "E11",
        "difficulty": "medium",
        "category": "join",
        "question": "What is the fraud rate by card type (Credit vs Debit)?",
        "ground_truth_sql": """
            SELECT c.card_type, ROUND(AVG(fl.is_fraud)*100, 3) AS fraud_rate_pct
            FROM transactions t
            JOIN cards c ON t.card_id = c.id
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY c.card_type ORDER BY fraud_rate_pct DESC
        """,
        "expected_answer_contains": ["Credit", "Debit"]
    },
    {
        "id": "E12",
        "difficulty": "medium",
        "category": "join",
        "question": "Which merchant category has the highest fraud rate?",
        "ground_truth_sql": """
            SELECT m.description, ROUND(AVG(fl.is_fraud)*100, 3) AS fraud_rate_pct
            FROM transactions t
            JOIN mcc_codes m ON t.mcc = m.mcc
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY m.description ORDER BY fraud_rate_pct DESC LIMIT 1
        """,
        "expected_answer_contains": ["%", "percent", "fraud"]
    },
    {
        "id": "E13",
        "difficulty": "medium",
        "category": "join",
        "question": "What is the average transaction amount for male vs female customers?",
        "ground_truth_sql": """
            SELECT u.gender, ROUND(AVG(t.amount), 2) AS avg_amount
            FROM transactions t
            JOIN users u ON t.client_id = u.id
            WHERE t.amount > 0
            GROUP BY u.gender
        """,
        "expected_answer_contains": ["Male", "Female"]
    },
    {
        "id": "E14",
        "difficulty": "medium",
        "category": "join",
        "question": "How many transactions were made using chip vs swipe vs online?",
        "ground_truth_sql": """
            SELECT use_chip, COUNT(*) AS txn_count
            FROM transactions
            GROUP BY use_chip ORDER BY txn_count DESC
        """,
        "expected_answer_contains": ["Swipe", "Chip", "Online"]
    },
    {
        "id": "E15",
        "difficulty": "medium",
        "category": "join",
        "question": "What is the fraud rate for online transactions vs chip vs swipe?",
        "ground_truth_sql": """
            SELECT t.use_chip, ROUND(AVG(fl.is_fraud)*100, 4) AS fraud_rate_pct
            FROM transactions t
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY t.use_chip ORDER BY fraud_rate_pct DESC
        """,
        "expected_answer_contains": ["Online", "Swipe", "Chip"]
    },

    # ── Fraud Analysis ──────────────────────────────────────────────
    {
        "id": "E16",
        "difficulty": "hard",
        "category": "fraud",
        "question": "What are the top 3 merchant categories by total fraud amount?",
        "ground_truth_sql": """
            SELECT m.description,
                   SUM(CASE WHEN fl.is_fraud=1 THEN t.amount ELSE 0 END) AS total_fraud_amount
            FROM transactions t
            JOIN mcc_codes m ON t.mcc = m.mcc
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            WHERE t.amount > 0
            GROUP BY m.description ORDER BY total_fraud_amount DESC LIMIT 3
        """,
        "expected_answer_contains": ["$", "fraud"]
    },
    {
        "id": "E17",
        "difficulty": "hard",
        "category": "fraud",
        "question": "Do customers with higher credit scores have lower fraud rates?",
        "ground_truth_sql": """
            SELECT
                CASE
                    WHEN u.credit_score >= 750 THEN 'Excellent (750+)'
                    WHEN u.credit_score >= 670 THEN 'Good (670-749)'
                    WHEN u.credit_score >= 580 THEN 'Fair (580-669)'
                    ELSE 'Poor (<580)'
                END AS credit_tier,
                ROUND(AVG(fl.is_fraud)*100, 4) AS fraud_rate_pct
            FROM transactions t
            JOIN users u ON t.client_id = u.id
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY credit_tier ORDER BY fraud_rate_pct DESC
        """,
        "expected_answer_contains": ["credit", "fraud"]
    },
    {
        "id": "E18",
        "difficulty": "hard",
        "category": "fraud",
        "question": "What is the average fraudulent transaction amount vs legitimate transaction amount?",
        "ground_truth_sql": """
            SELECT fl.is_fraud,
                   ROUND(AVG(t.amount), 2) AS avg_amount,
                   COUNT(*) AS txn_count
            FROM transactions t
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            WHERE t.amount > 0
            GROUP BY fl.is_fraud
        """,
        "expected_answer_contains": ["fraud", "legitimate", "$"]
    },
    {
        "id": "E19",
        "difficulty": "hard",
        "category": "fraud",
        "question": "Which hour of the day has the highest fraud rate?",
        "ground_truth_sql": """
            SELECT HOUR(CAST(date AS TIMESTAMP)) AS hour,
                   ROUND(AVG(fl.is_fraud)*100, 4) AS fraud_rate_pct,
                   COUNT(*) AS total_txns
            FROM transactions t
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY hour ORDER BY fraud_rate_pct DESC LIMIT 5
        """,
        "expected_answer_contains": ["hour", "AM", "PM", ":00"]
    },
    {
        "id": "E20",
        "difficulty": "hard",
        "category": "fraud",
        "question": "What percentage of fraud occurs on transactions with errors?",
        "ground_truth_sql": """
            SELECT
                CASE WHEN t.errors IS NULL THEN 'No Error' ELSE 'Has Error' END AS error_flag,
                COUNT(*) AS total,
                ROUND(AVG(fl.is_fraud)*100, 3) AS fraud_rate_pct
            FROM transactions t
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY error_flag
        """,
        "expected_answer_contains": ["error", "Error", "%"]
    },

    # ── Customer Persona ──────────────────────────────────────────────
    {
        "id": "E21",
        "difficulty": "hard",
        "category": "customer",
        "question": "What is the gender breakdown of customers?",
        "ground_truth_sql": """
            SELECT gender, COUNT(*) AS count,
                   ROUND(COUNT(*)*100.0/(SELECT COUNT(*) FROM users), 1) AS pct
            FROM users GROUP BY gender
        """,
        "expected_answer_contains": ["Male", "Female"]
    },
    {
        "id": "E22",
        "difficulty": "hard",
        "category": "customer",
        "question": "What is the average yearly income of customers who experienced fraud vs those who didn't?",
        "ground_truth_sql": """
            SELECT
                MAX(fl.is_fraud) AS had_fraud,
                ROUND(AVG(u.yearly_income), 0) AS avg_income
            FROM users u
            JOIN transactions t ON u.id = t.client_id
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY u.id
            ORDER BY had_fraud DESC
        """,
        "expected_answer_contains": ["income", "$", "fraud"]
    },
    {
        "id": "E23",
        "difficulty": "hard",
        "category": "customer",
        "question": "Which age group has the most transactions?",
        "ground_truth_sql": """
            SELECT
                CASE
                    WHEN u.current_age < 30 THEN 'Under 30'
                    WHEN u.current_age < 45 THEN '30-44'
                    WHEN u.current_age < 60 THEN '45-59'
                    ELSE '60+'
                END AS age_group,
                COUNT(*) AS txn_count
            FROM transactions t
            JOIN users u ON t.client_id = u.id
            GROUP BY age_group ORDER BY txn_count DESC
        """,
        "expected_answer_contains": ["30", "45", "60"]
    },
    {
        "id": "E24",
        "difficulty": "hard",
        "category": "customer",
        "question": "What is the total debt to income ratio on average across all customers?",
        "ground_truth_sql": """
            SELECT ROUND(AVG(total_debt / NULLIF(yearly_income, 0)), 3) AS avg_dti_ratio
            FROM users
        """,
        "expected_answer_contains": ["."]
    },
    {
        "id": "E25",
        "difficulty": "hard",
        "category": "customer",
        "question": "How many customers have more than 3 credit cards?",
        "ground_truth_sql": """
            SELECT COUNT(*) AS customers_with_4plus_cards
            FROM users WHERE num_credit_cards > 3
        """,
        "expected_answer_contains": ["customer", "card"]
    },

    # ── Trend Analysis ──────────────────────────────────────────────
    {
        "id": "E26",
        "difficulty": "hard",
        "category": "trend",
        "question": "How has the total transaction volume changed year over year?",
        "ground_truth_sql": """
            SELECT YEAR(CAST(date AS TIMESTAMP)) AS year,
                   COUNT(*) AS txn_count,
                   ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS total_volume
            FROM transactions
            GROUP BY year ORDER BY year
        """,
        "expected_answer_contains": ["2010", "201"]
    },
    {
        "id": "E27",
        "difficulty": "hard",
        "category": "trend",
        "question": "Which month of the year has the highest average transaction amount?",
        "ground_truth_sql": """
            SELECT MONTH(CAST(date AS TIMESTAMP)) AS month,
                   ROUND(AVG(amount), 2) AS avg_amount
            FROM transactions WHERE amount > 0
            GROUP BY month ORDER BY avg_amount DESC LIMIT 1
        """,
        "expected_answer_contains": ["January", "February", "March", "April", "May",
                                      "June", "July", "August", "September",
                                      "October", "November", "December", "month"]
    },
    {
        "id": "E28",
        "difficulty": "hard",
        "category": "trend",
        "question": "What is the fraud rate trend by year?",
        "ground_truth_sql": """
            SELECT YEAR(CAST(t.date AS TIMESTAMP)) AS year,
                   ROUND(AVG(fl.is_fraud)*100, 4) AS fraud_rate_pct
            FROM transactions t
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY year ORDER BY year
        """,
        "expected_answer_contains": ["2010", "fraud", "%"]
    },
    {
        "id": "E29",
        "difficulty": "hard",
        "category": "trend",
        "question": "What is the most common transaction error type?",
        "ground_truth_sql": """
            SELECT errors, COUNT(*) AS count
            FROM transactions
            WHERE errors IS NOT NULL
            GROUP BY errors ORDER BY count DESC LIMIT 5
        """,
        "expected_answer_contains": ["error", "Error", "insufficient", "declined"]
    },
    {
        "id": "E30",
        "difficulty": "hard",
        "category": "trend",
        "question": "How does fraud rate differ between transactions with errors and those without?",
        "ground_truth_sql": """
            SELECT
                CASE WHEN t.errors IS NULL THEN 'No Error' ELSE 'Has Error' END AS has_error,
                COUNT(*) AS total_txns,
                ROUND(AVG(fl.is_fraud)*100, 3) AS fraud_rate_pct
            FROM transactions t
            JOIN fraud_labels fl ON t.id = fl.transaction_id
            GROUP BY has_error ORDER BY fraud_rate_pct DESC
        """,
        "expected_answer_contains": ["error", "fraud", "%"]
    },
]