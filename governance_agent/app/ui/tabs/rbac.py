"""RBAC audit tab."""
import pandas as pd
import streamlit as st


def render(scan: dict):
    rbac = scan["rbac"]
    st.subheader("🔐 RBAC Audit")

    if rbac.get("error"):
        st.error(f"⚠️ Could not access SNOWFLAKE.ACCOUNT_USAGE: {rbac['error']}")
        st.info("Ensure your role has SELECT privilege on the SNOWFLAKE.ACCOUNT_USAGE schema.")
        return

    priv_df = rbac.get("privileged_users", pd.DataFrame())
    pub_df  = rbac.get("public_grants",    pd.DataFrame())

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Users",            rbac.get("total_users", "N/A"))
    c2.metric("Total Roles",            rbac.get("total_roles", "N/A"))
    c3.metric("Privileged Assignments", len(priv_df))

    if not priv_df.empty:
        st.warning(f"The following **{len(priv_df)}** assignments grant highly privileged roles:")
        by_role = priv_df["ROLE_NAME"].value_counts().reset_index()
        by_role.columns = ["Role", "Users"]
        col_t, col_c = st.columns([2, 1])
        with col_t:
            st.dataframe(priv_df, use_container_width=True, hide_index=True)
        with col_c:
            st.dataframe(by_role, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No highly privileged role assignments found (or ACCOUNT_USAGE is still syncing).")

    st.divider()
    if not pub_df.empty:
        st.warning(f"**{len(pub_df)}** objects are accessible via the PUBLIC role:")
        st.dataframe(pub_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No excessive PUBLIC role grants detected.")

    st.caption("⏱️ ACCOUNT_USAGE data has up to 3-hour latency.")
