"""Unit tests for app/services/scoring.py (Feature 6 — Governance Scoring)."""
import pandas as pd

from app import scoring


class TestGrade:
    def test_bands(self):
        assert scoring._grade(95) == ("A", "#2ecc71")
        assert scoring._grade(90) == ("A", "#2ecc71")
        assert scoring._grade(80)[0] == "B"
        assert scoring._grade(60)[0] == "C"
        assert scoring._grade(40)[0] == "D"
        assert scoring._grade(0)[0] == "F"
        assert scoring._grade(-5)[0] == "F"


class TestScorePii:
    def test_no_pii_is_perfect(self):
        out = scoring._score_pii(pd.DataFrame(), pd.DataFrame())
        assert out["score"] == 25.0
        assert "No PII" in out["note"]

    def test_partial_masking_ratio(self, pii_df, policy_df):
        # 1 of 3 PII columns (USER_EMAIL) is masked -> 25 * 1/3 = 8.3
        out = scoring._score_pii(pii_df, policy_df)
        assert out["score"] == 8.3
        assert out["note"] == "1/3 PII columns masked"

    def test_no_policies_means_zero(self, pii_df):
        out = scoring._score_pii(pii_df, pd.DataFrame())
        assert out["score"] == 0.0


class TestScoreDocs:
    def test_empty_is_zero(self):
        out = scoring._score_docs(pd.DataFrame())
        assert out["score"] == 0.0
        assert out["note"] == "No tables found"

    def test_ratio(self, doc_df):
        # documented 9 / total 14 -> 25 * 9/14 = 16.1
        out = scoring._score_docs(doc_df)
        assert out["score"] == 16.1
        assert out["note"] == "9/14 columns documented"


class TestScoreRbac:
    def test_error_returns_neutral(self):
        out = scoring._score_rbac({"error": "no access"})
        assert out["score"] == 12.5

    def test_healthy(self):
        out = scoring._score_rbac({"error": None})
        assert out["score"] == 25.0
        assert out["note"] == "RBAC looks healthy"

    def test_too_many_admins_deducts(self):
        priv = pd.DataFrame({"ROLE_NAME": ["ACCOUNTADMIN"] * 6})
        out = scoring._score_rbac({"error": None, "privileged_users": priv})
        # (6-3)*3 = 9 deduction
        assert out["score"] == 16.0
        assert "6 ACCOUNTADMIN users" in out["note"]

    def test_public_grants_deduct(self):
        pub = pd.DataFrame({"PRIVILEGE": ["USAGE"] * 6})
        out = scoring._score_rbac({"error": None, "public_grants": pub})
        assert out["score"] == 20.0
        assert "6 PUBLIC role grants" in out["note"]


class TestScorePolicy:
    def test_no_tables_zero(self):
        assert scoring._score_policy(pd.DataFrame(), 0)["score"] == 0.0

    def test_coverage_ratio(self, policy_df):
        out = scoring._score_policy(policy_df, total_tables=2)
        # 1 distinct covered table / 2 -> 12.5
        assert out["score"] == 12.5
        assert out["note"] == "1/2 tables have policies"


class TestComputeGovernanceScore:
    def test_full_bundle(self, pii_df, policy_df, doc_df, rbac_ok):
        out = scoring.compute_governance_score(
            pii_df, policy_df, doc_df, rbac_ok, total_tables=2
        )
        assert set(out["components"]) == {"pii", "docs", "rbac", "policy"}
        assert 0 <= out["total"] <= 100
        assert out["grade"] in {"A", "B", "C", "D", "F"}

    def test_normalisation_to_100(self):
        # Force three pillars to max (25) and policy to 0.
        empty = pd.DataFrame()
        out = scoring.compute_governance_score(
            pii_df=empty,                 # no PII -> 25
            policy_df=empty,
            doc_df=pd.DataFrame(
                {"TOTAL_COLUMNS": [4], "DOCUMENTED_COLUMNS": [4]}
            ),                            # 25
            rbac={"error": None},         # 25
            total_tables=0,               # policy 0 (no tables)
        )
        # pii 25 + docs 25 + rbac 25 + policy 0 = 75.0
        assert out["total"] == 75.0
