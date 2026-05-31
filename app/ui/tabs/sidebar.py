"""Sidebar: database/schema picker, scan trigger, history target."""
import streamlit as st

from app.services.catalog import list_databases, list_schemas


def render(conn):
    """Render the sidebar; returns (selected_db, selected_schema, run_scan, dbs, history_db)."""
    with st.sidebar:
        st.markdown("## 🛡️ Data Governance Agent")
        st.divider()

        with st.spinner("Loading databases..."):
            dbs, db_err = list_databases(conn)

        if not dbs:
            st.error("No databases found.")
            if db_err:
                st.caption(f"Error: `{db_err}`")
            st.stop()

        selected_db = st.selectbox("📦 Database", dbs)

        with st.spinner("Loading schemas..."):
            schemas = list_schemas(conn, selected_db)

        schema_options = ["All schemas"] + schemas
        selected_schema_label = st.selectbox("📂 Schema", schema_options)
        selected_schema = (
            None if selected_schema_label == "All schemas" else selected_schema_label
        )

        st.divider()
        run_scan = st.button(
            "🔍 Run Governance Scan", type="primary", use_container_width=True
        )

        st.divider()
        st.markdown("**📦 History Storage**")
        st.caption("Where to save scan results")
        history_db = st.selectbox(
            "History Database", dbs,
            index=dbs.index(selected_db) if selected_db in dbs else 0,
            key="history_db",
        )

        if "scan_results" in st.session_state:
            st.divider()
            st.success("✅ Scan complete")
            r = st.session_state["scan_results"]
            scope_label = f"{r['database']}.{r['schema']}" if r["schema"] else r["database"]
            st.caption(f"Last scoped to: **{scope_label}**")
            if st.button("🗑️ Clear Results", use_container_width=True):
                del st.session_state["scan_results"]
                for k in ["remediations"]:
                    st.session_state.pop(k, None)
                st.rerun()

    return selected_db, selected_schema, run_scan, dbs, history_db
