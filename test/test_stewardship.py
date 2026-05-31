"""Unit tests for app/services/stewardship.py (Feature 14 — Object Contacts)."""
import pandas as pd

from app import stewardship
from tests.conftest import FakeConn


class TestGetObjectContacts:
    def test_references_and_contacts_parsed(self):
        refs = pd.DataFrame({"object_name": ["T"], "contact_name": ["C"]})
        contacts = pd.DataFrame({"contact_name": ["C"]})
        conn = FakeConn(dfs=[refs, contacts])
        out = stewardship.get_object_contacts(conn, "DB")
        assert out["error"] is None
        assert not out["references"].empty
        assert not out["contacts"].empty
        assert "OBJECT_DATABASE = 'DB'" in conn.queries[0]

    def test_contacts_view_failure_is_swallowed(self):
        refs = pd.DataFrame({"object_name": ["T"]})
        # second query raises -> caught inside, contacts becomes empty
        def handler(sql):
            if "CONTACT_REFERENCES" in sql:
                return refs
            raise RuntimeError("contacts view missing")
        conn = FakeConn(handler=handler)
        out = stewardship.get_object_contacts(conn)
        assert out["error"] is None
        assert out["contacts"].empty
        assert not out["references"].empty

    def test_references_failure_sets_error(self):
        conn = FakeConn(raise_exc=RuntimeError("denied"))
        out = stewardship.get_object_contacts(conn)
        assert "denied" in out["error"]


class TestGenerateContactSql:
    def test_valid_purpose(self):
        out = stewardship.generate_contact_sql(
            "DATA_TEAM", "steward", "TABLE", "DB.S.T", email="x@y.com"
        )
        assert "CREATE CONTACT IF NOT EXISTS DATA_TEAM" in out
        assert "EMAIL_DISTRIBUTION_LIST = 'x@y.com'" in out
        assert "SET CONTACT STEWARD = DATA_TEAM" in out
        assert "ALTER TABLE DB.S.T" in out

    def test_invalid_purpose_falls_back_to_steward(self):
        out = stewardship.generate_contact_sql("C", "NONSENSE", "TABLE", "DB.S.T")
        assert "SET CONTACT STEWARD = C" in out

    def test_no_email_omits_distribution_list(self):
        out = stewardship.generate_contact_sql("C", "SUPPORT", "VIEW", "DB.S.V")
        assert "EMAIL_DISTRIBUTION_LIST" not in out
