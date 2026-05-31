"""Unit tests for app/services/quality.py (Feature 16 — Data Metric Functions)."""
import pandas as pd

from app import quality
from tests.conftest import FakeConn


class TestGetDmfCoverage:
    def test_counts_distinct_tables_with_dmf(self):
        df = pd.DataFrame({
            "database_name": ["DB", "DB", "DB"],
            "schema_name": ["S", "S", "S"],
            "table_name": ["A", "A", "B"],
            "metric_name": ["NULL_COUNT", "ROW_COUNT", "NULL_COUNT"],
            "metric_schema_name": ["CORE"] * 3,
            "schedule": ["5 MINUTE"] * 3,
        })
        conn = FakeConn(df=df)
        out = quality.get_dmf_coverage(conn, "DB")
        assert out["error"] is None
        assert out["tables_with_dmf"] == 2

    def test_schema_filter(self):
        conn = FakeConn(df=pd.DataFrame())
        quality.get_dmf_coverage(conn, "DB", schema="S")
        assert "REF_SCHEMA_NAME = 'S'" in conn.queries[0]

    def test_error_captured(self):
        conn = FakeConn(raise_exc=RuntimeError("denied"))
        out = quality.get_dmf_coverage(conn, "DB")
        assert "denied" in out["error"]
        assert out["tables_with_dmf"] == 0


class TestBuiltinDmfs:
    def test_six_builtins(self):
        assert len(quality.BUILTIN_DMFS) == 6
        assert quality.BUILTIN_DMFS["Row count"] == "SNOWFLAKE.CORE.ROW_COUNT"


class TestGenerateDmfAttachSql:
    def test_table_level(self):
        out = quality.generate_dmf_attach_sql("DB.S.T", "SNOWFLAKE.CORE.ROW_COUNT")
        assert "SET DATA_METRIC_SCHEDULE" in out
        assert "ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.ROW_COUNT" in out
        assert "ON ();" in out

    def test_column_level(self):
        out = quality.generate_dmf_attach_sql(
            "DB.S.T", "SNOWFLAKE.CORE.NULL_COUNT", column="EMAIL"
        )
        assert "ON (EMAIL);" in out

    def test_custom_schedule(self):
        out = quality.generate_dmf_attach_sql(
            "DB.S.T", "SNOWFLAKE.CORE.ROW_COUNT", schedule="60 MINUTE"
        )
        assert "'60 MINUTE'" in out
