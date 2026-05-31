"""Access audit tab — recent data access patterns."""
import pandas as pd
import streamlit as st


def render(scan: dict):
    st.subheader("👁️ Access Audit")
    audit = scan.get("access_audit") or {}

    if audit.get("error"):
        st.error(f"⚠️ Could not access ACCESS_HISTORY: {audit['error']}")
        st.info("Ensure your role has SELECT privilege on SNOWFLAKE.ACCOUNT_USAGE.")
        return

    days = audit.get("days", 7)
    st.caption(f"Showing the last **{days}** days of activity from `ACCESS_HISTORY` (up to 3-hour latency).")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Queries", f"{audit.get('total_queries', 0):,}")
    c2.metric("Distinct Readers", len(audit.get("top_readers", pd.DataFrame())))
    c3.metric("Objects Touched", len(audit.get("top_objects", pd.DataFrame())))
    c4.metric("Off-Hours Queries", len(audit.get("off_hours", pd.DataFrame())))

    st.markdown("#### 👥 Top Readers")
    readers = audit.get("top_readers", pd.DataFrame())
    if readers.empty:
        st.info("No reader activity in window.")
    else:
        st.dataframe(readers, use_container_width=True, hide_index=True)

    st.markdown("#### 📦 Most-Accessed Objects")
    objs = audit.get("top_objects", pd.DataFrame())
    if objs.empty:
        st.info("No object access recorded.")
    else:
        st.dataframe(objs, use_container_width=True, hide_index=True)

    st.markdown("#### ✍️ Most-Modified Objects")
    mods = audit.get("modifications", pd.DataFrame())
    if mods.empty:
        st.info("No write activity in window.")
    else:
        st.dataframe(mods, use_container_width=True, hide_index=True)

    st.markdown("#### 🌙 Off-Hours Activity (before 6am / after 10pm)")
    off = audit.get("off_hours", pd.DataFrame())
    if off.empty:
        st.success("✅ No off-hours queries detected.")
    else:
        st.warning(f"{len(off)} off-hours queries detected — review for unusual access.")
        st.dataframe(off, use_container_width=True, hide_index=True)
