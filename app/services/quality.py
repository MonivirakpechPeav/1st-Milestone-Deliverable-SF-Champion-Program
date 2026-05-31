"""Data quality monitoring via Data Metric Functions (DMFs)."""
import pandas as pd

from ._common import normalize_columns, safe_id


def get_dmf_coverage(conn, database: str, schema: str | None = None) -> dict:
    """Return DMFs attached to tables in scope and a coverage summary."""
    result: dict = {
        "dmfs":            pd.DataFrame(),
        "tables_with_dmf": 0,
        "error":           None,
    }
    try:
        db = safe_id(database)
        sf = (
            f"AND REF_SCHEMA_NAME = '{safe_id(schema)}'"
            if schema else ""
        )
        df = normalize_columns(conn.query(f"""
            SELECT
                REF_DATABASE_NAME  AS DATABASE_NAME,
                REF_SCHEMA_NAME    AS SCHEMA_NAME,
                REF_ENTITY_NAME    AS TABLE_NAME,
                METRIC_NAME,
                METRIC_SCHEMA_NAME,
                SCHEDULE
            FROM SNOWFLAKE.ACCOUNT_USAGE.DATA_METRIC_FUNCTION_REFERENCES
            WHERE REF_DATABASE_NAME = '{db}' {sf}
            ORDER BY REF_SCHEMA_NAME, REF_ENTITY_NAME, METRIC_NAME
        """, ttl=300))
        result["dmfs"] = df
        if not df.empty:
            result["tables_with_dmf"] = df[
                ["DATABASE_NAME", "SCHEMA_NAME", "TABLE_NAME"]
            ].drop_duplicates().shape[0]
    except Exception as e:
        result["error"] = str(e)
    return result


# Built-in system DMFs commonly used.
BUILTIN_DMFS = {
    "Null count":      "SNOWFLAKE.CORE.NULL_COUNT",
    "Null percent":    "SNOWFLAKE.CORE.NULL_PERCENT",
    "Duplicate count": "SNOWFLAKE.CORE.DUPLICATE_COUNT",
    "Unique count":    "SNOWFLAKE.CORE.UNIQUE_COUNT",
    "Row count":       "SNOWFLAKE.CORE.ROW_COUNT",
    "Freshness":       "SNOWFLAKE.CORE.FRESHNESS",
}


def generate_dmf_attach_sql(
    fully_qualified_table: str,
    metric_fqn: str,
    column: str | None = None,
    schedule: str = "USING CRON 0 * * * * UTC",
) -> str:
    """Return SQL that schedules + attaches a DMF to a table/column."""
    arg = f"({column})" if column else "()"
    return (
        f"-- 1. Set the metric schedule on the table (one-time per table)\n"
        f"ALTER TABLE {fully_qualified_table}\n"
        f"  SET DATA_METRIC_SCHEDULE = '{schedule}';\n\n"
        f"-- 2. Attach the metric\n"
        f"ALTER TABLE {fully_qualified_table}\n"
        f"  ADD DATA METRIC FUNCTION {metric_fqn}\n"
        f"  ON {arg};"
    )
