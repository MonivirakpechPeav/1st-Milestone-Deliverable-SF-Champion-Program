"""Snowflake-native Sensitive Data Classification tab.

Replaces (or augments) the regex-based PII scanner with Snowflake's
SYSTEM$CLASSIFY + DATA_CLASSIFICATION_LATEST pipeline, including
Classification Profile creation and database attachment.
"""
import altair as alt
import streamlit as st

from ...services.classification import (
    attach_profile_to_database,
    classify_table,
    create_classification_profile,
    latest_classification,
    latest_classification_summary,
)


def render(conn, scan: dict):
    st.subheader("🧬 Sensitive Data Classification (Horizon-native)")
    st.caption(
        "Powered by `SYSTEM$CLASSIFY` and `SNOWFLAKE.ACCOUNT_USAGE."
        "DATA_CLASSIFICATION_LATEST`. Complements the name-based PII scan."
    )

    db     = scan.get("database")
    schema = scan.get("schema")

    tab_latest, tab_run, tab_profile = st.tabs(
        ["📊 Latest Classification", "▶️ Run on a Table", "⚙️ Profile / Auto-Tag"]
    )

    with tab_latest:
        with st.spinner("Loading latest classification..."):
            summary = latest_classification_summary(conn, db, schema)
            rows    = latest_classification(conn, db, schema)
        if summary.empty:
            st.info("No classification data yet for this scope. Run classification "
                    "on a table or attach a Classification Profile.")
        else:
            chart = (
                alt.Chart(summary)
                .mark_bar()
                .encode(
                    x="COLUMN_COUNT:Q",
                    y=alt.Y("PRIVACY_CATEGORY:N", sort="-x"),
                    color="SEMANTIC_CATEGORY:N",
                    tooltip=list(summary.columns),
                )
                .properties(height=260, title="Columns by Privacy/Semantic Category")
            )
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(rows, use_container_width=True, hide_index=True)

    with tab_run:
        st.write("Run `SYSTEM$CLASSIFY` against a single table:")
        inv = scan.get("inventory_df")
        if inv is None or inv.empty:
            st.info("Run a governance scan first.")
        else:
            opts = [f"{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}" for _, r in inv.iterrows()]
            sel  = st.selectbox("Table", opts)
            if st.button("▶️ Classify table", type="primary"):
                sch, tbl = sel.split(".", 1)
                with st.spinner("Classifying (consumes warehouse credits)..."):
                    res = classify_table(conn, db, sch, tbl)
                if res.empty:
                    st.warning("No classification results returned.")
                else:
                    st.dataframe(res, use_container_width=True, hide_index=True)

    with tab_profile:
        st.write("Create a Classification Profile and attach it to a database "
                 "to enable Horizon's automatic sensitive data classification.")
        c1, c2, c3 = st.columns(3)
        with c1:
            pdb = st.text_input("Profile DB", value=db or "")
        with c2:
            psc = st.text_input("Profile schema", value="GOVERNANCE")
        with c3:
            pnm = st.text_input("Profile name", value="GOV_AGENT_PROFILE")

        auto_tag = st.checkbox("Enable auto_tag", value=True)
        min_age  = st.number_input("Minimum object age (days)", min_value=0, value=0)

        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("Create / replace profile"):
                ok, err = create_classification_profile(
                    conn, pdb, psc, pnm, auto_tag=auto_tag,
                    minimum_object_age_for_classification_days=int(min_age),
                )
                st.success("Profile created.") if ok else st.error(err or "Failed.")
        with cc2:
            target_db = st.text_input("Attach to database", value=db or "")
            if st.button("Attach profile to DB"):
                ok, err = attach_profile_to_database(
                    conn, f"{pdb}.{psc}.{pnm}", target_db,
                )
                st.success("Profile attached.") if ok else st.error(err or "Failed.")
