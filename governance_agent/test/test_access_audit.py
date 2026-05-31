"""Unit tests for app/services/access_audit.py (Feature 13 — Access Audit)."""
import pandas as pd

from app import access_audit
from tests.conftest import FakeConn


def _audit_dfs():
    readers = pd.DataFrame({"user_name": ["A"], "query_count": [5]})
    objects = pd.DataFrame({"object_name": ["T"], "object_domain": ["TABLE"],
                            "access_count": [3], "distinct_users": [2]})
    off_hours = pd.DataFrame({"user_name": ["A"], "query_id": ["q1"],
                              "query_start_time": ["2024-01-01 03:00"]})
    mods = pd.DataFrame({"object_name": ["T"], "mod_count": [1], "distinct_users": [1]})
    total = pd.DataFrame({"c": [42]})
    return [readers, objects, off_hours, mods, total]


class TestGetAccessAudit:
    def test_parses_all_panels(self):
        conn = FakeConn(dfs=_audit_dfs())
        out = access_audit.get_access_audit(conn, days=7)
        assert out["error"] is None
        assert out["total_queries"] == 42
        assert out["days"] == 7
        assert out["top_readers"].iloc[0]["USER_NAME"] == "A"

    def test_invalid_days_defaults_to_7(self):
        conn = FakeConn(dfs=_audit_dfs())
        out = access_audit.get_access_audit(conn, days=999)
        assert out["days"] == 7
        assert "DATEADD(day, -7" in conn.queries[0]

    def test_error_captured(self):
        conn = FakeConn(raise_exc=RuntimeError("no access"))
        out = access_audit.get_access_audit(conn)
        assert "no access" in out["error"]
        assert out["total_queries"] == 0
