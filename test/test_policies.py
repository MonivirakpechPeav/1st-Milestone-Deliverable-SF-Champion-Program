"""Unit tests for app/services/policies.py (Feature 4 — Policy Coverage)."""
import pandas as pd

from app import policies
from tests.conftest import FakeConn


class TestGetPolicyCoverage:
    def test_returns_rows(self):
        raw = pd.DataFrame(
            {
                "table_schema": ["PUBLIC"], "table_name": ["T"],
                "column_name": ["C"], "policy_name": ["P"],
                "policy_kind": ["MASKING_POLICY"],
            }
        )
        conn = FakeConn(df=raw)
        out = policies.get_policy_coverage(conn, "DB")
        assert out.iloc[0]["POLICY_KIND"] == "MASKING_POLICY"

    def test_empty_returns_empty_schema(self):
        conn = FakeConn(df=pd.DataFrame())
        out = policies.get_policy_coverage(conn, "DB")
        assert out.empty
        assert "POLICY_KIND" in out.columns

    def test_error_returns_empty_schema(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        out = policies.get_policy_coverage(conn, "DB")
        assert out.empty
        assert list(out.columns) == [
            "TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "POLICY_NAME", "POLICY_KIND",
        ]

    def test_schema_filter_uses_ref_schema_name(self):
        conn = FakeConn(df=pd.DataFrame())
        policies.get_policy_coverage(conn, "DB", schema="PUBLIC")
        assert "AND REF_SCHEMA_NAME = 'PUBLIC'" in conn.queries[0]
