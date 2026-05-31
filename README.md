# Data Governance Agent — Project Architecture

## 1. Overview

The Data Governance Agent is a Streamlit-in-Snowflake application that mirrors the complete **Snowflake Horizon Catalog** feature surface in a single UI, then adds two project-unique capabilities on top: a multi-pillar governance score and scan history trend tracking.

- **Runtime:** Streamlit-in-Snowflake (SPCS, `SYSTEM_COMPUTE_POOL_CPU`)
- **Entry point:** `main.py`
- **Identifier:** <catalog_object db="USER$PHANSIVANG" schema="PUBLIC" name="GOVERNANCE_AGENT" type="streamlit" />
- **Query warehouse:** `COMPUTE_WH`
- **Python:** >= 3.11, `streamlit[snowflake] >= 1.54.0`

### Local Run

Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`, then start the app with:

```bash
streamlit run main.py
```

The Snowflake `account` value must be the account identifier from your Snowflake URL. For example, use `orgname-accountname` for `https://orgname-accountname.snowflakecomputing.com`, or include the region/cloud for locator-style URLs such as `ve82242.ap-southeast-1.aws`.

---

## 2. High-Level Component Diagram

```
                ┌──────────────────────────────────────────┐
                │               main.py                    │
                │  page config · section router · tab wiring│
                └───────────────────┬──────────────────────┘
                                    │
          ┌─────────────────────────┼──────────────────────────┐
          ▼                         ▼                          ▼
     app/ui/                  app/services/
  (presentation)            (Snowflake logic)
                                    │
                                    ▼
               ┌────────────────────────────────────────┐
               │           Snowflake account            │
               │  INFORMATION_SCHEMA · ACCOUNT_USAGE    │
               │  SNOWFLAKE.CORE · SNOWFLAKE.TRUST_CENTER│
               │  CORTEX.COMPLETE                       │
               └────────────────────────────────────────┘
```

---

## 3. Directory Layout

```
governance_agent/
├── main.py                      # Entry point: section router + tab wiring
├── snowflake.yml                # Streamlit-in-Snowflake deployment manifest
├── pyproject.toml               # Python dependencies
├── .streamlit/config.toml       # UI theme (Snowflake-blue palette)
├── docs/
│   └── FEATURES.md              # Full Horizon feature mapping + per-feature docs
├── sql/
│   └── column_level_security.sql # Reference DDL for column-level security setup
├── tests/                       # pytest test suite (one file per service)
│   ├── conftest.py
│   └── test_*.py                # 20+ test modules covering every service
└── app/
    ├── config.py                # Constants: PII regexes, grade bands, role lists
    ├── services/                # All Snowflake-facing business logic
    │   ├── _common.py           # SQL helpers, safe_id, exec_sql, normalize_columns
    │   ├── catalog.py           # Database/schema/table enumeration (SHOW commands)
    │   ├── inventory.py         # Table list + documentation coverage
    │   ├── pii.py               # Regex-based PII column detection
    │   ├── policies.py          # Masking / row-access / projection policy refs
    │   ├── rbac.py              # Privileged users + PUBLIC grants audit
    │   ├── scoring.py           # 4-pillar score + letter grade
    │   ├── history.py           # SCAN_HISTORY table read/write
    │   ├── remediation.py       # Auto-generated DDL fixes for findings
    │   ├── classification.py    # Horizon Classification Profile + DATA_CLASSIFICATION_LATEST
    │   ├── classify.py          # SYSTEM$CLASSIFY single-table wrapper
    │   ├── discovery.py         # Universal Search over ACCOUNT_USAGE.TABLES/COLUMNS
    │   ├── tags.py              # Tag inventory + TAG_REFERENCES + DDL generators
    │   ├── lineage.py           # SNOWFLAKE.CORE.GET_LINEAGE (table + column level)
    │   ├── access_audit.py      # ACCESS_HISTORY: top readers, objects, off-hours queries
    │   ├── quality.py           # Data Metric Functions (DMF) coverage + attach SQL
    │   ├── stewardship.py       # Object contacts/stewards (CONTACT_REFERENCES)
    │   ├── trust_center.py      # TRUST_CENTER.FINDINGS + SCANNERS reader
    │   └── cortex_docs.py       # AI-generated column/table descriptions via CORTEX.COMPLETE
    └── ui/
        ├── sidebar.py           # DB/schema picker, scan trigger, history-DB selector
        ├── landing.py           # Pre-scan landing page
        ├── scan.py              # Scan orchestration (calls all services in sequence)
        ├── styles.py            # Injected CSS
        └── tabs/                # One module per report tab
            ├── overview.py      # Score dashboard + pillar breakdown
            ├── history.py       # Scan trend chart
            ├── docs.py          # Documentation coverage table
            ├── discovery.py     # Universal Search UI
            ├── classification.py # Classification profile management + summary
            ├── pii.py           # Regex PII findings table
            ├── policy.py        # Policy coverage grid
            ├── tags.py          # Tag inventory + assignment SQL
            ├── lineage.py       # Lineage explorer (upstream/downstream)
            ├── access_audit.py  # Access history panels
            ├── quality.py       # DMF coverage + attach SQL generator
            ├── stewardship.py   # Steward contacts + SQL generator
            ├── trust_center.py  # Trust Center findings + scanner list
            ├── cortex_docs.py   # AI description suggester + COMMENT ON generator
            ├── rbac.py          # RBAC audit (privileged users, PUBLIC grants)
            ├── remediation.py   # Prioritized remediation SQL viewer
            ├── setup_wizard.py  # Horizon one-click setup wizard
            └── guide.py         # In-app feature guide (pre-scan)
```

---

## 4. Layered Architecture

The codebase follows a strict three-layer separation:

| Layer            | Location              | Responsibility                                             |
|------------------|-----------------------|------------------------------------------------------------|
| Presentation     | `app/ui/`             | Streamlit widgets, layout, session state                   |
| Domain / Service | `app/services/`       | All Snowflake SQL, scoring, persistence                    |
| Configuration    | `app/config.py`       | Constants (PII categories, grade bands, role lists, names) |

`main.py` performs no business logic — it constructs page chrome, groups tabs into three named sections, and dispatches to tab modules.

---

## 5. UI Section Layout

After a scan completes, the report is organized into three sections selectable via a top-level radio:

| Section | Contents |
|---|---|
| **📊 Insights** | Overview & Score, History trend, Inventory & Docs |
| **🌐 Horizon Catalog** | Discovery, Classification, PII (regex), Policies, Tags, Lineage, Access History, Data Quality, Stewards, Trust Center, Cortex Docs |
| **🛠️ Governance Actions** | Setup Wizard, RBAC Audit, Remediation |

Before any scan is run, the sidebar shows a pre-scan menu offering a Home landing page and a **Features & Guide** page (`tabs/guide.py`).

---

## 6. Scan Pipeline

A scan triggered from the sidebar executes the following steps in `app/ui/scan.py`:

1. **Inventory** (`services/inventory.py`) — `INFORMATION_SCHEMA.TABLES` / `COLUMNS` for table list and documentation coverage ratio.
2. **PII Detection** (`services/pii.py`) — regex match of column names against `PII_CATEGORIES` from `config.py` (12 categories, name-based, zero data-read cost).
3. **Policy Coverage** (`services/policies.py`) — `INFORMATION_SCHEMA.POLICY_REFERENCES` for masking, row-access, and projection policy assignments.
4. **RBAC Audit** (`services/rbac.py`) — `SNOWFLAKE.ACCOUNT_USAGE.GRANTS_TO_USERS` / `GRANTS_TO_ROLES` for privileged users and `PUBLIC` grants.
5. **Scoring** (`services/scoring.py`) — four 25-point pillars (see §7).
6. **Persistence** (`services/history.py`) — appends one row to `<history_db>.GOVERNANCE_AGENT.SCAN_HISTORY`.
7. **Render** — the full result dict is stored in `st.session_state["scan_results"]` and consumed by every tab.

---

## 7. Governance Scoring Model

`scoring.py` computes a **0–100 score** across four 25-point pillars and a letter grade via `GRADE_BANDS`.

| Pillar | Max | Formula |
|---|---|---|
| PII Masking | 25 | `25 × masked_pii_cols / total_pii_cols` |
| Documentation | 25 | `25 × documented_cols / total_cols` |
| RBAC Hygiene | 25 | `25 − deductions` (excess ACCOUNTADMIN users, PUBLIC grants) |
| Policy Coverage | 25 | `25 × tables_with_any_policy / total_tables` |

**Grade bands** (configurable in `config.py`):

| Score | Grade | Color |
|---|---|---|
| ≥ 90 | A | Green |
| ≥ 75 | B | Blue |
| ≥ 60 | C | Orange |
| ≥ 40 | D | Dark orange |
| < 40 | F | Red |

Each pillar also returns a one-line `note` (e.g., `"3/14 PII columns masked"`) used in the overview UI, email alert body, and HTML export.

---

## 8. Horizon Catalog Feature Mapping

The **Horizon Catalog** section mirrors every Snowflake Horizon primitive in a single read-only UI:

| Horizon feature | Snowflake source | Service | Tab |
|---|---|---|---|
| Universal Search / catalog browse | `ACCOUNT_USAGE.TABLES`, `COLUMNS`, `SHOW LISTINGS`, `SHOW SEMANTIC VIEWS` | `discovery.py` | Discovery |
| Sensitive Data Classification (auto + manual) | `SYSTEM$CLASSIFY`, `DATA_CLASSIFICATION_LATEST`, `CLASSIFICATION_PROFILE` | `classification.py`, `classify.py` | Classification |
| Name-based PII heuristic (regex fallback) | `INFORMATION_SCHEMA.COLUMNS` | `pii.py` | PII (regex) |
| Tags & tag-based masking | `ACCOUNT_USAGE.TAGS`, `TAG_REFERENCES` | `tags.py` | Tags |
| Policies (masking / row-access / projection) | `INFORMATION_SCHEMA.POLICY_REFERENCES` | `policies.py` | Policies |
| Object Lineage (table / view / DT / MV / column / proc / task) | `SNOWFLAKE.CORE.GET_LINEAGE` | `lineage.py` | Lineage |
| Access History | `ACCOUNT_USAGE.ACCESS_HISTORY` | `access_audit.py` | Access History |
| Data Quality / DMFs | `ACCOUNT_USAGE.DATA_METRIC_FUNCTION_REFERENCES` | `quality.py` | Data Quality |
| Object Contacts / Stewards | `ACCOUNT_USAGE.CONTACTS`, `CONTACT_REFERENCES` | `stewardship.py` | Stewards |
| Trust Center findings & scanners | `SNOWFLAKE.TRUST_CENTER.FINDINGS`, `SCANNERS` | `trust_center.py` | Trust Center |
| Cortex-powered object descriptions | `SNOWFLAKE.CORTEX.COMPLETE` (`claude-3-5-sonnet`) | `cortex_docs.py` | Cortex Docs |

---

## 9. Project-Unique Features

These live in the **Insights** and **Governance Actions** sections and have no direct Horizon equivalent:

| Feature | Service | Tab |
|---|---|---|
| Governance Score & Letter Grade | `scoring.py` | Overview & Score |
| Scan History trend chart | `history.py` | History |
| Auto-generated remediation SQL | `remediation.py` | Remediation |
| Horizon one-click Setup Wizard | `setup_wizard.py` (UI only) | Setup Wizard |

---

## 10. Persistence Model

A dedicated history database (chosen in the sidebar) holds:

- **Schema:** `GOVERNANCE_AGENT`
- **Table:** `SCAN_HISTORY` — one row per scan; columns include `SCAN_ID` (UUID), `DATABASE_NAME`, `SCHEMA_NAME`, `SCAN_TS`, `OVERALL_SCORE`, `GRADE`, the four pillar sub-scores, and raw counts (`PII_COLUMNS_COUNT`, `TOTAL_TABLES`, `POLICIES_COUNT`, `PRIVILEGED_USERS_COUNT`).

---

## 11. Setup Wizard

`app/ui/tabs/setup_wizard.py` provides a five-step guided form for Horizon Catalog configuration that replaces navigating multiple Snowsight pages:

| Step | Action |
|---|---|
| 1 | Create + attach a **Classification Profile** (enables auto-tagging) |
| 2 | Create a **sensitivity tag** (`DATA_SENSITIVITY`) with allowed values |
| 3 | Create a **tag-based masking policy** and bind it to the tag |
| 4 | Generate `CREATE CONTACT` + `ALTER … SET CONTACT` SQL for a **data steward** |
| 5 | Enable a **Trust Center scanner package** (CIS Benchmark, Security Essentials, Threat Intelligence) |

Each step previews the generated SQL before executing it, and execution errors surface inline without stopping the form.

---

## 12. Integrations

| Integration | Used for |
|---|---|
| `INFORMATION_SCHEMA` | Inventory, columns, policy references |
| `SNOWFLAKE.ACCOUNT_USAGE` | RBAC, access history, tags, lineage, DMF, classification results |
| `SNOWFLAKE.CORE.GET_LINEAGE` | Table and column-level lineage |
| `SNOWFLAKE.TRUST_CENTER` | Security findings and scanner inventory |
| `SNOWFLAKE.CORTEX.COMPLETE` | AI-generated column/table descriptions |
| `SYSTEM$CLASSIFY` | On-demand single-table sensitive data classification |

---

## 13. Configuration Surface

All tunable values live in `app/config.py`:

| Constant | Purpose |
|---|---|
| `PII_CATEGORIES` | 12 regex patterns for name-based PII detection |
| `PRIVILEGED_ROLES` | Roles treated as high-risk (`ACCOUNTADMIN`, `SECURITYADMIN`, `SYSADMIN`, `ORGADMIN`) |
| `HISTORY_SCHEMA` | Schema name for scan history persistence (`GOVERNANCE_AGENT`) |
| `HISTORY_TABLE` | Table name (`SCAN_HISTORY`) |
| `GRADE_BANDS` | Score thresholds → letter grade + hex color |

---

## 14. Security & Permissions

The application runs `execute_as: OWNER`. The owner role must have:

- `USAGE` on every database the user may scan.
- `SELECT` on `SNOWFLAKE.ACCOUNT_USAGE` views for RBAC, access history, tags, lineage, DMF, and classification. Features that cannot access these views degrade gracefully (neutral pillar score or empty tables).
- `USAGE` on `COMPUTE_WH`.
- `CREATE SCHEMA / TABLE` in the chosen history database for history persistence.
- `SNOWFLAKE.TRUST_CENTER` access for Trust Center features.

All identifiers from user input flow through `_common.safe_id` / `clean_db` to prevent SQL injection in dynamically-built queries.

---

## 15. Deployment

Defined in `snowflake.yml`:

```yaml
definition_version: 2
entities:
  streamlit_app:
    type: streamlit
    identifier:
      database: USER$PHANSIVANG
      schema: PUBLIC
      name: GOVERNANCE_AGENT
    title: governance_agent
    query_warehouse: COMPUTE_WH
    compute_pool: SYSTEM_COMPUTE_POOL_CPU
    run_mode: SpcsOnly
    execute_as: OWNER
    main_file: main.py
    artifacts:
      - pyproject.toml
      - main.py
      - app/
      - .streamlit/config.toml
```

---

## 16. Testing

A `pytest` test suite lives in `tests/` covering every service module. Each test file mocks the Snowflake connection and validates SQL construction, scoring logic, and edge-case handling (missing data, inaccessible `ACCOUNT_USAGE`, empty DataFrames).

```
tests/
├── conftest.py           # Shared fixtures and mock connection
└── test_*.py             # One file per service (20+ modules)
```

Run tests:

```bash
pytest -q
```

---

## 17. Extension Points

- **New PII category:** add a regex entry to `PII_CATEGORIES` in `config.py`.
- **New scoring pillar:** add a `_score_*` function in `services/scoring.py` and include it in `compute_governance_score()` (total is the sum of the four 25-point pillars).
- **New Horizon tab:** create `app/ui/tabs/<name>.py` with a `render(...)` function, add the corresponding service in `app/services/`, and register the tab in the appropriate section in `main.py`.
