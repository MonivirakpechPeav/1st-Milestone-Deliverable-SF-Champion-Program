"""Access audit via SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY."""
import pandas as pd

from ._common import normalize_columns


def get_access_audit(conn, days: int = 7) -> dict:
    """Summarize recent data access from ACCESS_HISTORY."""
    days = int(days)
    if days <= 0 or days > 365:
        days = 7

    result: dict = {
        "top_readers":   pd.DataFrame(),
        "top_objects":   pd.DataFrame(),
        "off_hours":     pd.DataFrame(),
        "modifications": pd.DataFrame(),
        "total_queries": 0,
        "days":          days,
        "error":         None,
    }

    try:
        result["top_readers"] = normalize_columns(conn.query(f"""
            SELECT USER_NAME, COUNT(*) AS QUERY_COUNT
            FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
            WHERE QUERY_START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
            GROUP BY USER_NAME
            ORDER BY QUERY_COUNT DESC
            LIMIT 20
        """, ttl=300))

        result["top_objects"] = normalize_columns(conn.query(f"""
            SELECT
                obj.value:"objectName"::STRING AS OBJECT_NAME,
                obj.value:"objectDomain"::STRING AS OBJECT_DOMAIN,
                COUNT(*) AS ACCESS_COUNT,
                COUNT(DISTINCT USER_NAME) AS DISTINCT_USERS
            FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY,
                 LATERAL FLATTEN(INPUT => DIRECT_OBJECTS_ACCESSED) obj
            WHERE QUERY_START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
              AND obj.value:"objectName" IS NOT NULL
            GROUP BY 1, 2
            ORDER BY ACCESS_COUNT DESC
            LIMIT 25
        """, ttl=300))

        result["off_hours"] = normalize_columns(conn.query(f"""
            SELECT USER_NAME, QUERY_ID, QUERY_START_TIME
            FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
            WHERE QUERY_START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
              AND (HOUR(QUERY_START_TIME) < 6 OR HOUR(QUERY_START_TIME) >= 22)
            ORDER BY QUERY_START_TIME DESC
            LIMIT 50
        """, ttl=300))

        result["modifications"] = normalize_columns(conn.query(f"""
            SELECT
                obj.value:"objectName"::STRING AS OBJECT_NAME,
                COUNT(*) AS MOD_COUNT,
                COUNT(DISTINCT USER_NAME) AS DISTINCT_USERS
            FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY,
                 LATERAL FLATTEN(INPUT => OBJECTS_MODIFIED) obj
            WHERE QUERY_START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
              AND obj.value:"objectName" IS NOT NULL
            GROUP BY 1
            ORDER BY MOD_COUNT DESC
            LIMIT 25
        """, ttl=300))

        total = normalize_columns(conn.query(f"""
            SELECT COUNT(*) AS C
            FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
            WHERE QUERY_START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        """, ttl=300))
        result["total_queries"] = int(total["C"].iloc[0]) if not total.empty else 0
    except Exception as e:
        result["error"] = str(e)
    return result
