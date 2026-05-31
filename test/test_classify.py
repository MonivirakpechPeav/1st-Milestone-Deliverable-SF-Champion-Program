"""Unit tests for app/services/classify.py (Feature — value-based classify)."""
import json

import pandas as pd

from app import classify
from tests.conftest import FakeConn


_PAYLOAD = {
    "classification_result": {
        "email": {
            "valid_value_ratio": 0.98,
            "recommendation": {
                "semantic_category": "EMAIL",
                "privacy_category": "IDENTIFIER",
                "extra_info": {"probability": 0.9},
            },
        }
    }
}


class TestClassifyTable:
    def test_parses_dict_payload(self):
        conn = FakeConn(df=pd.DataFrame({"RESULT": [_PAYLOAD]}))
        out = classify.classify_table(conn, "DB", "PUBLIC", "T")
        assert out.iloc[0]["COLUMN_NAME"] == "EMAIL"
        assert out.iloc[0]["SEMANTIC_CATEGORY"] == "EMAIL"
        assert out.iloc[0]["PRIVACY_CATEGORY"] == "IDENTIFIER"

    def test_parses_json_string_payload(self):
        conn = FakeConn(df=pd.DataFrame({"RESULT": [json.dumps(_PAYLOAD)]}))
        out = classify.classify_table(conn, "DB", "PUBLIC", "T")
        assert out.iloc[0]["COLUMN_NAME"] == "EMAIL"

    def test_invalid_json_returns_empty(self):
        conn = FakeConn(df=pd.DataFrame({"RESULT": ["not-json"]}))
        out = classify.classify_table(conn, "DB", "PUBLIC", "T")
        assert out.empty
        assert "SEMANTIC_CATEGORY" in out.columns

    def test_query_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert classify.classify_table(conn, "DB", "S", "T").empty

    def test_empty_result_returns_empty(self):
        conn = FakeConn(df=pd.DataFrame())
        assert classify.classify_table(conn, "DB", "S", "T").empty


class TestLatestClassification:
    def test_query_uses_uppercase_db(self):
        conn = FakeConn(df=pd.DataFrame({"column_name": ["E"]}))
        classify.latest_classification(conn, "db", schema="pub")
        sql = conn.queries[0]
        assert "'DB'" in sql
        assert "t.SCHEMA_NAME = 'PUB'" in sql

    def test_error_returns_empty(self):
        conn = FakeConn(raise_exc=RuntimeError("x"))
        assert classify.latest_classification(conn, "DB").empty
