"""Value-based PII classification via SYSTEM$CLASSIFY.

Complements the name-based regex scanner in services/pii.py by sampling actual
column values and returning Snowflake's semantic / privacy categories.
This is on-demand (per table) because SYSTEM$CLASSIFY consumes warehouse
compute.
"""
import json

import pandas as pd

from ._common import normalize_columns, safe_id

_EMPTY = pd.DataFrame(
    columns=["COLUMN_NAME", "SEMANTIC_CATEGORY", "PRIVACY_CATEGORY",
             "EXTRA_INFO", "VALID_VALUE_RATIO"]
)


def classify_table(conn, database: str, schema: str, table: str) -> pd.DataFrame:
    """Run SYSTEM$CLASSIFY on a single table and return one row per column."""
    db = safe_id(database)
    sc = safe_id(schema)
    tb = safe_id(table)
    sql = f"SELECT SYSTEM$CLASSIFY('\"{db}\".\"{sc}\".\"{tb}\"', {{}}) AS RESULT"
    try:
        raw = conn.query(sql, ttl=0)
    except Exception:
        return _EMPTY.copy()
    if raw is None or raw.empty:
        return _EMPTY.copy()
    payload = raw.iloc[0, 0]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return _EMPTY.copy()
    rows = []
    for col_name, info in (payload.get("classification_result", {}) or {}).items():
        rec = info.get("recommendation") or {}
        rows.append({
            "COLUMN_NAME":       col_name.upper(),
            "SEMANTIC_CATEGORY": rec.get("semantic_category"),
            "PRIVACY_CATEGORY":  rec.get("privacy_category"),
            "EXTRA_INFO":        json.dumps(rec.get("extra_info", {})),
            "VALID_VALUE_RATIO": info.get("valid_value_ratio"),
        })
    df = pd.DataFrame(rows)
    return df if not df.empty else _EMPTY.copy()


def latest_classification(conn, database: str, schema: str | None = None) -> pd.DataFrame:
    """Return per-column classification by flattening the RESULT VARIANT
    column on `SNOWFLAKE.ACCOUNT_USAGE.DATA_CLASSIFICATION_LATEST`.
    """
    db_lit = safe_id(database).upper()
    schema_clause = (
        f"AND t.SCHEMA_NAME = '{safe_id(schema).upper()}'" if schema else ""
    )
    sql = f"""
        SELECT
            t.DATABASE_NAME, t.SCHEMA_NAME, t.TABLE_NAME,
            f.key            AS COLUMN_NAME,
            f.value:recommendation:semantic_category::string AS SEMANTIC_CATEGORY,
            f.value:recommendation:privacy_category::string  AS PRIVACY_CATEGORY,
            t.LAST_CLASSIFIED_ON
        FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_CLASSIFICATION_LATEST t,
             LATERAL FLATTEN(input => t.RESULT:classification_result) f
        WHERE t.DATABASE_NAME = '{db_lit}'
          AND t.STATUS = 'COMPLETED'
          {schema_clause}
        ORDER BY t.SCHEMA_NAME, t.TABLE_NAME, COLUMN_NAME
    """
    try:
        return normalize_columns(conn.query(sql, ttl=600))
    except Exception:
        return pd.DataFrame()
