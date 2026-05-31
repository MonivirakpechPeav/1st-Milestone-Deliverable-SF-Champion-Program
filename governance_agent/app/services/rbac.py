"""RBAC / ACCOUNT_USAGE summary."""
import pandas as pd

from app.config import PRIVILEGED_ROLES
from ._common import normalize_columns


def get_rbac_summary(conn) -> dict:
    result = {
        "privileged_users": pd.DataFrame(),
        "public_grants":    pd.DataFrame(),
        "total_users": 0,
        "total_roles": 0,
        "error": None,
    }
    try:
        result["privileged_users"] = normalize_columns(conn.query(f"""
            SELECT GRANTEE_NAME AS USER_NAME, ROLE AS ROLE_NAME
            FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_USERS
            WHERE ROLE IN {PRIVILEGED_ROLES} AND DELETED_ON IS NULL
            ORDER BY ROLE_NAME, USER_NAME
        """, ttl=300))
        result["public_grants"] = normalize_columns(conn.query("""
            SELECT PRIVILEGE, NAME AS OBJECT_NAME, GRANTED_ON
            FROM SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_ROLES
            WHERE GRANTEE_NAME = 'PUBLIC' AND DELETED_ON IS NULL
            ORDER BY GRANTED_ON DESC LIMIT 100
        """, ttl=300))
        counts = normalize_columns(conn.query("""
            SELECT
                (SELECT COUNT(*) FROM SNOWFLAKE.ACCOUNT_USAGE.USERS WHERE DELETED_ON IS NULL) AS TOTAL_USERS,
                (SELECT COUNT(*) FROM SNOWFLAKE.ACCOUNT_USAGE.ROLES WHERE DELETED_ON IS NULL) AS TOTAL_ROLES
        """, ttl=300))
        result["total_users"] = int(counts["TOTAL_USERS"].iloc[0])
        result["total_roles"] = int(counts["TOTAL_ROLES"].iloc[0])
    except Exception as e:
        result["error"] = str(e)
    return result
