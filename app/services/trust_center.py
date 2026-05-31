"""Snowflake Trust Center findings reader.

Reads scanner findings from SNOWFLAKE.TRUST_CENTER.FINDINGS so the UI
can show security posture / at-risk entities in a single place.
"""
import pandas as pd

from ._common import normalize_columns


def get_findings(conn, limit: int = 500) -> pd.DataFrame:
    """Return the most recent Trust Center findings."""
    sql = f"""
        SELECT
            SCANNER_NAME, SCANNER_SHORT_DESCRIPTION,
            SEVERITY, SCANNER_TYPE,
            TOTAL_AT_RISK_COUNT, AT_RISK_ENTITIES,
            SUGGESTED_ACTION, IMPACT, STATE,
            CREATED_ON
        FROM SNOWFLAKE.TRUST_CENTER.FINDINGS
        ORDER BY CREATED_ON DESC
        LIMIT {int(limit)}
    """
    try:
        return normalize_columns(conn.query(sql, ttl=600))
    except Exception:
        return pd.DataFrame()


def severity_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "SEVERITY" not in df.columns:
        return pd.DataFrame(columns=["SEVERITY", "COUNT"])
    out = df["SEVERITY"].fillna("UNKNOWN").value_counts().reset_index()
    out.columns = ["SEVERITY", "COUNT"]
    return out


def list_scanners(conn) -> pd.DataFrame:
    """Return Trust Center scanner inventory + state."""
    sql = """
        SELECT NAME, ID, TYPE, SCHEDULE, STATE, LAST_SCAN_TIMESTAMP
        FROM SNOWFLAKE.TRUST_CENTER.SCANNERS
        ORDER BY NAME
    """
    try:
        return normalize_columns(conn.query(sql, ttl=600))
    except Exception:
        return pd.DataFrame()
