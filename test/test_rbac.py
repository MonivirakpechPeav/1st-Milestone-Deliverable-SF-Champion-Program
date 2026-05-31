"""Unit tests for app/services/rbac.py (Feature 5 — RBAC Audit)."""
import pandas as pd

from app import rbac
from tests.conftest import FakeConn


class TestGetRbacSummary:
    def test_parses_three_queries_in_order(self):
        priv = pd.DataFrame({"user_name": ["A"], "role_name": ["ACCOUNTADMIN"]})
        pub = pd.DataFrame({"privilege": ["USAGE"], "object_name": ["X"],
                            "granted_on": ["DB"]})
        counts = pd.DataFrame({"total_users": [12], "total_roles": [7]})
        conn = FakeConn(dfs=[priv, pub, counts])
        out = rbac.get_rbac_summary(conn)
        assert out["error"] is None
        assert out["total_users"] == 12
        assert out["total_roles"] == 7
        assert out["privileged_users"].iloc[0]["USER_NAME"] == "A"
        assert not out["public_grants"].empty

    def test_error_captured(self):
        conn = FakeConn(raise_exc=RuntimeError("ACCOUNT_USAGE denied"))
        out = rbac.get_rbac_summary(conn)
        assert "denied" in out["error"]
        assert out["total_users"] == 0
        assert out["privileged_users"].empty

    def test_privileged_role_list_in_query(self):
        conn = FakeConn(dfs=[pd.DataFrame(), pd.DataFrame(),
                             pd.DataFrame({"total_users": [0], "total_roles": [0]})])
        rbac.get_rbac_summary(conn)
        assert "ACCOUNTADMIN" in conn.queries[0]
        assert "GRANTS_TO_USERS" in conn.queries[0]
