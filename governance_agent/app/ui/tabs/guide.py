"""Features & Guide menu — full walkthrough of every capability."""
import streamlit as st


def render():
    st.markdown("# 📖 Features & Guide")
    st.caption("Everything the Data Governance Agent can do, grouped by section.")
    st.divider()

    left, right = st.columns([2, 1])
    with left:
        st.markdown("""
**📊 Insights** _(project-unique)_

| Feature | What it does |
|---|---|
| 📊 Overview & Score | Governance score (0–100) + letter grade across 4 pillars |
| 📈 History | Trend of every scan over time |
| 🧱 Inventory & Docs | Table inventory + documentation coverage |

**🌐 Horizon Catalog** _(read-only mirrors)_

| Feature | What it does |
|---|---|
| 🔎 Discovery | Universal search across tables, views & semantic views |
| 🧬 Classification | Auto + manual sensitive-data classification |
| 🔍 PII (regex) | Name-based PII detection using 12 category patterns |
| 🛡️ Policies | Masking, row-access & projection policy coverage |
| 🏷️ Tags | Tags & tag-based masking references |
| 🔗 Lineage | Upstream / downstream object lineage |
| 👁️ Access History | Who read & modified data (ACCESS_HISTORY) |
| 📏 Data Quality | DMF coverage & metric attachment |
| 👥 Stewards | Object contacts & stewardship |
| 🔒 Trust Center | Security scanners & findings |
| 📝 Cortex Docs | AI-generated object descriptions |

**🛠️ Governance Actions** _(write / automation)_

| Feature | What it does |
|---|---|
| 🧰 Setup Wizard | One form per Horizon primitive |
| 🔐 RBAC Audit | Privileged role assignments & PUBLIC grants |
| 🔧 Remediation | Auto-generated, copy-pasteable fix SQL |
        """)
    with right:
        st.markdown("""
**How to use**

1. Select a **Database** in the sidebar
2. Optionally narrow to a **Schema**
3. Click **Run Governance Scan**
4. Review results across the **📊 Insights**, **🌐 Horizon Catalog**, and **🛠️ Governance Actions** sections

---
**Governance Score Components**
- PII Masking Coverage — 25 pts
- Schema Documentation — 25 pts
- RBAC Hygiene — 25 pts
- Policy Coverage — 25 pts
        """)
