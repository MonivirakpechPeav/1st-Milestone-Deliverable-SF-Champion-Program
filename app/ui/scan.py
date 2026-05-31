"""Governance scan orchestration."""
import pandas as pd
import streamlit as st

from ..services.access_audit import get_access_audit
from ..services.history import ensure_history_store, save_scan
from ..services.inventory import get_schema_doc_coverage, get_table_inventory
from ..services.lineage import get_lineage  # noqa: F401  (used by tab)
from ..services.pii import detect_pii_columns
from ..services.policies import get_policy_coverage
from ..services.quality import get_dmf_coverage
from ..services.rbac import get_rbac_summary
from ..services.scoring import compute_governance_score
from ..services.stewardship import get_object_contacts


def run(conn, database: str, schema: str | None, history_db: str | None = None) -> None:
    """Execute a full scan and stash results in session state."""
    progress = st.progress(0, text="Starting scan...")
    with st.spinner("Running governance scan..."):
        progress.progress(10, text="Detecting PII columns...")
        pii_df = detect_pii_columns(conn, database, schema)

        progress.progress(30, text="Loading table inventory...")
        inventory_df = get_table_inventory(conn, database, schema)

        progress.progress(50, text="Measuring schema documentation...")
        doc_df = get_schema_doc_coverage(conn, database, schema)

        progress.progress(65, text="Checking policy coverage...")
        policy_df = get_policy_coverage(conn, database, schema)

        progress.progress(75, text="Auditing RBAC...")
        rbac = get_rbac_summary(conn)

        progress.progress(82, text="Auditing data access...")
        access_audit = get_access_audit(conn, days=7)

        progress.progress(88, text="Loading object contacts / stewards...")
        stewardship = get_object_contacts(conn, database)

        progress.progress(92, text="Checking DMF coverage...")
        quality = get_dmf_coverage(conn, database, schema)

        progress.progress(95, text="Computing governance score...")
        base_tables = (
            inventory_df[inventory_df["TABLE_TYPE"] == "BASE TABLE"]
            if not inventory_df.empty else pd.DataFrame()
        )
        score = compute_governance_score(
            pii_df, policy_df, doc_df, rbac, len(base_tables)
        )
        progress.progress(100, text="Done!")

        st.session_state["scan_results"] = {
            "pii_df":       pii_df,
            "inventory_df": inventory_df,
            "doc_df":       doc_df,
            "policy_df":    policy_df,
            "rbac":         rbac,
            "access_audit": access_audit,
            "stewardship":  stewardship,
            "quality":      quality,
            "score":        score,
            "database":     database,
            "schema":       schema,
        }
        st.session_state.pop("remediations", None)

        if history_db:
            progress.progress(100, text="Saving scan to history...")
            ok, _ = ensure_history_store(conn, history_db)
            if ok:
                ok2, _ = save_scan(conn, st.session_state["scan_results"], history_db)
                if ok2:
                    st.session_state.pop("history_df", None)
    st.rerun()
