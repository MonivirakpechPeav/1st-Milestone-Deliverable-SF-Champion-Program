"""PII detection tab."""
import altair as alt
import streamlit as st


def render(scan: dict):
    pii_df    = scan["pii_df"]
    policy_df = scan["policy_df"]

    st.subheader(f"🔍 PII Detection — {len(pii_df)} columns found")

    if pii_df.empty:
        st.success("✅ No PII-pattern columns detected in the selected scope.")
        return

    pii_display = pii_df.copy()
    if not policy_df.empty and "COLUMN_NAME" in policy_df.columns:
        masked_set = set(policy_df["COLUMN_NAME"].dropna().str.upper())
        pii_display["MASKED"] = pii_display["COLUMN_NAME"].str.upper().isin(masked_set)
        unmasked_count = int((~pii_display["MASKED"]).sum())
    else:
        pii_display["MASKED"] = False
        unmasked_count = len(pii_display)

    c1, c2, c3 = st.columns(3)
    c1.metric("PII Columns Found", len(pii_df))
    c2.metric("Tables Affected", pii_df["TABLE_NAME"].nunique())
    c3.metric(
        "Unmasked PII Columns", unmasked_count,
        delta=f"-{unmasked_count} need masking" if unmasked_count else None,
        delta_color="inverse",
    )

    cat_counts = pii_df["PII_CATEGORY"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    bar = (
        alt.Chart(cat_counts)
        .mark_bar(color="#e74c3c", cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X("Count:Q", title="Columns"),
            y=alt.Y("Category:N", sort="-x", title=None),
            tooltip=["Category", "Count"],
        )
        .properties(height=min(40 * len(cat_counts) + 60, 320), title="PII Columns by Category")
    )
    st.altair_chart(bar, use_container_width=True)

    if unmasked_count > 0:
        with st.expander(
            f"🚨 {unmasked_count} unmasked PII columns — click to review", expanded=True
        ):
            st.dataframe(
                pii_display[~pii_display["MASKED"]][
                    ["TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "DATA_TYPE", "PII_CATEGORY"]
                ],
                use_container_width=True, hide_index=True,
            )

    st.subheader("All PII Columns")
    st.dataframe(
        pii_display[["TABLE_SCHEMA", "TABLE_NAME", "COLUMN_NAME", "DATA_TYPE", "PII_CATEGORY", "MASKED"]],
        use_container_width=True, hide_index=True,
        column_config={
            "MASKED":       st.column_config.CheckboxColumn("Masked?", width="small"),
            "PII_CATEGORY": st.column_config.TextColumn("PII Category", width="medium"),
        },
    )
