"""Policy coverage tab."""
import altair as alt
import streamlit as st


def render(scan: dict):
    policy_df = scan["policy_df"]
    st.subheader("🛡️ Policy Coverage")

    if policy_df.empty:
        st.warning("⚠️ No masking, row access, or projection policies found.")
        st.info(
            "**Recommendation:** Apply Dynamic Data Masking policies to sensitive columns, "
            "especially those flagged in the PII Detection tab."
        )
        return

    by_kind = policy_df["POLICY_KIND"].value_counts().reset_index()
    by_kind.columns = ["Policy Type", "Count"]

    col_metrics, col_chart = st.columns([1, 2])
    with col_metrics:
        for _, row in by_kind.iterrows():
            st.metric(row["Policy Type"].replace("_", " ").title(), row["Count"])
    with col_chart:
        pie = (
            alt.Chart(by_kind)
            .mark_arc(innerRadius=45)
            .encode(
                theta="Count:Q",
                color=alt.Color("Policy Type:N", scale=alt.Scale(scheme="tableau10")),
                tooltip=["Policy Type", "Count"],
            )
            .properties(height=200, title="Policies by Type")
        )
        st.altair_chart(pie, use_container_width=True)

    st.subheader("All Policies")
    st.dataframe(policy_df, use_container_width=True, hide_index=True)
