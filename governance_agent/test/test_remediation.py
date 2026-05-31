"""Unit tests for app/services/remediation.py (Feature 10 — Remediation SQL)."""
import pandas as pd

from app import remediation


class TestMaskingSql:
    def test_email_masking(self):
        row = {
            "TABLE_SCHEMA": "PUBLIC", "TABLE_NAME": "CUST",
            "COLUMN_NAME": "EMAIL", "PII_CATEGORY": "Email", "DATA_TYPE": "VARCHAR",
        }
        item = remediation._masking_sql(row, "DB")
        assert item["priority"] == "HIGH"
        assert item["type"] == "Unmasked PII Column"
        assert item["target"] == "PUBLIC.CUST.EMAIL"
        assert "CREATE MASKING POLICY" in item["sql"]
        assert '"DB"."PUBLIC"."MASK_CUST_EMAIL"' in item["sql"]
        assert "REGEXP_REPLACE" in item["sql"]

    def test_numeric_column_returns_number_type(self):
        row = {
            "TABLE_SCHEMA": "S", "TABLE_NAME": "T",
            "COLUMN_NAME": "ACCT", "PII_CATEGORY": "Bank Account", "DATA_TYPE": "NUMBER",
        }
        item = remediation._masking_sql(row, "DB")
        assert "(val NUMBER) RETURNS NUMBER" in item["sql"]

    def test_unknown_category_default_mask(self):
        row = {
            "TABLE_SCHEMA": "S", "TABLE_NAME": "T",
            "COLUMN_NAME": "X", "PII_CATEGORY": "Mystery", "DATA_TYPE": "VARCHAR",
        }
        item = remediation._masking_sql(row, "DB")
        assert "****MASKED****" in item["sql"]
        assert item["priority"] == "MEDIUM"


class TestDocSql:
    def test_comment_template(self):
        row = {"TABLE_SCHEMA": "S", "TABLE_NAME": "T",
               "TOTAL_COLUMNS": 10, "DOCUMENTED_COLUMNS": 2}
        item = remediation._doc_sql(row, "DB")
        assert item["type"] == "Undocumented Table"
        assert "COMMENT ON TABLE" in item["sql"]
        assert "8 column(s) still need documentation" in item["sql"]


class TestRbacSql:
    def test_accountadmin_high_priority(self):
        item = remediation._rbac_sql("ALICE", "ACCOUNTADMIN")
        assert item["priority"] == "HIGH"
        assert "REVOKE ROLE ACCOUNTADMIN FROM USER ALICE" in item["sql"]
        assert "ACCOUNTADMIN_LIMITED" in item["sql"]

    def test_other_role_medium(self):
        item = remediation._rbac_sql("BOB", "SYSADMIN")
        assert item["priority"] == "MEDIUM"


class TestGenerateAllRemediations:
    def test_unmasked_pii_emitted(self, pii_df, doc_df):
        items = remediation.generate_all_remediations(
            pii_df, pd.DataFrame(), pd.DataFrame(), {"error": "x"}, "DB"
        )
        pii_items = [i for i in items if i["type"] == "Unmasked PII Column"]
        assert len(pii_items) == 3  # none masked

    def test_masked_pii_skipped(self, pii_df, policy_df):
        items = remediation.generate_all_remediations(
            pii_df, policy_df, pd.DataFrame(), {"error": "x"}, "DB"
        )
        targets = [i["target"] for i in items if i["type"] == "Unmasked PII Column"]
        assert "PUBLIC.CUSTOMERS.USER_EMAIL" not in targets  # already masked
        assert len(targets) == 2

    def test_low_doc_tables_emitted(self, doc_df):
        items = remediation.generate_all_remediations(
            pd.DataFrame(), pd.DataFrame(), doc_df, {"error": "x"}, "DB"
        )
        doc_items = [i for i in items if i["type"] == "Undocumented Table"]
        # only ORDERS has DOC_PCT < 50
        assert len(doc_items) == 1
        assert doc_items[0]["target"] == "PUBLIC.ORDERS"

    def test_overprivileged_users_emitted(self):
        priv = pd.DataFrame(
            {"USER_NAME": list("ABCDE"), "ROLE_NAME": ["ACCOUNTADMIN"] * 5}
        )
        items = remediation.generate_all_remediations(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
            {"error": None, "privileged_users": priv}, "DB",
        )
        assert len([i for i in items if i["type"] == "Overprivileged User"]) == 5

    def test_results_sorted_by_priority(self, pii_df, doc_df):
        priv = pd.DataFrame(
            {"USER_NAME": list("ABCDE"), "ROLE_NAME": ["ACCOUNTADMIN"] * 5}
        )
        items = remediation.generate_all_remediations(
            pii_df, pd.DataFrame(), doc_df,
            {"error": None, "privileged_users": priv}, "DB",
        )
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        ranks = [order[i["priority"]] for i in items]
        assert ranks == sorted(ranks)
