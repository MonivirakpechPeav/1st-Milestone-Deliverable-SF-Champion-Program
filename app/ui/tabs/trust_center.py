"""Trust Center findings tab."""
import altair as alt
import streamlit as st

from ...services.trust_center import get_findings, list_scanners, severity_summary


def render(conn):
    st.subheader("🔒 Trust Center")
    st.caption(
        "Snowflake-native security scanners (CIS, Threat Intelligence, custom). "
        "Reads from `SNOWFLAKE.TRUST_CENTER.FINDINGS`."
    )

    with st.spinner("Loading findings..."):
        findings = get_findings(conn)
        scanners = list_scanners(conn)

    if findings.empty:
        st.info(
            "No findings returned. Either there are zero findings, or your role "
            "lacks the SNOWFLAKE.TRUST_CENTER_ADMIN/VIEWER database role."
        )
    else:
        sev = severity_summary(findings)
        c1, c2 = st.columns([1, 2])
        with c1:
            for _, r in sev.iterrows():
                st.metric(r["SEVERITY"], int(r["COUNT"]))
        with c2:
            chart = (
                alt.Chart(sev)
                .mark_bar()
                .encode(
                    x="COUNT:Q",
                    y=alt.Y("SEVERITY:N", sort="-x"),
                    color=alt.Color("SEVERITY:N",
                                    scale=alt.Scale(scheme="reds")),
                    tooltip=["SEVERITY", "COUNT"],
                )
                .properties(height=180, title="Findings by Severity")
            )
            st.altair_chart(chart, use_container_width=True)

        st.subheader("All Findings")
        st.dataframe(findings, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📡 Scanners")
    if scanners.empty:
        st.caption("No scanner inventory available.")
    else:
        st.dataframe(scanners, use_container_width=True, hide_index=True)
