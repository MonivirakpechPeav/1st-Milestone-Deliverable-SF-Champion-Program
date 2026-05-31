"""Schema documentation quality tab."""
import streamlit as st


def render(scan: dict):
    doc_df = scan["doc_df"]
    st.subheader("📚 Schema Documentation Quality")

    if doc_df.empty:
        st.info("No tables found in this scope.")
        return

    total_cols  = int(doc_df["TOTAL_COLUMNS"].sum())
    doc_cols    = int(doc_df["DOCUMENTED_COLUMNS"].sum())
    overall_pct = round(doc_cols / max(total_cols, 1) * 100, 1)
    fully_doc   = int((doc_df["DOC_PCT"] == 100).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Coverage",  f"{overall_pct}%")
    c2.metric("Tables Scanned",    len(doc_df))
    c3.metric("Fully Documented",  fully_doc)
    c4.metric("Total Columns",     total_cols)

    st.dataframe(
        doc_df,
        use_container_width=True, hide_index=True,
        column_config={
            "DOC_PCT": st.column_config.ProgressColumn(
                "Coverage %", format="%.1f%%", min_value=0, max_value=100
            ),
            "TOTAL_COLUMNS":      st.column_config.NumberColumn("Total Cols", width="small"),
            "DOCUMENTED_COLUMNS": st.column_config.NumberColumn("Documented", width="small"),
        },
    )

    undoc = doc_df[doc_df["DOC_PCT"] < 50].sort_values("DOC_PCT")
    if not undoc.empty:
        st.warning(f"⚠️ **{len(undoc)}** tables have <50% column documentation:")
        st.dataframe(
            undoc[["TABLE_SCHEMA", "TABLE_NAME", "TOTAL_COLUMNS", "DOCUMENTED_COLUMNS", "DOC_PCT"]],
            use_container_width=True, hide_index=True,
        )
