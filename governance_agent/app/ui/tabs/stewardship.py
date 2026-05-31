"""Stewardship / Object Contacts tab."""
import pandas as pd
import streamlit as st

from ...services.stewardship import generate_contact_sql


def render(scan: dict):
    st.subheader("👥 Stewardship & Object Contacts")
    stew = scan.get("stewardship") or {}

    if stew.get("error"):
        st.error(f"⚠️ Could not access contact metadata: {stew['error']}")
        return

    refs = stew.get("references", pd.DataFrame())
    contacts = stew.get("contacts", pd.DataFrame())

    c1, c2, c3 = st.columns(3)
    c1.metric("Contacts Defined",   len(contacts))
    c2.metric("Object Assignments", len(refs))
    c3.metric("Stewards (STEWARD)", int((refs["CONTACT_PURPOSE"] == "STEWARD").sum()) if not refs.empty else 0)

    st.markdown("#### Existing Object Contact Assignments")
    if refs.empty:
        st.info("No object contacts found. Assign data stewards to make ownership explicit.")
    else:
        st.dataframe(refs, use_container_width=True, hide_index=True)

    st.markdown("#### Defined Contacts")
    if contacts.empty:
        st.info("No contacts defined yet (or `CONTACTS` view not accessible).")
    else:
        st.dataframe(contacts, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### 🛠 Generate Contact SQL")
    col1, col2 = st.columns(2)
    with col1:
        contact_name = st.text_input("Contact name", value="data_stewards")
        purpose      = st.selectbox(
            "Purpose",
            ["STEWARD", "ACCESS_APPROVAL", "SECURITY_COMPLIANCE", "SUPPORT"],
        )
        email = st.text_input("Email distribution list (optional)", value="")
    with col2:
        object_type  = st.selectbox("Object type", ["TABLE", "SCHEMA", "DATABASE", "VIEW"])
        object_name  = st.text_input("Fully-qualified object name", value="MY_DB.MY_SCHEMA.MY_TABLE")

    if contact_name and object_name:
        sql = generate_contact_sql(
            contact_name=contact_name,
            purpose=purpose,
            object_type=object_type,
            fully_qualified_name=object_name,
            email=email or None,
        )
        st.code(sql, language="sql")
