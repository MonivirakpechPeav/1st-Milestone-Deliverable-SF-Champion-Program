"""Common helpers for service modules."""
import re
import pandas as pd


def safe_id(name: str) -> str:
    """Validate a Snowflake identifier (alphanum + _ + $)."""
    if not re.match(r"^[A-Za-z0-9_$]+$", name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip surrounding quotes and uppercase all DataFrame columns in place."""
    df.columns = df.columns.str.strip('"').str.upper()
    return df


def schema_filter(schema: str | None, col: str = "TABLE_SCHEMA") -> str:
    """Return ``AND <col> = '<schema>'`` or empty string."""
    return f"AND {col} = '{safe_id(schema)}'" if schema else ""


def exec_sql(conn, sql: str) -> tuple[bool, str | None]:
    """Execute a SQL statement; return (ok, error)."""
    try:
        conn.session().sql(sql).collect()
        return True, None
    except Exception as e:
        return False, str(e)


def clean_db(database: str) -> str:
    """Strip quotes from a database name (for use inside double-quoted ids)."""
    return database.replace('"', '').replace("'", "")
