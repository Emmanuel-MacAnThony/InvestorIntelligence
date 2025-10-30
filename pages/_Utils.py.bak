import os
import sys
import io
import csv
from datetime import datetime
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any

_THIS_DIR = os.path.dirname(__file__)
_APP_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from utils.airtable_client import get_airtable_client

st.set_page_config(page_title="Utilities", layout="wide")

# Load environment
_PROJECT_ROOT = Path(_APP_DIR).parent
_env_name = os.getenv("ENVIRONMENT", "development")
load_dotenv(_PROJECT_ROOT / f".env.{_env_name}", override=False)
load_dotenv(_PROJECT_ROOT / ".env", override=False)

st.title("Utilities")
st.caption("Admin tools for data hygiene and exports")

airtable = get_airtable_client()


@st.cache_data(ttl=120)
def _load_bases() -> List[Dict[str, Any]]:
    return airtable.get_bases()


@st.cache_data(ttl=120)
def _load_tables(base_id: str) -> List[Dict[str, Any]]:
    return airtable.get_tables(base_id)


# Navigation helpers for a simple utilities hub
def _set_tool(tool: str = None) -> None:
    try:
        if tool:
            st.query_params["tool"] = tool
        else:
            if "tool" in st.query_params:
                del st.query_params["tool"]
    except Exception:
        pass


def _render_landing() -> None:
    st.markdown("---")
    st.header("Utilities Hub")
    st.caption("Pick a tool below")

    # Single clickable card with hover + pointer
    card_css = """
    <style>
    .util-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 220px));
        gap: 20px;
        justify-content: start;
        max-width: 760px;
        margin: 0;
    }
    .util-card { 
        background: linear-gradient(135deg, #3b82f6, #9333ea);
        width: 220px;
        aspect-ratio: 1 / 1;
        border-radius: 14px; 
        color: white; 
        text-decoration: none; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        padding: 16px; 
        box-sizing: border-box;
        transition: filter .15s ease, transform .05s ease; 
        cursor: pointer; 
    }
    .util-card:hover { 
        filter: brightness(0.92); 
        transform: translateY(-1px); 
    }
    .util-card .title { font-size: 16px; font-weight: 700; text-align: center; }
    .util-card .desc { opacity: 0.9; margin-top: 6px; font-size: 13px; text-align: center; }
    </style>
    """
    st.markdown(card_css, unsafe_allow_html=True)

    st.markdown(
        """
        <div class=\"util-grid\">
            <a class=\"util-card\" href=\"?tool=missing_linkedin\" target=\"_self\"> 
                <div class=\"title\">Missing/Invalid LinkedIn</div>
                <div class=\"desc\">Find contacts with empty or bad LinkedIn URLs and export.</div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Determine selected utility
selected_tool = None
try:
    qp_tool = st.query_params.get("tool")
    if isinstance(qp_tool, list):
        selected_tool = qp_tool[0] if qp_tool else None
    else:
        selected_tool = qp_tool
except Exception:
    selected_tool = None

if not selected_tool:
    _render_landing()
    st.stop()

# Back to hub
st.markdown("---")
if st.button("← All Utilities"):
    _set_tool(None)
    st.rerun()

# Section: Contacts missing/invalid LinkedIn
if selected_tool == "missing_linkedin":
    st.header("Contacts Missing/Invalid LinkedIn URL")

bases = _load_bases()
if not bases:
    st.warning("No Airtable bases available. Check your AIRTABLE_API_KEY.")
    st.stop()

base_options = {b.get("name", b.get("id")): b.get("id") for b in bases}
base_name = st.selectbox("Base", list(base_options.keys()))
base_id = base_options[base_name]

tables = _load_tables(base_id)
if not tables:
    st.warning("No tables found for selected base.")
    st.stop()

table_options = {t.get("name", t.get("id")): t.get("id") for t in tables}
table_name = st.selectbox("Table", list(table_options.keys()))
table_id = table_options[table_name]

# LinkedIn field name
default_field_names = [
    "LinkedIn",
    "LinkedIn URL",
    "LinkedIn Profile",
    "Linkedin",
    "Linkedin URL",
]
all_fields = []
for t in tables:
    if t.get("id") == table_id:
        for f in t.get("fields", []) or []:
            fname = f.get("name")
            if fname:
                all_fields.append(fname)
        break

li_field = st.selectbox(
    "LinkedIn field",
    sorted(all_fields) if all_fields else default_field_names,
    index=(
        sorted(all_fields).index("LinkedIn")
        if all_fields and "LinkedIn" in all_fields
        else 0
    ),
)

# Filter options
colA, colB, colC = st.columns(3)
with colA:
    empty_only = st.checkbox("Empty/blank", value=True)
with colB:
    invalid_host = st.checkbox("Invalid host (no 'linkedin.com')", value=True)
with colC:
    min_length = st.number_input(
        "Min length",
        min_value=0,
        max_value=200,
        value=8,
        step=1,
        help="Treat values shorter than this as invalid",
    )

# Columns to include
preselect = [
    c for c in ["Name", "Email", li_field, "Company", "Record ID"] if c in all_fields
]
include_cols = st.multiselect(
    "Columns to include in export",
    sorted(all_fields),
    default=preselect or (sorted(all_fields)[:5] if all_fields else []),
)

# Build Airtable filterByFormula
formula_clauses: List[str] = []
# Coerce field to text safely where needed
coerced = f"CONCATENATE({{{li_field}}}, '')"
if empty_only:
    # Use BLANK() and empty-string checks (avoid IS_BLANK which may not be recognized)
    formula_clauses.append(f"OR({{{li_field}}} = BLANK(), {coerced} = '')")
if invalid_host:
    # Treat as invalid when 'linkedin.com' not found in the lowercased text
    formula_clauses.append(f"FIND('linkedin.com', LOWER({coerced})) = 0")
if min_length and min_length > 0:
    formula_clauses.append(f"LEN(TRIM({coerced})) < {int(min_length)}")

if not formula_clauses:
    st.info("Select at least one rule to filter records.")
    st.stop()

filter_formula = "OR(" + ", ".join(formula_clauses) + ")"

st.markdown("### Search")
run = st.button("🔎 Find records")


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_filtered(
    base_id: str, table_id: str, filter_formula: str, fields: List[str]
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    offset = None
    while True:
        resp = airtable.get_records(
            base_id,
            table_id,
            page_size=100,
            offset=offset,
            fields=fields if fields else None,
            filter_by_formula=filter_formula,
        )
        if resp.get("status") and resp.get("status") != 200:
            # Surface useful error for debugging formula issues
            st.error(f"Airtable error {resp.get('status')}: {resp.get('error')}")
            return []
        records = resp.get("records", [])
        results.extend(records)
        offset = resp.get("offset")
        if not offset:
            break
    return results


if run:
    with st.spinner("Querying Airtable…"):
        records = _fetch_filtered(base_id, table_id, filter_formula, include_cols)

    st.success(f"Found {len(records)} matching records")

    # Build preview table (first 50)
    preview_rows = []
    for r in records[:50]:
        fields = r.get("fields", {})
        row = {c: fields.get(c, "") for c in include_cols}
        preview_rows.append(row)

    if preview_rows:
        st.markdown("### Preview (first 50)")
        st.dataframe(preview_rows, use_container_width=True)
    else:
        st.info("No records to preview")

    # Prepare downloads
    def _to_csv(rows: List[Dict[str, Any]]) -> bytes:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=include_cols)
        w.writeheader()
        for row in rows:
            w.writerow(
                {
                    k: ("" if row.get(k) is None else str(row.get(k)))
                    for k in include_cols
                }
            )
        return buf.getvalue().encode("utf-8")

    def _to_txt(rows: List[Dict[str, Any]]) -> bytes:
        buf = io.StringIO()
        for row in rows:
            buf.write(" | ".join(str(row.get(k, "")) for k in include_cols) + "\n")
        return buf.getvalue().encode("utf-8")

    file_base = (
        f"missing_linkedin_{table_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    )
    csv_bytes = _to_csv(
        [{c: r.get("fields", {}).get(c, "") for c in include_cols} for r in records]
    )
    txt_bytes = _to_txt(
        [{c: r.get("fields", {}).get(c, "") for c in include_cols} for r in records]
    )

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Download CSV",
            data=csv_bytes,
            file_name=f"{file_base}.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            "⬇️ Download TXT",
            data=txt_bytes,
            file_name=f"{file_base}.txt",
            mime="text/plain",
        )

    st.caption(
        "PDF export can be added later (rendered table to PDF). For now, CSV/TXT are provided."
    )
