"""Auto-generated remediation SQL for governance findings."""
import pandas as pd


_MASK_EXPR = {
    "Email":         "REGEXP_REPLACE(val, '[^@]+@', '****@')",
    "Phone":         "REGEXP_REPLACE(val, '[0-9]', '*')",
    "SSN / SIN":     "'***-**-****'",
    "Date of Birth": "TO_CHAR(DATE_TRUNC('year', TRY_TO_DATE(val)), 'YYYY-01-01')",
    "Address":       "'**** MASKED ****'",
    "Payment Card":  "CONCAT('****-****-****-', RIGHT(val, 4))",
    "Government ID": "'***MASKED***'",
    "IP Address":    "REGEXP_REPLACE(val, r'\\d+$', '***')",
    "Financial":     "'*****'",
    "Bank Account":  "CONCAT('****', RIGHT(val, 4))",
    "Tax ID":        "'***-**-****'",
    "Health":        "'REDACTED'",
}

_PRIORITY = {
    "Email":         "HIGH",
    "SSN / SIN":     "HIGH",
    "Payment Card":  "HIGH",
    "Government ID": "HIGH",
    "Health":        "HIGH",
    "Tax ID":        "HIGH",
    "Bank Account":  "HIGH",
    "Phone":         "MEDIUM",
    "Date of Birth": "MEDIUM",
    "Financial":     "MEDIUM",
    "Address":       "LOW",
    "IP Address":    "LOW",
}


def _masking_sql(row: dict, database: str) -> dict:
    schema, table, col, cat = (
        row["TABLE_SCHEMA"], row["TABLE_NAME"], row["COLUMN_NAME"], row["PII_CATEGORY"],
    )
    dtype  = row.get("DATA_TYPE", "VARCHAR").upper()
    ret    = "NUMBER" if any(t in dtype for t in ("INT", "FLOAT", "NUMBER", "DECIMAL")) else "STRING"
    expr   = _MASK_EXPR.get(cat, "'****MASKED****'")
    policy = f"MASK_{table}_{col}".upper()

    return {
        "priority":     _PRIORITY.get(cat, "MEDIUM"),
        "type":         "Unmasked PII Column",
        "target":       f"{schema}.{table}.{col}",
        "pii_category": cat,
        "sql": f"""-- Step 1: Create masking policy for {cat} column
CREATE MASKING POLICY IF NOT EXISTS "{database}"."{schema}"."{policy}"
  AS (val {ret}) RETURNS {ret} ->
    CASE
      WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'SYSADMIN') THEN val
      ELSE {expr}
    END;

-- Step 2: Apply policy to column
ALTER TABLE "{database}"."{schema}"."{table}"
  MODIFY COLUMN "{col}"
  SET MASKING POLICY "{database}"."{schema}"."{policy}";""",
    }


def _doc_sql(row: dict, database: str) -> dict:
    schema, table = row["TABLE_SCHEMA"], row["TABLE_NAME"]
    undoc = int(row["TOTAL_COLUMNS"]) - int(row["DOCUMENTED_COLUMNS"])
    return {
        "priority":     "MEDIUM",
        "type":         "Undocumented Table",
        "target":       f"{schema}.{table}",
        "pii_category": None,
        "sql": f"""-- Add table description
COMMENT ON TABLE "{database}"."{schema}"."{table}"
  IS 'TODO: Describe the purpose and business context of this table.';

-- Template: document each undocumented column (repeat per column)
-- COMMENT ON COLUMN "{database}"."{schema}"."{table}".<COLUMN_NAME>
--   IS 'TODO: column description.';
-- {undoc} column(s) still need documentation.""",
    }


def _rbac_sql(user: str, role: str) -> dict:
    scoped = f"{role}_LIMITED"
    return {
        "priority":     "HIGH" if role == "ACCOUNTADMIN" else "MEDIUM",
        "type":         "Overprivileged User",
        "target":       f"{user} → {role}",
        "pii_category": None,
        "sql": f"""-- Review: does {user} still need {role}?

-- Option A: Revoke if no longer required
REVOKE ROLE {role} FROM USER {user};

-- Option B: Replace with a scoped role (recommended)
CREATE ROLE IF NOT EXISTS {scoped};
-- GRANT <specific privileges> TO ROLE {scoped};
GRANT ROLE {scoped} TO USER {user};
REVOKE ROLE {role} FROM USER {user};""",
    }


def generate_all_remediations(
    pii_df: pd.DataFrame,
    policy_df: pd.DataFrame,
    doc_df: pd.DataFrame,
    rbac: dict,
    database: str,
) -> list:
    items: list = []

    if not pii_df.empty:
        masked = set()
        if not policy_df.empty and "COLUMN_NAME" in policy_df.columns:
            masked = set(policy_df["COLUMN_NAME"].dropna().str.upper())
        for _, row in pii_df.iterrows():
            if row["COLUMN_NAME"].upper() not in masked:
                items.append(_masking_sql(row.to_dict(), database))

    if not doc_df.empty:
        for _, row in doc_df[doc_df["DOC_PCT"] < 50].iterrows():
            items.append(_doc_sql(row.to_dict(), database))

    if not rbac.get("error"):
        priv_df = rbac.get("privileged_users", pd.DataFrame())
        if not priv_df.empty:
            admins = priv_df[priv_df["ROLE_NAME"] == "ACCOUNTADMIN"]
            if len(admins) > 3:
                for _, row in admins.iterrows():
                    items.append(_rbac_sql(row["USER_NAME"], row["ROLE_NAME"]))

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(items, key=lambda x: order.get(x["priority"], 3))
