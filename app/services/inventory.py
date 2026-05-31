"""Table inventory and documentation coverage."""
import pandas as pd

from ._common import normalize_columns, safe_id, schema_filter


def get_table_inventory(conn, database: str, schema: str | None = None) -> pd.DataFrame:
    db = safe_id(database)
    sf = schema_filter(schema)
    sql = f"""
        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE, ROW_COUNT, BYTES, LAST_ALTERED, COMMENT
        FROM "{db}".INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA')
          AND TABLE_TYPE IN ('BASE TABLE', 'VIEW') {sf}
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    try:
        return normalize_columns(conn.query(sql, ttl=0))
    except Exception:
        return pd.DataFrame()


def get_schema_doc_coverage(conn, database: str, schema: str | None = None) -> pd.DataFrame:
    db = safe_id(database)
    sf = schema_filter(schema)
    sql = f"""
        SELECT
            TABLE_SCHEMA, TABLE_NAME,
            COUNT(*) AS TOTAL_COLUMNS,
            COUNT(CASE WHEN COMMENT IS NOT NULL AND COMMENT != '' THEN 1 END) AS DOCUMENTED_COLUMNS
        FROM "{db}".INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA') {sf}
        GROUP BY TABLE_SCHEMA, TABLE_NAME
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    try:
        df = normalize_columns(conn.query(sql, ttl=0))
        df["DOC_PCT"] = (
            df["DOCUMENTED_COLUMNS"] / df["TOTAL_COLUMNS"].clip(lower=1) * 100
        ).round(1)
        return df
    except Exception:
        return pd.DataFrame()
