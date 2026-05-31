"""Lineage tracing using SNOWFLAKE.CORE.GET_LINEAGE."""
import pandas as pd

from ._common import normalize_columns


def get_lineage(
    conn,
    object_name: str,
    object_domain: str = "TABLE",
    direction: str = "DOWNSTREAM",
    distance: int = 2,
) -> pd.DataFrame:
    """Return lineage rows for the given object.

    object_name: fully-qualified, e.g. 'DB.SCHEMA.TABLE'
    direction: 'UPSTREAM' | 'DOWNSTREAM'
    object_domain: TABLE | VIEW | MATERIALIZED_VIEW | DYNAMIC_TABLE |
                   COLUMN | PROCEDURE | TASK | DATASET
    """
    direction = direction.upper()
    if direction not in {"UPSTREAM", "DOWNSTREAM"}:
        direction = "DOWNSTREAM"
    distance = max(1, min(int(distance), 5))

    safe_name   = object_name.replace("'", "''")
    safe_domain = object_domain.replace("'", "''")

    sql = f"""
        SELECT *
        FROM TABLE(
            SNOWFLAKE.CORE.GET_LINEAGE(
                '{safe_name}', '{safe_domain}', '{direction}', {distance}
            )
        )
    """
    try:
        return normalize_columns(conn.query(sql, ttl=60))
    except Exception:
        return pd.DataFrame()


def get_column_lineage(
    conn,
    db: str,
    schema: str,
    table: str,
    column: str,
    direction: str = "UPSTREAM",
    distance: int = 3,
) -> pd.DataFrame:
    """Convenience wrapper for column-level lineage."""
    fqn = f"{db}.{schema}.{table}.{column}"
    return get_lineage(conn, fqn, "COLUMN", direction, distance)

