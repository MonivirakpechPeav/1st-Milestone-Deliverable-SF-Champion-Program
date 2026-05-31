"""Cortex-powered object descriptions.

Generate column / table comments using Cortex AI_COMPLETE so undocumented
objects can be back-filled. The user reviews before applying.
"""
import pandas as pd

from ._common import normalize_columns, safe_id


_PROMPT = (
    "You are a data steward. Write a concise (<= 200 chars) plain-English "
    "description of the following Snowflake column based on its name, type, "
    "and parent table. No markdown, one sentence."
)


def suggest_column_descriptions(
    conn, database: str, schema: str, table: str
) -> pd.DataFrame:
    """Return a DataFrame of column-name + suggested-description rows."""
    db = safe_id(database); sc = safe_id(schema); tb = safe_id(table)
    cols_sql = f"""
        SELECT COLUMN_NAME, DATA_TYPE, COMMENT
        FROM "{db}".INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{sc}' AND TABLE_NAME = '{tb}'
        ORDER BY ORDINAL_POSITION
    """
    try:
        cols = normalize_columns(conn.query(cols_sql, ttl=0))
    except Exception:
        return pd.DataFrame(columns=["COLUMN_NAME", "DATA_TYPE", "SUGGESTED_DESCRIPTION"])

    if cols.empty:
        return cols

    suggestions: list[str] = []
    for _, row in cols.iterrows():
        prompt = (
            f"{_PROMPT}\n\nTable: {db}.{sc}.{tb}\n"
            f"Column: {row['COLUMN_NAME']} ({row['DATA_TYPE']})"
        ).replace("'", "''")
        sql = f"SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet', '{prompt}') AS R"
        try:
            res = conn.query(sql, ttl=0)
            text = str(res.iloc[0, 0]) if not res.empty else ""
        except Exception:
            text = ""
        suggestions.append(text.strip().splitlines()[0] if text else "")

    cols["SUGGESTED_DESCRIPTION"] = suggestions
    return cols[["COLUMN_NAME", "DATA_TYPE", "COMMENT", "SUGGESTED_DESCRIPTION"]]


def generate_comment_sql(
    database: str, schema: str, table: str,
    column_descriptions: dict[str, str],
    table_description: str | None = None,
) -> str:
    """Emit COMMENT ON statements ready to apply."""
    db = safe_id(database); sc = safe_id(schema); tb = safe_id(table)
    parts: list[str] = []
    if table_description:
        td = table_description.replace("'", "''")
        parts.append(f"COMMENT ON TABLE \"{db}\".\"{sc}\".\"{tb}\" IS '{td}';")
    for col, desc in column_descriptions.items():
        if not desc:
            continue
        d = desc.replace("'", "''")
        parts.append(
            f"COMMENT ON COLUMN \"{db}\".\"{sc}\".\"{tb}\".\"{safe_id(col)}\" IS '{d}';"
        )
    return "\n".join(parts)
