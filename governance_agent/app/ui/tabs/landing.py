"""Landing page (hero) shown before any scan has run."""
import streamlit as st


def render():
    st.markdown(
        """
<div style="
    text-align:center;
    padding:3.5rem 1rem 2.5rem 1rem;
    background:linear-gradient(135deg,#11567F 0%,#29B5E8 100%);
    border-radius:18px;
    color:#ffffff;
    margin-bottom:1.5rem;">
    <div style="font-size:3.2rem;line-height:1;">🛡️</div>
    <h1 style="color:#ffffff;margin:0.6rem 0 0.4rem 0;font-size:2.4rem;">
        Data Governance Agent
    </h1>
    <p style="font-size:1.15rem;max-width:640px;margin:0 auto;opacity:0.95;">
        Enterprise-grade data governance scanning — Snowflake native, no plugins required.
    </p>
    <p style="font-size:0.95rem;margin-top:1.2rem;opacity:0.9;">
        Score your data estate, mirror the Horizon Catalog, and automate remediation
        — all in one place.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            "### 📊 Insights\nGovernance score, trend history & table inventory."
        )
    with c2:
        st.markdown(
            "### 🌐 Horizon Catalog\nDiscovery, classification, PII, policies, lineage, quality & more."
        )
    with c3:
        st.markdown(
            "### 🛠️ Governance Actions\nSetup wizard, RBAC audit & remediation SQL."
        )

    st.divider()
    st.info(
        "👈 Select a **Database** in the sidebar and click **Run Governance Scan** to begin. "
        "New here? Open **📖 Features & Guide** in the sidebar for a full walkthrough."
    )
