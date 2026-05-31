"""Tag inventory and tag-based references (Horizon Catalog tagging)."""
import pandas as pd

from ._common import normalize_columns, safe_id


def list_tags(conn, database: str | None = None) -> pd.DataFrame:
    """Return all tags defined in the account (or scoped to a database)."""
    if database:
        where = (
            f"WHERE TAG_DATABASE = '{safe_id(database)}' "
            f"AND DELETED IS NULL"
        )
    else:
        where = "WHERE DELETED IS NULL"
    sql = f"""
        SELECT TAG_DATABASE, TAG_SCHEMA, TAG_NAME, TAG_OWNER, TAG_COMMENT,
               ALLOWED_VALUES, CREATED, LAST_ALTERED
        FROM SNOWFLAKE.ACCOUNT_USAGE.TAGS
        {where}
        ORDER BY TAG_DATABASE, TAG_SCHEMA, TAG_NAME
        LIMIT 500
    """
    try:
        return normalize_columns(conn.query(sql, ttl=600))
    except Exception:
        return pd.DataFrame()


def tag_references(conn, database: str | None = None) -> pd.DataFrame:
    """Return objects/columns that have tags applied."""
    f = f"AND OBJECT_DATABASE = '{safe_id(database)}'" if database else ""
    sql = f"""
        SELECT
            OBJECT_DATABASE, OBJECT_SCHEMA, OBJECT_NAME, COLUMN_NAME,
            TAG_DATABASE, TAG_SCHEMA, TAG_NAME, TAG_VALUE, DOMAIN
        FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
        WHERE OBJECT_DELETED IS NULL {f}
        ORDER BY OBJECT_DATABASE, OBJECT_SCHEMA, OBJECT_NAME
        LIMIT 1000
    """
    try:
        return normalize_columns(conn.query(sql, ttl=600))
    except Exception:
        return pd.DataFrame()


def generate_tag_sql(
    tag_db: str,
    tag_schema: str,
    tag_name: str,
    allowed_values: list[str] | None = None,
) -> str:
    """Emit DDL to create a tag with optional allowed values."""
    av = ""
    if allowed_values:
        quoted = ", ".join(f"'{v}'" for v in allowed_values)
        av = f"\n  ALLOWED_VALUES {quoted}"
    return (
        f"CREATE TAG IF NOT EXISTS {safe_id(tag_db)}.{safe_id(tag_schema)}."
        f"{safe_id(tag_name)}{av};"
    )


def generate_tag_assignment_sql(
    object_type: str,
    fully_qualified_name: str,
    tag_fqn: str,
    tag_value: str,
) -> str:
    return (
        f"ALTER {object_type.upper()} {fully_qualified_name}\n"
        f"  SET TAG {tag_fqn} = '{tag_value}';"
    )
