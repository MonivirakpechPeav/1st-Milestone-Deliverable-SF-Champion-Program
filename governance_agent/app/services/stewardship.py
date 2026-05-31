"""Object stewardship via Snowflake Object Contacts."""
import pandas as pd

from ._common import normalize_columns, safe_id


def get_object_contacts(conn, database: str | None = None) -> dict:
    """Return contact assignments and inventory of contacts in the account."""
    result: dict = {
        "contacts":   pd.DataFrame(),
        "references": pd.DataFrame(),
        "error":      None,
    }
    try:
        db_filter = f"AND OBJECT_DATABASE = '{safe_id(database)}'" if database else ""

        result["references"] = normalize_columns(conn.query(f"""
            SELECT
                OBJECT_DATABASE, OBJECT_SCHEMA, OBJECT_NAME, OBJECT_DOMAIN,
                CONTACT_NAME, CONTACT_PURPOSE
            FROM SNOWFLAKE.ACCOUNT_USAGE.CONTACT_REFERENCES
            WHERE OBJECT_DELETED IS NULL {db_filter}
            ORDER BY OBJECT_DATABASE, OBJECT_SCHEMA, OBJECT_NAME
            LIMIT 500
        """, ttl=300))

        try:
            result["contacts"] = normalize_columns(conn.query("""
                SELECT CONTACT_DATABASE, CONTACT_SCHEMA, CONTACT_NAME
                FROM SNOWFLAKE.ACCOUNT_USAGE.CONTACTS
                WHERE DELETED IS NULL
                ORDER BY CONTACT_DATABASE, CONTACT_SCHEMA, CONTACT_NAME
                LIMIT 200
            """, ttl=300))
        except Exception:
            # Contacts inventory view may have a different schema; ignore.
            result["contacts"] = pd.DataFrame()
    except Exception as e:
        result["error"] = str(e)
    return result


def generate_contact_sql(
    contact_name: str,
    purpose: str,
    object_type: str,
    fully_qualified_name: str,
    email: str | None = None,
) -> str:
    """Return a copy-pasteable SQL block to create + assign a contact."""
    purpose = purpose.upper().strip()
    valid = {"ACCESS_APPROVAL", "SECURITY_COMPLIANCE", "STEWARD", "SUPPORT"}
    if purpose not in valid:
        purpose = "STEWARD"

    contact_def = (
        f"CREATE CONTACT IF NOT EXISTS {contact_name}"
        + (f"\n  EMAIL_DISTRIBUTION_LIST = '{email}'" if email else "")
        + ";"
    )
    return (
        f"-- 1. Create the contact (run in the schema where you want it stored)\n"
        f"{contact_def}\n\n"
        f"-- 2. Assign the contact to the object\n"
        f"ALTER {object_type.upper()} {fully_qualified_name}\n"
        f"  SET CONTACT {purpose} = {contact_name};"
    )
