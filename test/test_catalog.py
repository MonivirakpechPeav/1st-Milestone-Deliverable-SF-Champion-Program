"""Unit tests for app/services/catalog.py (Feature 1 — Scan scope picker)."""
import pandas as pd
import pytest

from app import catalog
from tests.conftest import FakeConn


class TestListDatabases:
    def test_sorted_names_returned(self):
        conn = FakeConn(df=pd.DataFrame({"name": ["Z_DB", "A_DB"]}))
        names, err = catalog.list_databases(conn)
        assert err is None
        assert names == ["A_DB", "Z_DB"]

    def test_missing_name_column_reports_error(self):
        conn = FakeConn(df=pd.DataFrame({"other": [1]}))
        names, err = catalog.list_databases(conn)
        assert names == []
        assert "Unexpected columns" in err

    def test_exception_reported(self):
        conn = FakeConn(raise_exc=RuntimeError("boom"))
        names, err = catalog.list_databases(conn)
        assert names == []
        assert "RuntimeError" in err


class TestListSchemas:
    def test_filters_information_schema(self):
        conn = FakeConn(df=pd.DataFrame({"name": ["PUBLIC", "INFORMATION_SCHEMA", "RAW"]}))
        assert catalog.list_schemas(conn, "DB") == ["PUBLIC", "RAW"]

    def test_error_returns_empty_list(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert catalog.list_schemas(conn, "DB") == []

    def test_invalid_db_raises_value_error(self):
        conn = FakeConn()
        with pytest.raises(ValueError):
            catalog.list_schemas(conn, "DB; DROP")


class TestListTables:
    def test_sorted(self):
        conn = FakeConn(df=pd.DataFrame({"name": ["B", "A"]}))
        assert catalog.list_tables(conn, "DB", "PUBLIC") == ["A", "B"]

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert catalog.list_tables(conn, "DB", "PUBLIC") == []
