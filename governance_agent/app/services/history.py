"""Persistent scan history (SCAN_HISTORY table)."""
import pandas as pd

from app.config import HISTORY_SCHEMA, HISTORY_TABLE
from ._common import clean_db, exec_sql


def ensure_history_store(conn, database: str) -> tuple[bool, str | None]:
    db = clean_db(database)
    ok, err = exec_sql(conn, f'CREATE SCHEMA IF NOT EXISTS "{db}"."{HISTORY_SCHEMA}"')
    if not ok:
        return False, err
    ok, err = exec_sql(conn, f"""
        CREATE TABLE IF NOT EXISTS "{db}"."{HISTORY_SCHEMA}"."{HISTORY_TABLE}" (
            SCAN_ID                VARCHAR       DEFAULT UUID_STRING(),
            SCAN_TS                TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            DATABASE_NAME          VARCHAR,
            SCHEMA_NAME            VARCHAR,
            OVERALL_SCORE          FLOAT,
            GRADE                  VARCHAR(2),
            PII_SCORE              FLOAT,
            DOC_SCORE              FLOAT,
            RBAC_SCORE             FLOAT,
            POLICY_SCORE           FLOAT,
            STORAGE_SCORE          FLOAT,
            PII_COLUMNS_COUNT      INTEGER,
            TOTAL_TABLES           INTEGER,
            POLICIES_COUNT         INTEGER,
            PRIVILEGED_USERS_COUNT INTEGER
        )
    """)
    if not ok:
        return False, err
    # Forward-compat: add STORAGE_SCORE column on pre-existing tables.
    return exec_sql(conn, f"""
        ALTER TABLE "{db}"."{HISTORY_SCHEMA}"."{HISTORY_TABLE}"
        ADD COLUMN IF NOT EXISTS STORAGE_SCORE FLOAT
    """)


def save_scan(conn, scan_results: dict, history_db: str) -> tuple[bool, str | None]:
    r     = scan_results
    score = r["score"]
    comp  = score["components"]
    inv   = r["inventory_df"]
    rbac  = r["rbac"]

    base_tables = len(inv[inv["TABLE_TYPE"] == "BASE TABLE"]) if not inv.empty else 0
    priv_count  = len(rbac.get("privileged_users", pd.DataFrame())) if not rbac.get("error") else -1
    db_val      = (r["database"] or "").replace("'", "''")
    schema_val  = (r.get("schema") or "ALL").replace("'", "''")
    db          = clean_db(history_db)

    sql = f"""
        INSERT INTO "{db}"."{HISTORY_SCHEMA}"."{HISTORY_TABLE}"
            (DATABASE_NAME, SCHEMA_NAME, OVERALL_SCORE, GRADE,
             PII_SCORE, DOC_SCORE, RBAC_SCORE, POLICY_SCORE, STORAGE_SCORE,
             PII_COLUMNS_COUNT, TOTAL_TABLES, POLICIES_COUNT, PRIVILEGED_USERS_COUNT)
        VALUES (
            '{db_val}', '{schema_val}',
            {score["total"]}, '{score["grade"]}',
            {comp["pii"]["score"]}, {comp["docs"]["score"]},
            {comp["rbac"]["score"]}, {comp["policy"]["score"]},
            {comp.get("storage", {}).get("score", 0)},
            {len(r["pii_df"])}, {base_tables},
            {len(r["policy_df"])}, {priv_count}
        )
    """
    return exec_sql(conn, sql)


def load_history(conn, history_db: str) -> pd.DataFrame:
    db = clean_db(history_db)
    try:
        df = conn.query(f"""
            SELECT SCAN_TS, DATABASE_NAME, SCHEMA_NAME,
                   OVERALL_SCORE, GRADE,
                   PII_SCORE, DOC_SCORE, RBAC_SCORE, POLICY_SCORE, STORAGE_SCORE,
                   PII_COLUMNS_COUNT, TOTAL_TABLES, POLICIES_COUNT
            FROM "{db}"."{HISTORY_SCHEMA}"."{HISTORY_TABLE}"
            ORDER BY SCAN_TS DESC
            LIMIT 500
        """, ttl=0)
        df.columns = df.columns.str.upper()
        return df
    except Exception:
        return pd.DataFrame()
