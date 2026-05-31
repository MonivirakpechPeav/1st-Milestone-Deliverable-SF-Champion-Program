"""PII column detection."""
import re
import pandas as pd

from app.config import PII_CATEGORIES
from ._common import normalize_columns, safe_id, schema_filter


_EMPTY = pd.DataFrame(
    columns=["TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "DATA_TYPE", "PII_CATEGORY"]
)


def detect_pii_columns(conn, database: str, schema: str | None = None) -> pd.DataFrame:
    db = safe_id(database)
    sf = schema_filter(schema)
    sql = f"""
        SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM "{db}".INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA NOT IN ('INFORMATION_SCHEMA') {sf}
        ORDER BY TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
    """
    try:
        df = normalize_columns(conn.query(sql, ttl=0))
        if df.empty:
            return _EMPTY.copy()
        rows = []
        for _, row in df.iterrows():
            col_lower = row["COLUMN_NAME"].lower()
            for cat, pattern in PII_CATEGORIES.items():
                if re.search(pattern, col_lower):
                    rows.append({**row.to_dict(), "PII_CATEGORY": cat})
                    break
        return pd.DataFrame(rows) if rows else _EMPTY.copy()
    except Exception:
        return _EMPTY.copy()
