"""Database / schema discovery."""
from ._common import normalize_columns, safe_id


def list_databases(conn) -> tuple[list, str | None]:
    try:
        df = conn.session().sql("SHOW DATABASES").to_pandas()
        df = normalize_columns(df)
        if "NAME" not in df.columns:
            return [], f"Unexpected columns from SHOW DATABASES: {list(df.columns)}"
        names = [n for n in df["NAME"].tolist() if n]
        return sorted(names), None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def list_schemas(conn, database: str) -> list:
    db = safe_id(database)
    try:
        df = conn.session().sql(f'SHOW SCHEMAS IN DATABASE "{db}"').to_pandas()
        df = normalize_columns(df)
        if "NAME" not in df.columns:
            return []
        return sorted([s for s in df["NAME"].tolist() if s and s != "INFORMATION_SCHEMA"])
    except Exception:
        return []


def list_tables(conn, database: str, schema: str) -> list:
    db = safe_id(database)
    sc = safe_id(schema)
    try:
        df = conn.session().sql(f'SHOW TABLES IN SCHEMA "{db}"."{sc}"').to_pandas()
        df = normalize_columns(df)
        if "NAME" not in df.columns:
            return []
        return sorted([t for t in df["NAME"].tolist() if t])
    except Exception:
        return []
