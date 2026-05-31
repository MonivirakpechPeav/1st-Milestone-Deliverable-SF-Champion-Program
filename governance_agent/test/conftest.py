"""Shared pytest fixtures for the Data Governance Agent test-suite.

Service modules talk to Snowflake through a small ``conn`` protocol:

    conn.query(sql, ttl=...)            -> pandas.DataFrame
    conn.session().sql(sql).collect()   -> list   (used by exec_sql)
    conn.session().sql(sql).to_pandas() -> pandas.DataFrame (SHOW commands)

``FakeConn`` below implements that protocol in-memory so the services can be
unit-tested without a live Snowflake account. It records every statement it
receives so tests can assert on the generated SQL.
"""
import os
import sys

import pandas as pd
import pytest

# Make the ``app`` package importable when pytest is run from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _FakeSession:
    def __init__(self, conn):
        self._conn = conn

    def sql(self, sql):
        self._conn.executed.append(sql)
        self._conn._last_sql = sql
        return self

    def collect(self):
        if self._conn.raise_exc is not None:
            raise self._conn.raise_exc
        return []

    def to_pandas(self):
        if self._conn.raise_exc is not None:
            raise self._conn.raise_exc
        return self._conn._next_df()


class FakeConn:
    """Programmable stand-in for the Streamlit/Snowflake connection.

    Parameters
    ----------
    df:        single DataFrame returned by every ``query`` / ``to_pandas``.
    dfs:       FIFO list of DataFrames (one per call, in order).
    handler:   callable(sql) -> DataFrame for content-based responses.
    raise_exc: Exception instance raised by query/collect/to_pandas.
    """

    def __init__(self, df=None, dfs=None, handler=None, raise_exc=None):
        self.df = df
        self.dfs = list(dfs) if dfs is not None else None
        self.handler = handler
        self.raise_exc = raise_exc
        self.queries = []      # SQL passed to .query()
        self.executed = []     # SQL passed to session().sql()
        self._last_sql = None

    def query(self, sql, ttl=0):
        self.queries.append(sql)
        if self.raise_exc is not None:
            raise self.raise_exc
        if self.handler is not None:
            return self.handler(sql)
        return self._next_df()

    def session(self):
        return _FakeSession(self)

    def _next_df(self):
        if self.dfs is not None:
            if not self.dfs:
                return pd.DataFrame()
            return self.dfs.pop(0)
        return self.df if self.df is not None else pd.DataFrame()


@pytest.fixture
def fake_conn():
    """Return the FakeConn class so each test builds its own instance."""
    return FakeConn


@pytest.fixture
def pii_df():
    return pd.DataFrame(
        {
            "TABLE_SCHEMA": ["PUBLIC", "PUBLIC", "PUBLIC"],
            "TABLE_NAME": ["CUSTOMERS", "CUSTOMERS", "ORDERS"],
            "COLUMN_NAME": ["USER_EMAIL", "SSN", "CARD_NUM"],
            "DATA_TYPE": ["VARCHAR", "VARCHAR", "VARCHAR"],
            "PII_CATEGORY": ["Email", "SSN / SIN", "Payment Card"],
        }
    )


@pytest.fixture
def policy_df():
    return pd.DataFrame(
        {
            "TABLE_SCHEMA": ["PUBLIC"],
            "TABLE_NAME": ["CUSTOMERS"],
            "COLUMN_NAME": ["USER_EMAIL"],
            "POLICY_NAME": ["MASK_EMAIL"],
            "POLICY_KIND": ["MASKING_POLICY"],
        }
    )


@pytest.fixture
def doc_df():
    return pd.DataFrame(
        {
            "TABLE_SCHEMA": ["PUBLIC", "PUBLIC"],
            "TABLE_NAME": ["CUSTOMERS", "ORDERS"],
            "TOTAL_COLUMNS": [10, 4],
            "DOCUMENTED_COLUMNS": [8, 1],
            "DOC_PCT": [80.0, 25.0],
        }
    )


@pytest.fixture
def rbac_ok():
    return {
        "privileged_users": pd.DataFrame(
            {
                "USER_NAME": ["A", "B", "C", "D", "E"],
                "ROLE_NAME": ["ACCOUNTADMIN"] * 4 + ["SYSADMIN"],
            }
        ),
        "public_grants": pd.DataFrame({"PRIVILEGE": ["USAGE"]}),
        "total_users": 5,
        "total_roles": 9,
        "error": None,
    }
