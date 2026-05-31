"""Unit tests for app/services/inventory.py (Feature 2 — Inventory & Docs)."""
import pandas as pd

from app import inventory
from tests.conftest import FakeConn


class TestGetTableInventory:
    def test_returns_normalized_dataframe(self):
        raw = pd.DataFrame(
            {
                "table_schema": ["PUBLIC"], "table_name": ["T"],
                "table_type": ["BASE TABLE"], "row_count": [10],
                "bytes": [1024], "last_altered": ["2024-01-01"], "comment": [""],
            }
        )
        conn = FakeConn(df=raw)
        out = inventory.get_table_inventory(conn, "DB")
        assert "TABLE_NAME" in out.columns
        assert out.iloc[0]["TABLE_NAME"] == "T"

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert inventory.get_table_inventory(conn, "DB").empty

    def test_schema_filter_applied(self):
        conn = FakeConn(df=pd.DataFrame({"TABLE_NAME": []}))
        inventory.get_table_inventory(conn, "DB", schema="PUBLIC")
        assert "AND TABLE_SCHEMA = 'PUBLIC'" in conn.queries[0]


class TestGetSchemaDocCoverage:
    def test_doc_pct_computed(self):
        raw = pd.DataFrame(
            {
                "table_schema": ["PUBLIC", "PUBLIC"],
                "table_name": ["A", "B"],
                "total_columns": [4, 0],
                "documented_columns": [2, 0],
            }
        )
        conn = FakeConn(df=raw)
        out = inventory.get_schema_doc_coverage(conn, "DB")
        assert out.iloc[0]["DOC_PCT"] == 50.0
        # division guarded by clip(lower=1) -> 0/1 = 0.0
        assert out.iloc[1]["DOC_PCT"] == 0.0

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert inventory.get_schema_doc_coverage(conn, "DB").empty
