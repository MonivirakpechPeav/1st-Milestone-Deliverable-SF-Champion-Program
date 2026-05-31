"""Horizon Catalog discovery: search across tables / views / databases.

Reads ACCOUNT_USAGE.TABLES / VIEWS / DATABASES (the same backing data
that powers Universal Search) and exposes a single text-search API.
"""
import pandas as pd

from ._common import normalize_columns, safe_id


def search_objects(conn, query: str, limit: int = 200) -> pd.DataFrame:
    """Find tables/views matching a substring across the account."""
    q = (query or "").replace("'", "''").upper()
    if not q:
        return pd.DataFrame()
    sql = f"""
        SELECT
            TABLE_CATALOG AS DATABASE_NAME,
            TABLE_SCHEMA  AS SCHEMA_NAME,
            TABLE_NAME,
            TABLE_TYPE,
            ROW_COUNT,
            BYTES,
            LAST_ALTERED,
            COMMENT
        FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
        WHERE DELETED IS NULL
          AND (UPPER(TABLE_NAME) LIKE '%{q}%'
               OR UPPER(TABLE_SCHEMA) LIKE '%{q}%'
               OR UPPER(COMMENT)      LIKE '%{q}%')
        ORDER BY LAST_ALTERED DESC NULLS LAST
        LIMIT {int(limit)}
    """
    try:
        return normalize_columns(conn.query(sql, ttl=600))
    except Exception:
        return pd.DataFrame()


def search_columns(conn, query: str, limit: int = 200) -> pd.DataFrame:
    """Find columns whose name or comment match a substring."""
    q = (query or "").replace("'", "''").upper()
    if not q:
        return pd.DataFrame()
    sql = f"""
        SELECT
            TABLE_CATALOG AS DATABASE_NAME,
            TABLE_SCHEMA  AS SCHEMA_NAME,
            TABLE_NAME, COLUMN_NAME, DATA_TYPE, COMMENT
        FROM SNOWFLAKE.ACCOUNT_USAGE.COLUMNS
        WHERE DELETED IS NULL
          AND (UPPER(COLUMN_NAME) LIKE '%{q}%'
               OR UPPER(COMMENT)  LIKE '%{q}%')
        ORDER BY DATABASE_NAME, SCHEMA_NAME, TABLE_NAME, COLUMN_NAME
        LIMIT {int(limit)}
    """
    try:
        return normalize_columns(conn.query(sql, ttl=600))
    except Exception:
        return pd.DataFrame()


def list_semantic_views(conn) -> pd.DataFrame:
    """List semantic views known to the account."""
    try:
        return normalize_columns(conn.query("SHOW SEMANTIC VIEWS IN ACCOUNT", ttl=300))
    except Exception:
        return pd.DataFrame()


def list_internal_listings(conn) -> pd.DataFrame:
    """List internal Marketplace listings (data products) the role can see."""
    try:
        return normalize_columns(
            conn.query("SHOW LISTINGS", ttl=300)
        )
    except Exception:
        return pd.DataFrame()
