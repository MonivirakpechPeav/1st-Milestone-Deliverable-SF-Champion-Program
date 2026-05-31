"""Data Governance Agent — Streamlit entry point.

Top-level navigation is grouped to mirror the Snowflake Horizon Catalog
feature surface and keep the project's unique scoring features clearly
separated from the read-only Horizon mirrors.
"""
import os
import sys

import streamlit as st
from streamlit.runtime import exists as streamlit_runtime_exists

from app.ui import landing, scan, sidebar, styles
from app.ui.tabs import (
    access_audit,
    classification,
    cortex_docs,
    discovery,
    docs,
    guide,
    history,
    lineage,
    overview,
    pii,
    policy,
    quality,
    rbac,
    remediation,
    setup_wizard,
    stewardship,
    tags,
    trust_center,
)


def _ensure_streamlit_runtime():
    """Exit with a useful message when the app is launched as plain Python."""
    if streamlit_runtime_exists():
        return

    app_path = os.path.abspath(__file__)
    print(
        "\nThis is a Streamlit app. Start it with:\n\n"
        f"  streamlit run {app_path}\n\n"
        "Running `python main.py` starts Streamlit in bare mode and cannot "
        "open the app session or Snowflake connection.\n"
    )
    sys.exit(1)


def _connection_ttl():
    value = os.getenv("SNOWFLAKE_CONNECTION_TTL")
    if value and value.isdigit():
        return int(value)
    return value


def _connect_snowflake():
    try:
        return st.connection("snowflake", ttl=_connection_ttl())
    except Exception as exc:
        details = str(exc)
        st.error("Could not connect to Snowflake.")
        st.caption(f"{type(exc).__name__}: {details}")

        if "404 Not Found" in details and "login-request" in details:
            st.info(
                "Snowflake returned 404 for the account host. Check "
                "`[connections.snowflake].account` in `.streamlit/secrets.toml`; "
                "it usually needs the full account identifier from your Snowflake "
                "URL, not just the short locator."
            )
        elif "Could not connect to Snowflake backend" in details:
            st.info(
                "The account host no longer looks like a 404, but Snowflake did "
                "not complete login. Verify the auth method in "
                "`.streamlit/secrets.toml` matches your Snowflake setup "
                "(password, external browser/OAuth, or key-pair auth), and check "
                "VPN/proxy rules if your account requires them."
            )
        else:
            st.info(
                "Check `.streamlit/secrets.toml` and confirm the account, user, "
                "password or authenticator, role, and warehouse are valid."
            )

        with st.expander("Expected local secrets format"):
            st.code(
                """[connections.snowflake]
account = "orgname-accountname"
# Or, for locator-style URLs:
# account = "ve82242.ap-southeast-1.aws"
user = "YOUR_USER"
password = "YOUR_PASSWORD"
role = "ACCOUNTADMIN"
warehouse = "SANDBOX_WH"
""",
                language="toml",
            )

        st.stop()


_ensure_streamlit_runtime()


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Governance Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()

# ── Snowflake connection ─────────────────────────────────────────────────────
conn = _connect_snowflake()

# ── Sidebar ──────────────────────────────────────────────────────────────────
selected_db, selected_schema, run_scan, dbs, history_db = sidebar.render(conn)

# ── Trigger scan ─────────────────────────────────────────────────────────────
if run_scan:
    scan.run(conn, selected_db, selected_schema, history_db)

# ── Landing page (no scan yet) ───────────────────────────────────────────────
if "scan_results" not in st.session_state:
    with st.sidebar:
        st.divider()
        menu = st.radio(
            "Menu",
            ["🏠 Home", "📖 Features & Guide"],
            label_visibility="collapsed",
        )
    if menu == "📖 Features & Guide":
        guide.render()
    else:
        landing.render()
    st.stop()

# ── Render report ────────────────────────────────────────────────────────────
scan_data = st.session_state["scan_results"]
scope     = (
    f"{scan_data['database']}.{scan_data['schema']}"
    if scan_data["schema"] else scan_data["database"]
)
st.markdown(f"# 🛡️ Governance Report — `{scope}`")

section = st.radio(
    "Section",
    ["📊 Insights", "🌐 Horizon Catalog", "🛠️ Governance Actions"],
    horizontal=True,
    label_visibility="collapsed",
)

# ── Section 1 — Insights (project differentiators) ──────────────────────────
if section == "📊 Insights":
    (
        tab_overview, tab_history, tab_inventory,
    ) = st.tabs([
        "📊 Overview & Score", "📈 History", "🧱 Inventory & Docs",
    ])
    with tab_overview:  overview.render(scan_data)
    with tab_history:   history.render(conn, scan_data, history_db)
    with tab_inventory: docs.render(scan_data)

# ── Section 2 — Horizon Catalog mirrors (read-only) ─────────────────────────
elif section == "🌐 Horizon Catalog":
    (
        tab_disc, tab_class, tab_pii, tab_policy, tab_tags,
        tab_lineage, tab_access, tab_quality, tab_steward,
        tab_trust, tab_cortex_docs,
    ) = st.tabs([
        "🔎 Discovery", "🧬 Classification", "🔍 PII (regex)",
        "🛡️ Policies", "🏷️ Tags", "🔗 Lineage", "👁️ Access History",
        "📏 Data Quality", "👥 Stewards", "🔒 Trust Center", "📝 Cortex Docs",
    ])
    with tab_disc:         discovery.render(conn)
    with tab_class:        classification.render(conn, scan_data)
    with tab_pii:          pii.render(scan_data)
    with tab_policy:       policy.render(scan_data)
    with tab_tags:         tags.render(conn, scan_data)
    with tab_lineage:      lineage.render(conn, scan_data)
    with tab_access:       access_audit.render(scan_data)
    with tab_quality:      quality.render(scan_data)
    with tab_steward:      stewardship.render(scan_data)
    with tab_trust:        trust_center.render(conn)
    with tab_cortex_docs:  cortex_docs.render(conn, scan_data)

# ── Section 3 — Governance Actions (write/automation) ───────────────────────
else:
    (
        tab_setup, tab_rbac, tab_remediation,
    ) = st.tabs([
        "🧰 Setup Wizard", "🔐 RBAC Audit", "🔧 Remediation",
    ])
    with tab_setup:        setup_wizard.render(conn, scan_data)
    with tab_rbac:         rbac.render(scan_data)
    with tab_remediation:  remediation.render(conn, scan_data)
