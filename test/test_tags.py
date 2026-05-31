"""Unit tests for app/services/tags.py (Feature — Tags & tag-based masking)."""
import pandas as pd

from app import tags
from tests.conftest import FakeConn


class TestListTags:
    def test_account_wide_filter(self):
        conn = FakeConn(df=pd.DataFrame({"tag_name": ["PII"]}))
        tags.list_tags(conn)
        assert "WHERE DELETED IS NULL" in conn.queries[0]

    def test_database_scoped_filter(self):
        conn = FakeConn(df=pd.DataFrame({"tag_name": ["PII"]}))
        tags.list_tags(conn, database="DB")
        assert "TAG_DATABASE = 'DB'" in conn.queries[0]

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert tags.list_tags(conn).empty


class TestTagReferences:
    def test_scoped(self):
        conn = FakeConn(df=pd.DataFrame({"tag_name": ["PII"]}))
        tags.tag_references(conn, database="DB")
        assert "OBJECT_DATABASE = 'DB'" in conn.queries[0]


class TestGenerateTagSql:
    def test_without_allowed_values(self):
        out = tags.generate_tag_sql("DB", "GOV", "SENSITIVITY")
        assert out == "CREATE TAG IF NOT EXISTS DB.GOV.SENSITIVITY;"

    def test_with_allowed_values(self):
        out = tags.generate_tag_sql("DB", "GOV", "SENSITIVITY", ["LOW", "HIGH"])
        assert "ALLOWED_VALUES 'LOW', 'HIGH'" in out


class TestGenerateTagAssignmentSql:
    def test_assignment(self):
        out = tags.generate_tag_assignment_sql("TABLE", "DB.S.T", "DB.GOV.PII", "YES")
        assert out == "ALTER TABLE DB.S.T\n  SET TAG DB.GOV.PII = 'YES';"
