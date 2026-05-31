"""Data Quality / DMF coverage tab."""
import pandas as pd
import streamlit as st

from ...services.quality import BUILTIN_DMFS, generate_dmf_attach_sql


def render(scan: dict):
    st.subheader("📏 Data Quality (DMFs)")
    st.caption("Coverage of Snowflake **Data Metric Functions** on tables in scope.")

    quality = scan.get("quality") or {}
    if quality.get("error"):
        st.error(f"⚠️ Could not access DMF references: {quality['error']}")
        st.info("Ensure your role has SELECT on `SNOWFLAKE.ACCOUNT_USAGE.DATA_METRIC_FUNCTION_REFERENCES`.")
        return

    dmfs = quality.get("dmfs", pd.DataFrame())
    inv  = scan.get("inventory_df", pd.DataFrame())
    base_tables = (
        inv[inv["TABLE_TYPE"] == "BASE TABLE"] if not inv.empty else pd.DataFrame()
    )
    total_tables = len(base_tables)
    covered      = quality.get("tables_with_dmf", 0)
    pct          = (covered / total_tables * 100) if total_tables else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Tables in scope",   total_tables)
    c2.metric("Tables with DMFs",  covered)
    c3.metric("Coverage",          f"{pct:.1f}%")

    st.markdown("#### Active DMFs")
    if dmfs.empty:
        st.info("No DMFs are currently attached to tables in this scope.")
    else:
        st.dataframe(dmfs, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### 🛠 Generate DMF attachment SQL")
    db = scan.get("database", "")
    options: list[str] = []
    if not base_tables.empty:
        options = [
            f"{db}.{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}"
            for _, r in base_tables.iterrows()
        ]

    col1, col2 = st.columns(2)
    with col1:
        if options:
            target = st.selectbox("Target table", options)
        else:
            target = st.text_input("Target table (FQN)", value=f"{db}.PUBLIC.MY_TABLE")
        metric_label = st.selectbox("Metric", list(BUILTIN_DMFS.keys()))
    with col2:
        column   = st.text_input("Column (leave blank for table-level)", value="")
        schedule = st.text_input("Schedule", value="USING CRON 0 * * * * UTC")

    if target and metric_label:
        sql = generate_dmf_attach_sql(
            fully_qualified_table=target,
            metric_fqn=BUILTIN_DMFS[metric_label],
            column=column or None,
            schedule=schedule,
        )
        st.code(sql, language="sql")
