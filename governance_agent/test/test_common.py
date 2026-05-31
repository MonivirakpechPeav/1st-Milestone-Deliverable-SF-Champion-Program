"""Unit tests for app/services/_common.py (Feature 17.1 — Identifier Safety)."""
import pandas as pd
import pytest

from app import (
    clean_db,
    exec_sql,
    normalize_columns,
    safe_id,
    schema_filter,
)
from tests.conftest import FakeConn


class TestSafeId:
    @pytest.mark.parametrize("ident", ["DB", "my_db", "DB$1", "Table_99"])
    def test_valid_identifiers_pass_through(self, ident):
        assert safe_id(ident) == ident

    @pytest.mark.parametrize(
        "bad", ["DB; DROP TABLE", "my db", "a'b", 'a"b', "tbl-name", "tbl.name", ""]
    )
    def test_invalid_identifiers_raise(self, bad):
        with pytest.raises(ValueError):
            safe_id(bad)


class TestNormalizeColumns:
    def test_strips_quotes_and_uppercases(self):
        df = pd.DataFrame({'"name"': [1], "Value": [2]})
        out = normalize_columns(df)
        assert list(out.columns) == ["NAME", "VALUE"]

    def test_mutates_in_place_and_returns(self):
        df = pd.DataFrame({"a": [1]})
        out = normalize_columns(df)
        assert out is df
        assert list(df.columns) == ["A"]


class TestSchemaFilter:
    def test_none_returns_empty(self):
        assert schema_filter(None) == ""

    def test_default_column(self):
        assert schema_filter("PUBLIC") == "AND TABLE_SCHEMA = 'PUBLIC'"

    def test_custom_column(self):
        assert schema_filter("PUBLIC", col="REF_SCHEMA_NAME") == (
            "AND REF_SCHEMA_NAME = 'PUBLIC'"
        )

    def test_injection_attempt_raises(self):
        with pytest.raises(ValueError):
            schema_filter("PUBLIC'; DROP")


class TestCleanDb:
    def test_strips_single_and_double_quotes(self):
        assert clean_db('"My"Db') == "MyDb"
        assert clean_db("O'Brien") == "OBrien"

    def test_plain_name_untouched(self):
        assert clean_db("ANALYTICS") == "ANALYTICS"


class TestExecSql:
    def test_success_returns_ok_none(self):
        conn = FakeConn()
        ok, err = exec_sql(conn, "CREATE SCHEMA X")
        assert ok is True and err is None
        assert conn.executed == ["CREATE SCHEMA X"]

    def test_failure_returns_false_and_message(self):
        conn = FakeConn(raise_exc=RuntimeError("boom"))
        ok, err = exec_sql(conn, "CREATE SCHEMA X")
        assert ok is False
        assert "boom" in err
