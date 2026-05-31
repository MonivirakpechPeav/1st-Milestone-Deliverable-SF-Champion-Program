"""Remediation tab: auto-generated SQL fixes with execution."""
import streamlit as st

from ...services.remediation import generate_all_remediations


_BADGE = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}


def _strip_leading_comments(stmt: str) -> str:
    lines = []
    started = False
    for line in stmt.splitlines():
        if not started and (not line.strip() or line.strip().startswith("--")):
            continue
        started = True
        lines.append(line)
    return "\n".join(lines).strip()


def _execute_fix(conn, sql: str) -> tuple[bool, str | None]:
    statements = []
    for raw in sql.split(";"):
        cleaned = _strip_leading_comments(raw)
        if cleaned:
            statements.append(cleaned)
    if not statements:
        return False, "No executable SQL statements found in remediation."
    for stmt in statements:
        try:
            conn.session().sql(stmt).collect()
        except Exception as e:
            return False, str(e)
    return True, None


def render(conn, scan: dict):
    st.subheader("🔧 Remediation Suggestions")
    st.caption("Auto-generated SQL fixes for every governance finding")

    if "remediations" not in st.session_state:
        st.session_state["remediations"] = generate_all_remediations(
            scan["pii_df"], scan["policy_df"], scan["doc_df"],
            scan["rbac"], scan["database"],
        )

    items = st.session_state["remediations"]

    if not items:
        st.success("✅ No remediation actions needed — governance looks clean!")
        return

    high   = [i for i in items if i["priority"] == "HIGH"]
    medium = [i for i in items if i["priority"] == "MEDIUM"]
    low    = [i for i in items if i["priority"] == "LOW"]

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 HIGH",   len(high))
    c2.metric("🟡 MEDIUM", len(medium))
    c3.metric("🟢 LOW",    len(low))

    st.divider()

    for idx, item in enumerate(items):
        badge = _BADGE.get(item["priority"], "⚪")
        label = f"{badge} **{item['type']}** — `{item['target']}`"
        if item.get("pii_category"):
            label += f" *(PII: {item['pii_category']})*"

        with st.expander(label, expanded=(idx < 3)):
            st.code(item["sql"], language="sql")
            col_exec, col_info = st.columns([1, 3])
            with col_exec:
                if st.button(
                    "▶ Execute Fix", key=f"exec_{idx}",
                    type="primary" if item["priority"] == "HIGH" else "secondary",
                ):
                    st.session_state[f"confirm_{idx}"] = True
            with col_info:
                st.caption(f"Priority: **{item['priority']}** | Type: {item['type']}")

            if st.session_state.get(f"confirm_{idx}"):
                st.warning("⚠️ This will execute DDL on your Snowflake account. Confirm?")
                yes, no = st.columns(2)
                if yes.button("✅ Yes, execute", key=f"yes_{idx}"):
                    ok, err = _execute_fix(conn, item["sql"])
                    st.session_state.pop(f"confirm_{idx}", None)
                    if ok:
                        st.session_state["remediations"] = [
                            it for j, it in enumerate(items) if j != idx
                        ]
                        st.success("✅ Fix applied successfully! Re-run scan to refresh findings.")
                        st.rerun()
                    else:
                        st.error(f"Error: {err}")
                if no.button("❌ Cancel", key=f"no_{idx}"):
                    st.session_state.pop(f"confirm_{idx}", None)
                    st.rerun()
