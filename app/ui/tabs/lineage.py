"""Lineage explorer tab."""
import pandas as pd
import streamlit as st

from ...services.lineage import get_lineage


def _build_dot(edges_df: pd.DataFrame, copy_df: pd.DataFrame, focus: str) -> str:
    """Build a Graphviz DOT string from lineage + ingestion edges."""
    lines = [
        'digraph G {',
        '  rankdir=LR;',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];',
        '  edge [fontname="Helvetica", fontsize=8, color="#666666"];',
        f'  "{focus}" [fillcolor="#FFD24A", color="#B07A00"];',
    ]
    nodes: set[str] = {focus}

    # Object lineage edges
    if not edges_df.empty:
        cols = {c.upper() for c in edges_df.columns}
        src_col = "SOURCE_OBJECT_NAME" if "SOURCE_OBJECT_NAME" in cols else None
        tgt_col = "TARGET_OBJECT_NAME" if "TARGET_OBJECT_NAME" in cols else None
        if src_col and tgt_col:
            for _, r in edges_df.iterrows():
                s = str(r.get(src_col, "")).strip()
                t = str(r.get(tgt_col, "")).strip()
                if not s or not t:
                    continue
                for n in (s, t):
                    if n not in nodes:
                        lines.append(f'  "{n}" [fillcolor="#E8F1FB", color="#3a7bd5"];')
                        nodes.add(n)
                lines.append(f'  "{s}" -> "{t}";')

    # Ingestion edges (stage -> table)
    if not copy_df.empty and {"STAGE_LOCATION", "DATABASE_NAME", "SCHEMA_NAME", "TABLE_NAME"}.issubset(copy_df.columns):
        agg = (
            copy_df.dropna(subset=["STAGE_LOCATION"])
                   .groupby(["STAGE_LOCATION", "DATABASE_NAME", "SCHEMA_NAME", "TABLE_NAME"])
                   .size().reset_index(name="LOADS")
        )
        for _, r in agg.iterrows():
            stage = str(r["STAGE_LOCATION"])
            table = f'{r["DATABASE_NAME"]}.{r["SCHEMA_NAME"]}.{r["TABLE_NAME"]}'
            stage_lbl = stage if len(stage) <= 60 else stage[:57] + "..."
            if stage not in nodes:
                lines.append(f'  "{stage}" [label="\u2601 {stage_lbl}", fillcolor="#FCE8E8", color="#c0392b"];')
                nodes.add(stage)
            if table not in nodes:
                lines.append(f'  "{table}" [fillcolor="#E8F1FB", color="#3a7bd5"];')
                nodes.add(table)
            lines.append(f'  "{stage}" -> "{table}" [label="{int(r["LOADS"])} load(s)", color="#c0392b"];')

    lines.append('}')
    return "\n".join(lines)


def render(conn, scan: dict):
    st.subheader("🔗 Lineage Explorer")
    st.caption("Trace upstream sources and downstream consumers using `SNOWFLAKE.CORE.GET_LINEAGE`.")

    inv = scan.get("inventory_df", pd.DataFrame())
    db  = scan.get("database", "")

    options: list[str] = []
    if not inv.empty:
        options = [
            f"{db}.{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}"
            for _, r in inv.iterrows()
        ]

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        if options:
            selected = st.selectbox("Object (fully-qualified)", options)
        else:
            selected = st.text_input("Object (fully-qualified)", value=f"{db}.PUBLIC.MY_TABLE")
    with c2:
        direction = st.selectbox("Direction", ["DOWNSTREAM", "UPSTREAM"])
    with c3:
        distance  = st.slider("Distance", 1, 5, 2)

    object_domain = st.selectbox("Object domain", ["TABLE", "VIEW", "MATERIALIZED_VIEW", "DYNAMIC_TABLE"])

    if st.button("🔎 Trace lineage", type="primary"):
        if not selected:
            st.warning("Please specify an object.")
            return
        with st.spinner("Querying lineage..."):
            df = get_lineage(conn, selected, object_domain, direction, distance)
        st.session_state["lineage_df"]    = df
        st.session_state["lineage_focus"] = selected

    df = st.session_state.get("lineage_df")
    focus = st.session_state.get("lineage_focus")
    if df is None:
        return
    if df.empty:
        st.info("No lineage rows returned. The object may have no recorded lineage in this direction, or you may lack ACCOUNT_USAGE access.")
        return

    st.success(f"{len(df)} lineage edge(s) found.")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Visual DAG ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🕸 Visual DAG (lineage + ingestion)")
    storage = scan.get("storage") or {}
    copy_df = (storage.get("copy") or {}).get("loads", pd.DataFrame())
    if copy_df is None:
        copy_df = pd.DataFrame()
    only_relevant = st.checkbox(
        "Filter ingestion edges to focus object only", value=True, key="dag_filter",
    )
    cdf = copy_df.copy()
    if only_relevant and focus and not cdf.empty:
        try:
            db_p, sch_p, tbl_p = focus.split(".")
            cdf = cdf[
                (cdf["DATABASE_NAME"] == db_p)
                & (cdf["SCHEMA_NAME"] == sch_p)
                & (cdf["TABLE_NAME"] == tbl_p)
            ]
        except ValueError:
            pass

    dot = _build_dot(df, cdf, focus or selected)
    st.graphviz_chart(dot, use_container_width=True)
    if cdf.empty:
        st.caption(
            "No `COPY_HISTORY` ingestion edges to render — graph shows only object lineage. "
            "Storage scan data must be present (run a scan) for stage→table edges."
        )
