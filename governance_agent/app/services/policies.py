"""Masking / row-access / projection policy coverage."""
import pandas as pd

from ._common import normalize_columns, safe_id, schema_filter


_EMPTY = pd.DataFrame(
    columns=["TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "POLICY_NAME", "POLICY_KIND"]
)


def get_policy_coverage(conn, database: str, schema: str | None = None) -> pd.DataFrame:
    db = safe_id(database)
    sf = schema_filter(schema, col="REF_SCHEMA_NAME")
    sql = f"""
        SELECT
            REF_SCHEMA_NAME AS TABLE_SCHEMA,
            REF_ENTITY_NAME AS TABLE_NAME,
            REF_COLUMN_NAME AS COLUMN_NAME,
            POLICY_NAME, POLICY_KIND
        FROM "{db}".INFORMATION_SCHEMA.POLICY_REFERENCES
        WHERE POLICY_KIND IN (
            'MASKING_POLICY', 'ROW_ACCESS_POLICY', 'PROJECTION_POLICY',
            'AGGREGATION_POLICY', 'JOIN_POLICY'
        ) {sf}
        ORDER BY TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
    """
    try:
        df = normalize_columns(conn.query(sql, ttl=0))
        return df if not df.empty else _EMPTY.copy()
    except Exception:
        return _EMPTY.copy()
