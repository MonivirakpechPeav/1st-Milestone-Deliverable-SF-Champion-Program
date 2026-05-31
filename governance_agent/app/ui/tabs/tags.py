"""Tag inventory & assignment tab (Horizon Catalog tagging)."""
import streamlit as st

from ...services.tags import (
    generate_tag_assignment_sql,
    generate_tag_sql,
    list_tags,
    tag_references,
)


def render(conn, scan: dict):
    st.subheader("🏷️ Tags & Tag-Based Governance")
    st.caption(
        "Inventory of tags and where they are applied. Tags drive tag-based "
        "masking, classification auto-tagging, and Horizon Catalog filtering."
    )

    db = scan.get("database") or None

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Defined Tags")
        with st.spinner("Loading tags..."):
            tags = list_tags(conn, db)
        if tags.empty:
            st.info("No tags found in scope.")
        else:
            st.dataframe(tags, use_container_width=True, hide_index=True)
    with c2:
        st.markdown("#### Tag Assignments")
        with st.spinner("Loading tag references..."):
            refs = tag_references(conn, db)
        if refs.empty:
            st.info("No tag references found in scope.")
        else:
            st.dataframe(refs, use_container_width=True, hide_index=True)

    st.divider()
    with st.expander("➕ Generate tag DDL", expanded=False):
        tdb  = st.text_input("Tag database", value=db or "")
        tsch = st.text_input("Tag schema", value="GOVERNANCE")
        tnm  = st.text_input("Tag name",   value="DATA_SENSITIVITY")
        avs  = st.text_input("Allowed values (comma-separated, optional)",
                             value="PUBLIC,INTERNAL,CONFIDENTIAL,RESTRICTED")
        if tdb and tsch and tnm:
            allowed = [v.strip() for v in avs.split(",") if v.strip()] or None
            st.code(generate_tag_sql(tdb, tsch, tnm, allowed), language="sql")

    with st.expander("🏷️ Generate tag assignment DDL", expanded=False):
        otype = st.selectbox("Object type", ["TABLE", "VIEW", "COLUMN", "SCHEMA", "DATABASE"])
        fqn   = st.text_input("Fully qualified object name",
                              value=f"{db}.PUBLIC.MY_TABLE" if db else "DB.SCHEMA.OBJ")
        tfqn  = st.text_input("Tag FQN",   value=f"{db}.GOVERNANCE.DATA_SENSITIVITY" if db else "")
        tval  = st.text_input("Tag value", value="CONFIDENTIAL")
        if fqn and tfqn:
            st.code(generate_tag_assignment_sql(otype, fqn, tfqn, tval), language="sql")
