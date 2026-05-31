"""Unit tests for app/services/discovery.py (Feature 1 — Universal Search)."""
import pandas as pd

from app import discovery
from tests.conftest import FakeConn


class TestSearchObjects:
    def test_blank_query_returns_empty_without_hitting_db(self):
        conn = FakeConn(df=pd.DataFrame({"x": [1]}))
        out = discovery.search_objects(conn, "")
        assert out.empty
        assert conn.queries == []

    def test_query_uppercased_and_escaped(self):
        conn = FakeConn(df=pd.DataFrame({"table_name": ["CUST"]}))
        discovery.search_objects(conn, "cust'omer")
        sql = conn.queries[0]
        assert "%CUST''OMER%" in sql

    def test_results_normalized(self):
        conn = FakeConn(df=pd.DataFrame({"table_name": ["CUST"]}))
        out = discovery.search_objects(conn, "cust")
        assert "TABLE_NAME" in out.columns

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert discovery.search_objects(conn, "a").empty


class TestSearchColumns:
    def test_blank_returns_empty(self):
        conn = FakeConn()
        assert discovery.search_columns(conn, "").empty
        assert conn.queries == []

    def test_limit_in_sql(self):
        conn = FakeConn(df=pd.DataFrame({"column_name": ["X"]}))
        discovery.search_columns(conn, "email", limit=10)
        assert "LIMIT 10" in conn.queries[0]


class TestListSemanticViews:
    def test_runs_show_command(self):
        conn = FakeConn(df=pd.DataFrame({"name": ["SV"]}))
        out = discovery.list_semantic_views(conn)
        assert "SHOW SEMANTIC VIEWS IN ACCOUNT" in conn.queries[0]
        assert not out.empty

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert discovery.list_semantic_views(conn).empty


class TestListInternalListings:
    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert discovery.list_internal_listings(conn).empty
