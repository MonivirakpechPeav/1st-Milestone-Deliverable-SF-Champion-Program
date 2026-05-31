"""Unit tests for app/services/lineage.py (Feature 15 — Lineage Explorer)."""
import pandas as pd

from app import lineage
from tests.conftest import FakeConn


class TestGetLineage:
    def test_builds_get_lineage_call(self):
        conn = FakeConn(df=pd.DataFrame({"source": ["X"]}))
        lineage.get_lineage(conn, "DB.S.T", "TABLE", "UPSTREAM", 2)
        sql = conn.queries[0]
        assert "SNOWFLAKE.CORE.GET_LINEAGE" in sql
        assert "'DB.S.T'" in sql
        assert "'UPSTREAM'" in sql

    def test_invalid_direction_defaults_downstream(self):
        conn = FakeConn(df=pd.DataFrame())
        lineage.get_lineage(conn, "DB.S.T", direction="SIDEWAYS")
        assert "'DOWNSTREAM'" in conn.queries[0]

    def test_distance_clamped_to_max_5(self):
        conn = FakeConn(df=pd.DataFrame())
        lineage.get_lineage(conn, "DB.S.T", distance=99)
        assert "5\n" in conn.queries[0] or ", 5" in conn.queries[0]

    def test_distance_clamped_to_min_1(self):
        conn = FakeConn(df=pd.DataFrame())
        lineage.get_lineage(conn, "DB.S.T", distance=0)
        assert ", 1" in conn.queries[0] or "1\n" in conn.queries[0]

    def test_single_quote_escaped(self):
        conn = FakeConn(df=pd.DataFrame())
        lineage.get_lineage(conn, "DB.S.O'HARA")
        assert "O''HARA" in conn.queries[0]

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert lineage.get_lineage(conn, "DB.S.T").empty


class TestGetColumnLineage:
    def test_builds_column_fqn(self):
        conn = FakeConn(df=pd.DataFrame())
        lineage.get_column_lineage(conn, "DB", "S", "T", "C")
        sql = conn.queries[0]
        assert "'DB.S.T.C'" in sql
        assert "'COLUMN'" in sql
