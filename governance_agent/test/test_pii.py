"""Unit tests for app/services/pii.py (Feature 3 — PII Detection)."""
import pandas as pd

from app import pii
from app import PII_CATEGORIES
from tests.conftest import FakeConn


def _cols(*names):
    return pd.DataFrame(
        {
            "TABLE_SCHEMA": ["PUBLIC"] * len(names),
            "TABLE_NAME": ["T"] * len(names),
            "COLUMN_NAME": list(names),
            "DATA_TYPE": ["VARCHAR"] * len(names),
        }
    )


class TestDetectPiiColumns:
    def test_matches_known_categories(self):
        conn = FakeConn(df=_cols("USER_EMAIL", "HOME_PHONE", "SSN", "NOTES"))
        out = pii.detect_pii_columns(conn, "DB")
        cats = dict(zip(out["COLUMN_NAME"], out["PII_CATEGORY"]))
        assert cats["USER_EMAIL"] == "Email"
        assert cats["HOME_PHONE"] == "Phone"
        assert cats["SSN"] == "SSN / SIN"
        assert "NOTES" not in cats  # no PII match

    def test_first_matching_category_wins(self):
        # declaration order: Email before others
        conn = FakeConn(df=_cols("EMAIL"))
        out = pii.detect_pii_columns(conn, "DB")
        assert out.iloc[0]["PII_CATEGORY"] == "Email"

    def test_empty_input_returns_empty_schema(self):
        conn = FakeConn(df=pd.DataFrame())
        out = pii.detect_pii_columns(conn, "DB")
        assert out.empty
        assert list(out.columns) == [
            "TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "DATA_TYPE", "PII_CATEGORY",
        ]

    def test_query_failure_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("denied"))
        out = pii.detect_pii_columns(conn, "DB")
        assert out.empty

    def test_no_matches_returns_empty(self):
        conn = FakeConn(df=_cols("ID", "CREATED_AT", "STATUS"))
        out = pii.detect_pii_columns(conn, "DB")
        assert out.empty

    def test_schema_scoping_builds_filter(self):
        conn = FakeConn(df=_cols("EMAIL"))
        pii.detect_pii_columns(conn, "DB", schema="PUBLIC")
        assert "AND TABLE_SCHEMA = 'PUBLIC'" in conn.queries[0]


class TestPiiCategoryConfig:
    def test_twelve_categories_defined(self):
        assert len(PII_CATEGORIES) == 12

    def test_all_patterns_are_strings(self):
        assert all(isinstance(p, str) for p in PII_CATEGORIES.values())
