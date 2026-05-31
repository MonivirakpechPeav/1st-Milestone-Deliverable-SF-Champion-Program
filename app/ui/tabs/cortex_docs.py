"""Cortex-powered object descriptions tab.

Fill in missing comments by asking Cortex AI_COMPLETE to draft descriptions
based on column name + type + parent table.
"""
import streamlit as st

from ...services.cortex_docs import generate_comment_sql, suggest_column_descriptions


def render(conn, scan: dict):
    st.subheader("📝 Cortex Powered Object Descriptions")
    st.caption(
        "Use Cortex AI_COMPLETE to draft column descriptions for tables that "
        "lack documentation. Review the suggestions, then apply with one SQL block."
    )

    inv = scan.get("inventory_df")
    db  = scan.get("database", "")
    if inv is None or inv.empty:
        st.info("Run a scan first to populate the table picker.")
        return

    options = [
        f"{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}"
        for _, r in inv.iterrows()
    ]
    sel = st.selectbox("Pick a table", options)
    if not sel:
        return
    schema, table = sel.split(".", 1)

    if st.button("✨ Suggest descriptions with Cortex", type="primary"):
        with st.spinner("Calling Cortex..."):
            df = suggest_column_descriptions(conn, db, schema, table)
        st.session_state["cortex_doc_df"] = df
        st.session_state["cortex_doc_target"] = (db, schema, table)

    df = st.session_state.get("cortex_doc_df")
    target = st.session_state.get("cortex_doc_target")
    if df is None or df.empty or not target:
        return

    st.markdown("#### Review & edit the suggested descriptions")
    edited = st.data_editor(
        df, use_container_width=True, hide_index=True,
        disabled=["COLUMN_NAME", "DATA_TYPE", "COMMENT"],
        key="cortex_doc_editor",
    )

    table_desc = st.text_input("Optional table description", value="")
    desc_map = dict(zip(edited["COLUMN_NAME"], edited["SUGGESTED_DESCRIPTION"]))
    sql = generate_comment_sql(target[0], target[1], target[2], desc_map, table_desc or None)
    st.markdown("#### Ready-to-apply SQL")
    st.code(sql or "-- nothing to apply", language="sql")
