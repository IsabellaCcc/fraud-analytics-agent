"""
SQL execution against the DuckDB analytics database.

Pure execution: takes a connection and a SQL string, returns the result as a
formatted string (or an error string). The connection is passed in rather than
read from a global, so this is importable and testable.

Safety is handled separately by src.sql.validation.validate_sql — the pipeline
validates BEFORE calling execute_query, keeping each function single-purpose.
"""
import duckdb


def execute_query(con: duckdb.DuckDBPyConnection, sql: str) -> str:
    """Execute a (already-validated) SQL query and return results as a string."""
    try:
        result = con.execute(sql).df()
        if result.empty:
            return "Query returned no results."
        return result.to_string(index=False)
    except Exception as e:
        return f"SQL ERROR: {str(e)}"
