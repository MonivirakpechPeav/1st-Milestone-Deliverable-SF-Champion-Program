"""Overview tab: scorecard + key metrics + bar chart."""
import altair as alt
import pandas as pd
import streamlit as st


def render(scan: dict):
    score        = scan["score"]
    pii_df       = scan["pii_df"]
    inventory_df = scan["inventory_df"]
    policy_df    = scan["policy_df"]
    comp         = score["components"]
    color        = score["color"]

    col_grade, col_breakdown = st.columns([1, 3])
    with col_grade:
        st.markdown(f"""
<div style="text-align:center;padding:28px 20px;background:#f8f9fa;border-radius:12px;
            border-left:6px solid {color}">
  <div style="font-size:5rem;font-weight:700;color:{color};line-height:1">{score["grade"]}</div>
  <div style="font-size:2.2rem;color:{color};font-weight:600">{score["total"]}<span style="font-size:1rem;color:#888">/100</span></div>
  <div style="color:#888;font-size:0.82rem;margin-top:8px">Overall Governance Score</div>
</div>
        """, unsafe_allow_html=True)

    with col_breakdown:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔍 PII Masking",      f"{comp['pii']['score']}/25",    comp["pii"]["note"],    delta_color="off")
        c2.metric("📚 Documentation",    f"{comp['docs']['score']}/25",   comp["docs"]["note"],   delta_color="off")
        c3.metric("🔐 RBAC Hygiene",     f"{comp['rbac']['score']}/25",   comp["rbac"]["note"],   delta_color="off")
        c4.metric("🛡️ Policy Coverage", f"{comp['policy']['score']}/25", comp["policy"]["note"], delta_color="off")

    st.divider()

    if not inventory_df.empty:
        base  = inventory_df[inventory_df["TABLE_TYPE"] == "BASE TABLE"]
        views = inventory_df[inventory_df["TABLE_TYPE"] == "VIEW"]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Tables", len(base))
        c2.metric("Views",  len(views))
        c3.metric("PII Columns", len(pii_df))
        c4.metric("Policies Applied", len(policy_df))
        c5.metric("Schemas", inventory_df["TABLE_SCHEMA"].nunique())

    chart_df = pd.DataFrame([
        {"Component": "PII Masking",     "Score": comp["pii"]["score"]},
        {"Component": "Documentation",   "Score": comp["docs"]["score"]},
        {"Component": "RBAC Hygiene",    "Score": comp["rbac"]["score"]},
        {"Component": "Policy Coverage", "Score": comp["policy"]["score"]},
    ])
    chart = (
        alt.Chart(chart_df)
        .transform_calculate(
            Status="datum.Score >= 20 ? 'good' : datum.Score >= 12 ? 'ok' : 'bad'"
        )
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            y=alt.Y("Component:N", sort=None, title=None),
            x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 25]), title="Score (max 25)"),
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(
                    domain=["good", "ok", "bad"],
                    range=["#2ecc71", "#f39c12", "#e74c3c"],
                ),
                legend=None,
            ),
            tooltip=["Component", "Score"],
        )
        .properties(height=150, title="Score by Component")
    )
    st.altair_chart(chart, use_container_width=True)
