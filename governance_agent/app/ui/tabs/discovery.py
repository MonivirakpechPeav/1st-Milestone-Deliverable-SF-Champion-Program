"""Horizon Catalog discovery tab — search tables/columns, browse semantic
views, peek at internal Marketplace listings."""
import streamlit as st

from ...services.discovery import (
    list_internal_listings,
    list_semantic_views,
    search_columns,
    search_objects,
)


def render(conn):
    st.subheader("🌐 Horizon Catalog Discovery")
    st.caption(
        "One-stop search across Snowflake tables, columns, semantic views, "
        "and internal Marketplace listings — replaces the need to navigate "
        "Universal Search separately."
    )

    q = st.text_input("Search term (matches name, schema, comment)",
                      value="", placeholder="customer, order, pii, ...")

    if q:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Tables / Views")
            with st.spinner("Searching..."):
                obj = search_objects(conn, q)
            st.dataframe(
                obj if not obj.empty else obj,
                use_container_width=True, hide_index=True,
            )
            if obj.empty:
                st.caption("No matching objects.")
        with c2:
            st.markdown("#### Columns")
            with st.spinner("Searching..."):
                cols = search_columns(conn, q)
            st.dataframe(cols, use_container_width=True, hide_index=True)
            if cols.empty:
                st.caption("No matching columns.")

    st.divider()
    e1, e2 = st.columns(2)
    with e1:
        with st.expander("📐 Semantic views in account", expanded=False):
            sv = list_semantic_views(conn)
            if sv.empty:
                st.caption("No semantic views found / privilege missing.")
            else:
                st.dataframe(sv, use_container_width=True, hide_index=True)
    with e2:
        with st.expander("🛍️ Internal Marketplace listings", expanded=False):
            ls = list_internal_listings(conn)
            if ls.empty:
                st.caption("No listings visible.")
            else:
                st.dataframe(ls, use_container_width=True, hide_index=True)
