"""
Unit tests for SQL safety validation.

Run:  pytest tests/ -v
These cover the safety layer: legitimate analytics queries pass, destructive
or malformed queries are blocked. No database or API calls needed — pure logic.
"""
from src.sql.validation import validate_sql


# ---- queries that SHOULD pass ----
def test_simple_select_is_safe():
    assert validate_sql("SELECT * FROM transactions LIMIT 5").is_safe


def test_select_with_trailing_semicolon_is_safe():
    assert validate_sql("SELECT count(*) FROM cards;").is_safe


def test_cte_with_clause_is_safe():
    sql = "WITH f AS (SELECT * FROM fraud_labels) SELECT * FROM f"
    assert validate_sql(sql).is_safe


def test_join_and_aggregation_is_safe():
    sql = (
        "SELECT c.card_brand, AVG(fl.is_fraud)*100 AS fraud_rate "
        "FROM transactions t "
        "INNER JOIN fraud_labels fl ON t.id = fl.transaction_id "
        "INNER JOIN cards c ON t.card_id = c.id "
        "GROUP BY c.card_brand"
    )
    assert validate_sql(sql).is_safe


# ---- queries that SHOULD be blocked ----
def test_drop_is_blocked():
    result = validate_sql("DROP TABLE transactions")
    assert not result.is_safe
    assert "SELECT" in result.reason or "DROP" in result.reason


def test_delete_is_blocked():
    assert not validate_sql("DELETE FROM cards WHERE id = 1").is_safe


def test_stacked_statement_is_blocked():
    # classic injection shape: a SELECT followed by a destructive statement
    result = validate_sql("SELECT * FROM cards; DROP TABLE cards")
    assert not result.is_safe
    assert "Multiple statements" in result.reason


def test_drop_hidden_in_comment_then_executed_is_blocked():
    # a comment can't smuggle past, and the real statement still isn't a SELECT
    sql = "DROP TABLE cards -- SELECT pretend"
    assert not validate_sql(sql).is_safe


def test_empty_query_is_blocked():
    assert not validate_sql("").is_safe
    assert not validate_sql("   ").is_safe


def test_update_is_blocked():
    assert not validate_sql("UPDATE cards SET card_brand = 'x'").is_safe


def test_insert_is_blocked():
    assert not validate_sql("INSERT INTO cards VALUES (1)").is_safe
