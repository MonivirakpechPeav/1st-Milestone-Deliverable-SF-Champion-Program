"""History tab: persisted scan history with trend chart."""
import altair as alt
import streamlit as st

from ...services.history import load_history


def render(conn, scan: dict, history_db: str):
    st.subheader("📈 Governance Score History")
    st.caption(f"Stored in: `{history_db}.GOVERNANCE_AGENT.SCAN_HISTORY`")
    st.caption("✅ Scans are saved automatically after each scan.")

    if st.button("🔄 Refresh History", use_container_width=True):
        st.session_state.pop("history_df", None)

    if "history_df" not in st.session_state:
        st.session_state["history_df"] = load_history(conn, history_db)

    hist_df = st.session_state["history_df"]

    if hist_df.empty:
        st.info("No scan history yet. Run a scan to populate history.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Scans",  len(hist_df))
    c2.metric("Latest Score", f"{hist_df['OVERALL_SCORE'].iloc[0]}/100")
    c3.metric("Best Score",   f"{hist_df['OVERALL_SCORE'].max()}/100")

    if len(hist_df) >= 2:
        trend_df = hist_df[
            ["SCAN_TS", "OVERALL_SCORE", "PII_SCORE", "DOC_SCORE", "RBAC_SCORE", "POLICY_SCORE"]
        ].copy().sort_values("SCAN_TS")
        trend_melted = trend_df.melt(
            id_vars="SCAN_TS",
            value_vars=["OVERALL_SCORE", "PII_SCORE", "DOC_SCORE", "RBAC_SCORE", "POLICY_SCORE"],
            var_name="Metric", value_name="Score",
        )
        line = (
            alt.Chart(trend_melted)
            .mark_line(point=True)
            .encode(
                x=alt.X("SCAN_TS:T", title="Scan Time"),
                y=alt.Y("Score:Q", title="Score"),
                color=alt.Color("Metric:N", scale=alt.Scale(scheme="tableau10")),
                tooltip=["SCAN_TS:T", "Metric", "Score"],
            )
            .properties(height=280, title="Governance Score Trend")
        )
        st.altair_chart(line, use_container_width=True)
    else:
        st.info("Save at least 2 scans to see trend charts.")

    st.subheader("Scan History")
    st.dataframe(
        hist_df,
        use_container_width=True, hide_index=True,
        column_config={
            "SCAN_TS": st.column_config.DatetimeColumn("Scan Time", format="YYYY-MM-DD HH:mm"),
            "OVERALL_SCORE": st.column_config.ProgressColumn(
                "Overall Score", format="%.1f", min_value=0, max_value=100
            ),
        },
    )
