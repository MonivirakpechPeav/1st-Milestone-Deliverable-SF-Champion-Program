"""Unit tests for app/services/trust_center.py (Feature — Trust Center)."""
import pandas as pd

from app import trust_center
from tests.conftest import FakeConn


class TestGetFindings:
    def test_returns_normalized(self):
        conn = FakeConn(df=pd.DataFrame({"severity": ["HIGH"], "scanner_name": ["S"]}))
        out = trust_center.get_findings(conn)
        assert "SEVERITY" in out.columns

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert trust_center.get_findings(conn).empty


class TestSeveritySummary:
    def test_counts_by_severity(self):
        df = pd.DataFrame({"SEVERITY": ["HIGH", "HIGH", "LOW", None]})
        out = trust_center.severity_summary(df)
        counts = dict(zip(out["SEVERITY"], out["COUNT"]))
        assert counts["HIGH"] == 2
        assert counts["LOW"] == 1
        assert counts["UNKNOWN"] == 1

    def test_empty_df(self):
        out = trust_center.severity_summary(pd.DataFrame())
        assert list(out.columns) == ["SEVERITY", "COUNT"]
        assert out.empty

    def test_missing_severity_column(self):
        out = trust_center.severity_summary(pd.DataFrame({"X": [1]}))
        assert out.empty


class TestListScanners:
    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert trust_center.list_scanners(conn).empty
