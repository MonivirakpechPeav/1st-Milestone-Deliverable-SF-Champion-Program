"""Governance scoring."""
import pandas as pd

from app.config import GRADE_BANDS


def _grade(total: float) -> tuple[str, str]:
    for threshold, letter, color in GRADE_BANDS:
        if total >= threshold:
            return letter, color
    return "F", "#e74c3c"


def _score_pii(pii_df: pd.DataFrame, policy_df: pd.DataFrame) -> dict:
    total_pii = len(pii_df)
    if total_pii == 0:
        return {"score": 25.0, "max": 25, "note": "No PII columns detected"}
    masked = set()
    if not policy_df.empty and "COLUMN_NAME" in policy_df.columns:
        masked = set(policy_df["COLUMN_NAME"].dropna().str.upper())
    masked_pii = len(set(pii_df["COLUMN_NAME"].str.upper()) & masked)
    return {
        "score": round(25.0 * masked_pii / total_pii, 1),
        "max": 25,
        "note": f"{masked_pii}/{total_pii} PII columns masked",
    }


def _score_docs(doc_df: pd.DataFrame) -> dict:
    if doc_df.empty:
        return {"score": 0.0, "max": 25, "note": "No tables found"}
    total_cols = doc_df["TOTAL_COLUMNS"].sum()
    doc_cols   = doc_df["DOCUMENTED_COLUMNS"].sum()
    return {
        "score": round(25.0 * doc_cols / max(total_cols, 1), 1),
        "max": 25,
        "note": f"{int(doc_cols)}/{int(total_cols)} columns documented",
    }


def _score_rbac(rbac: dict) -> dict:
    rbac_score = 25.0
    issues: list[str] = []
    if rbac.get("error"):
        return {"score": 12.5, "max": 25, "note": "ACCOUNT_USAGE not accessible"}

    priv_df = rbac.get("privileged_users", pd.DataFrame())
    if not priv_df.empty:
        admin_count = int((priv_df["ROLE_NAME"] == "ACCOUNTADMIN").sum())
        if admin_count > 3:
            rbac_score -= min(15, (admin_count - 3) * 3)
            issues.append(f"{admin_count} ACCOUNTADMIN users")
    pub_df = rbac.get("public_grants", pd.DataFrame())
    if not pub_df.empty and len(pub_df) > 5:
        rbac_score -= 5
        issues.append(f"{len(pub_df)} PUBLIC role grants")

    return {
        "score": round(max(0, rbac_score), 1),
        "max": 25,
        "note": "; ".join(issues) if issues else "RBAC looks healthy",
    }


def _score_policy(policy_df: pd.DataFrame, total_tables: int) -> dict:
    if total_tables == 0:
        return {"score": 0.0, "max": 25, "note": "No tables found"}
    covered = (
        len(policy_df[["TABLE_SCHEMA", "TABLE_NAME"]].drop_duplicates())
        if not policy_df.empty else 0
    )
    return {
        "score": round(25.0 * min(covered, total_tables) / total_tables, 1),
        "max": 25,
        "note": f"{covered}/{total_tables} tables have policies",
    }


def compute_governance_score(
    pii_df: pd.DataFrame,
    policy_df: pd.DataFrame,
    doc_df: pd.DataFrame,
    rbac: dict,
    total_tables: int,
) -> dict:
    components = {
        "pii":     _score_pii(pii_df, policy_df),
        "docs":    _score_docs(doc_df),
        "rbac":    _score_rbac(rbac),
        "policy":  _score_policy(policy_df, total_tables),
    }
    total = round(sum(c["score"] for c in components.values()), 1)  # 0–100
    grade, color = _grade(total)
    return {"components": components, "total": total, "grade": grade, "color": color}
