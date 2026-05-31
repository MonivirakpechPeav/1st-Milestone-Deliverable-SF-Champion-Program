"""Unit tests for app/services/classification.py (Feature — Horizon classify)."""
import pandas as pd

from app import classification
from tests.conftest import FakeConn


class TestCreateClassificationProfile:
    def test_builds_create_profile_sql(self):
        conn = FakeConn()
        ok, err = classification.create_classification_profile(
            conn, "DB", "GOV", "MY_PROFILE", auto_tag=True,
            minimum_object_age_for_classification_days=5,
        )
        assert ok is True and err is None
        sql = conn.executed[0]
        assert "CLASSIFICATION_PROFILE" in sql
        assert '"DB"."GOV"."MY_PROFILE"' in sql
        assert "'auto_tag': TRUE" in sql
        assert "5" in sql

    def test_invalid_identifier_raises(self):
        conn = FakeConn()
        import pytest
        with pytest.raises(ValueError):
            classification.create_classification_profile(
                conn, "DB", "GOV", "bad name"
            )


class TestAttachProfileToDatabase:
    def test_alter_database_sql(self):
        conn = FakeConn()
        ok, _ = classification.attach_profile_to_database(conn, "DB.GOV.P", "TARGET")
        assert ok is True
        sql = conn.executed[0]
        assert "ALTER DATABASE TARGET" in sql
        assert "SET CLASSIFICATION_PROFILE = 'DB.GOV.P'" in sql


class TestLatestClassificationSummary:
    def test_aggregation_query_built(self):
        conn = FakeConn(df=pd.DataFrame({"privacy_category": ["IDENTIFIER"],
                                         "semantic_category": ["EMAIL"],
                                         "column_count": [3]}))
        out = classification.latest_classification_summary(conn, "db")
        assert "COLUMN_COUNT" in out.columns
        assert "'DB'" in conn.queries[0]

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert classification.latest_classification_summary(conn, "DB").empty
