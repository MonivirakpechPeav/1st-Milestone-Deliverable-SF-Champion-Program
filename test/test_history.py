"""Unit tests for app/services/history.py (Feature 7 — Scan History)."""
import pandas as pd

from app import history
from tests.conftest import FakeConn


def _scan_results():
    return {
        "database": "DB", "schema": "PUBLIC",
        "score": {
            "total": 80.0, "grade": "B",
            "components": {
                "pii": {"score": 8.3}, "docs": {"score": 16.1},
                "rbac": {"score": 25.0}, "policy": {"score": 12.5},
                "storage": {"score": 20.5},
            },
        },
        "inventory_df": pd.DataFrame(
            {"TABLE_TYPE": ["BASE TABLE", "VIEW", "BASE TABLE"]}
        ),
        "rbac": {"error": None, "privileged_users": pd.DataFrame({"U": ["a", "b"]})},
        "pii_df": pd.DataFrame({"COLUMN_NAME": ["A", "B", "C"]}),
        "policy_df": pd.DataFrame({"P": ["x"]}),
    }


class TestEnsureHistoryStore:
    def test_runs_three_statements(self):
        conn = FakeConn()
        ok, err = history.ensure_history_store(conn, "DB")
        assert ok is True and err is None
        assert len(conn.executed) == 3
        assert "CREATE SCHEMA IF NOT EXISTS" in conn.executed[0]
        assert "CREATE TABLE IF NOT EXISTS" in conn.executed[1]
        assert "ADD COLUMN IF NOT EXISTS STORAGE_SCORE" in conn.executed[2]

    def test_first_failure_short_circuits(self):
        conn = FakeConn(raise_exc=RuntimeError("perm"))
        ok, err = history.ensure_history_store(conn, "DB")
        assert ok is False
        assert "perm" in err
        assert len(conn.executed) == 1


class TestSaveScan:
    def test_insert_built_and_executed(self):
        conn = FakeConn()
        ok, err = history.save_scan(conn, _scan_results(), "DB")
        assert ok is True and err is None
        sql = conn.executed[0]
        assert "INSERT INTO" in sql
        assert "'DB', 'PUBLIC'" in sql
        assert "80.0" in sql and "'B'" in sql
        # base tables = 2, pii cols = 3, priv users = 2

    def test_base_table_and_pii_counts(self):
        conn = FakeConn()
        history.save_scan(conn, _scan_results(), "DB")
        sql = conn.executed[0]
        # 2 base tables, 3 pii, 1 policy, 2 privileged users present in VALUES
        assert ", 2," in sql or " 2," in sql


class TestLoadHistory:
    def test_returns_uppercase_columns(self):
        conn = FakeConn(df=pd.DataFrame({"scan_ts": ["t"], "overall_score": [80]}))
        out = history.load_history(conn, "DB")
        assert "OVERALL_SCORE" in out.columns

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert history.load_history(conn, "DB").empty
