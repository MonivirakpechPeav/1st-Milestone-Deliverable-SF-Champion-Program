"""Centralized setup wizard for Horizon-aligned governance configuration.

Generates and (optionally) executes the SQL for the most common
Horizon Catalog setup tasks in one place — replacing the need to
navigate Snowsight's many separate config pages.
"""
import streamlit as st

from ...services._common import exec_sql
from ...services.catalog import list_databases, list_schemas, list_tables
from ...services.classification import (
    attach_profile_to_database,
    create_classification_profile,
)
from ...services.stewardship import generate_contact_sql
from ...services.tags import generate_tag_assignment_sql, generate_tag_sql


def _idx(options: list, value: str) -> int:
    return options.index(value) if value in options else 0


def _db_select(conn, dbs: list, default: str, key: str):
    return st.selectbox("Database", dbs, index=_idx(dbs, default), key=key)


def _schema_select(conn, database: str, default: str, key: str, allow_new: bool = False):
    schemas = list_schemas(conn, database) if database else []
    options = schemas if default in schemas else ([default] + schemas if allow_new and default else schemas)
    return st.selectbox(
        "Schema", options, index=_idx(options, default),
        key=key, accept_new_options=allow_new,
        help="Pick an existing schema or type a new one to create it." if allow_new else None,
    )


def render(conn, scan: dict):
    st.subheader("🧰 Horizon Setup Wizard")
    st.caption(
        "One-click configuration of the Horizon Catalog primitives that "
        "normally require visiting many Snowsight pages."
    )

    db = scan.get("database") or ""
    dbs, _ = list_databases(conn)
    if not dbs:
        dbs = [db] if db else []

    step = st.radio(
        "Step",
        [
            "1. Classification Profile (auto-tag)",
            "2. Sensitivity tag",
            "3. Tag-based masking policy",
            "4. Object steward / contact",
            "5. Enable a Trust Center scanner",
        ],
        horizontal=False,
    )

    st.divider()

    if step.startswith("1"):
        c1, c2, c3 = st.columns(3)
        with c1: pdb = _db_select(conn, dbs, db, "p1_db")
        with c2: psc = _schema_select(conn, pdb, "GOVERNANCE", "p1_sch", allow_new=True)
        with c3: pnm = st.text_input("Profile name", value="GOV_AGENT_PROFILE")
        auto = st.checkbox("auto_tag", value=True)
        attach = _db_select(conn, dbs, db, "p1_attach")
        if st.button("Create + attach", type="primary"):
            ok, err = exec_sql(conn, f'CREATE SCHEMA IF NOT EXISTS "{pdb}"."{psc}";')
            if not ok:
                st.error(err); st.stop()
            ok, err = create_classification_profile(conn, pdb, psc, pnm, auto_tag=auto)
            if not ok:
                st.error(err); st.stop()
            ok, err = attach_profile_to_database(conn, f"{pdb}.{psc}.{pnm}", attach)
            st.success("Profile created & attached.") if ok else st.error(err)

    elif step.startswith("2"):
        c1, c2 = st.columns(2)
        with c1: tdb  = _db_select(conn, dbs, db, "t2_db")
        with c2: tsch = _schema_select(conn, tdb, "GOVERNANCE", "t2_sch", allow_new=True)
        tnm  = st.text_input("Tag name", value="DATA_SENSITIVITY")
        avs  = st.text_input("Allowed values",
                             value="PUBLIC,INTERNAL,CONFIDENTIAL,RESTRICTED")
        sql  = (
            f'CREATE SCHEMA IF NOT EXISTS "{tdb}"."{tsch}";\n\n'
            + generate_tag_sql(tdb, tsch, tnm,
                               [v.strip() for v in avs.split(",") if v.strip()])
        )
        st.code(sql, language="sql")
        if st.button("Run", type="primary"):
            for stmt in [s for s in sql.split(";") if s.strip()]:
                ok, err = exec_sql(conn, stmt + ";")
                if not ok:
                    st.error(err); st.stop()
            st.success("Tag created.")

    elif step.startswith("3"):
        st.write("Generate a tag-based masking policy that applies wherever "
                 "DATA_SENSITIVITY = 'CONFIDENTIAL'.")
        c1, c2 = st.columns(2)
        with c1: pol_db  = _db_select(conn, dbs, db, "p3_db")
        with c2: pol_sch = _schema_select(conn, pol_db, "GOVERNANCE", "p3_sch", allow_new=True)
        pol_nm  = st.text_input("Policy name",   value="MASK_CONFIDENTIAL_STR")
        tag_fqn = st.text_input("Tag FQN",
                                value=f"{db}.GOVERNANCE.DATA_SENSITIVITY")
        sql = (
            f"CREATE SCHEMA IF NOT EXISTS \"{pol_db}\".\"{pol_sch}\";\n\n"
            f"CREATE OR REPLACE MASKING POLICY \"{pol_db}\".\"{pol_sch}\".\"{pol_nm}\"\n"
            f"  AS (val STRING) RETURNS STRING ->\n"
            f"  CASE WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN','SECURITYADMIN')\n"
            f"       THEN val ELSE '***REDACTED***' END;\n\n"
            f"ALTER TAG {tag_fqn}\n"
            f"  SET MASKING POLICY \"{pol_db}\".\"{pol_sch}\".\"{pol_nm}\";"
        )
        st.code(sql, language="sql")
        if st.button("Run all", type="primary"):
            for stmt in [s for s in sql.split(";") if s.strip()]:
                ok, err = exec_sql(conn, stmt + ";")
                if not ok:
                    st.error(err); st.stop()
            st.success("Policy created and bound to tag.")

    elif step.startswith("4"):
        cnm = st.text_input("Contact name", value="DATA_STEWARDS")
        em  = st.text_input("Email distribution list (optional)",
                            value="data-stewards@example.com")
        otype = st.selectbox("Object type", ["TABLE", "VIEW", "SCHEMA", "DATABASE"])

        o_db = _db_select(conn, dbs, db, "c4_db")
        if otype == "DATABASE":
            fqn = o_db
        else:
            o_sch = _schema_select(conn, o_db, "PUBLIC", "c4_sch")
            if otype == "SCHEMA":
                fqn = f"{o_db}.{o_sch}"
            else:
                tables = list_tables(conn, o_db, o_sch)
                o_tbl = st.selectbox("Object", tables, key="c4_tbl") if tables \
                    else st.text_input("Object name (none found)", key="c4_tbl_txt")
                fqn = f"{o_db}.{o_sch}.{o_tbl}" if o_tbl else ""

        purpose = st.selectbox("Purpose",
                               ["STEWARD", "ACCESS_APPROVAL", "SECURITY_COMPLIANCE", "SUPPORT"])
        if fqn:
            sql = generate_contact_sql(cnm, purpose, otype, fqn, em or None)
            st.code(sql, language="sql")

    elif step.startswith("5"):
        st.write("Enable a Trust Center scanner package for the account.")
        pkg = st.selectbox("Scanner package", [
            "SNOWFLAKE.TRUST_CENTER.CIS_BENCHMARK_SCANNER_PACKAGE",
            "SNOWFLAKE.TRUST_CENTER.SECURITY_ESSENTIALS_SCANNER_PACKAGE",
            "SNOWFLAKE.TRUST_CENTER.THREAT_INTELLIGENCE_SCANNER_PACKAGE",
        ])
        sql = (
            f"CALL SNOWFLAKE.TRUST_CENTER.ENABLE_SCANNER_PACKAGE('{pkg}');"
        )
        st.code(sql, language="sql")
        if st.button("Run", type="primary"):
            ok, err = exec_sql(conn, sql)
            st.success("Scanner package enabled.") if ok else st.error(err)
