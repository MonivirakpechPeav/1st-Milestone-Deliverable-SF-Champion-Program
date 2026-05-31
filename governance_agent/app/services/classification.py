"""Sensitive Data Classification — Snowflake-native (Horizon) wrappers.

This builds on services/classify.py (which calls SYSTEM$CLASSIFY directly)
by adding Classification Profile management and database-wide automatic
classification — the Horizon-aligned alternative to the regex scanner in
services/pii.py.
"""
import pandas as pd

from ._common import exec_sql, normalize_columns, safe_id

# Re-export single-table + latest helpers for convenience.
from .classify import classify_table, latest_classification  # noqa: F401


def create_classification_profile(
    conn,
    profile_db: str,
    profile_schema: str,
    profile_name: str,
    auto_tag: bool = True,
    minimum_object_age_for_classification_days: int = 0,
) -> tuple[bool, str | None]:
    """Create or replace a Classification Profile (Horizon GA feature)."""
    pdb = safe_id(profile_db); psc = safe_id(profile_schema); pnm = safe_id(profile_name)
    body = f"""
    {{
        'minimum_object_age_for_classification_days': {int(minimum_object_age_for_classification_days)},
        'auto_tag': {str(bool(auto_tag)).upper()}
    }}
    """
    sql = (
        f"CREATE OR REPLACE SNOWFLAKE.DATA_PRIVACY.CLASSIFICATION_PROFILE "
        f"\"{pdb}\".\"{psc}\".\"{pnm}\"({body});"
    )
    return exec_sql(conn, sql)


def attach_profile_to_database(
    conn, profile_fqn: str, target_db: str
) -> tuple[bool, str | None]:
    """Attach a classification profile to a database to enable auto-classify."""
    sql = (
        f"ALTER DATABASE {safe_id(target_db)} "
        f"SET CLASSIFICATION_PROFILE = '{profile_fqn}';"
    )
    return exec_sql(conn, sql)


def latest_classification_summary(
    conn, database: str, schema: str | None = None
) -> pd.DataFrame:
    """Aggregate latest classification by privacy/semantic category.

    Source: `SNOWFLAKE.ACCOUNT_USAGE.DATA_CLASSIFICATION_LATEST`.
    The view stores one row per *table* with a VARIANT `RESULT` payload;
    we flatten it into one row per column before aggregating.
    """
    db_lit = safe_id(database).upper()
    sf = f"AND t.SCHEMA_NAME = '{safe_id(schema).upper()}'" if schema else ""
    sql = f"""
        SELECT
            COALESCE(f.value:recommendation:privacy_category::string,  'UNCLASSIFIED') AS PRIVACY_CATEGORY,
            COALESCE(f.value:recommendation:semantic_category::string, 'UNCLASSIFIED') AS SEMANTIC_CATEGORY,
            COUNT(*) AS COLUMN_COUNT
        FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_CLASSIFICATION_LATEST t,
             LATERAL FLATTEN(input => t.RESULT:classification_result) f
        WHERE t.DATABASE_NAME = '{db_lit}'
          AND t.STATUS = 'COMPLETED'
          {sf}
        GROUP BY 1, 2
        ORDER BY COLUMN_COUNT DESC
    """
    try:
        return normalize_columns(conn.query(sql, ttl=600))
    except Exception:
        return pd.DataFrame()
