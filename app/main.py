from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import configure_page, dataframe_status, page_title
from app.config import APP_DESCRIPTION, APP_SUBTITLE, APP_TITLE
from app.services.template_registry import list_templates


configure_page(APP_TITLE)
page_title(APP_TITLE, APP_SUBTITLE)
st.write(APP_DESCRIPTION)

dataframe_status()

st.subheader("Two-Layer Analytics Architecture")
layer_cols = st.columns(2)
with layer_cols[0]:
    st.write("Layer 1: Generic Workflow")
    st.write(
        "Works with any supported tabular dataset: upload, profile, prepare, score quality, "
        "run generic analytics, and export the transformed working copy."
    )
    st.caption("No predefined schema is required.")
with layer_cols[1]:
    st.write("Layer 2: Domain KPI Templates")
    st.write(
        "Business KPI pages require schema detection or manual column mapping so metrics are calculated "
        "from fields with clear business meaning."
    )
    st.caption("Templates use mapped fields for KPI logic but do not remove extra columns.")

st.subheader("Workflow")
cols = st.columns(6)
steps = [
    ("1", "Upload", "Load CSV, XLSX, JSON, or a sample dataset."),
    ("2", "Profile", "Inspect structure, missingness, types, and quality."),
    ("3", "Prepare", "Apply logged transformations to working_df only."),
    ("4", "Explore", "Use Generic Analytics when no template fits."),
    ("5", "Map", "Map domain fields for KPI templates."),
    ("6", "Summarize", "Review KPI outputs and management narrative."),
]
for col, (number, label, text) in zip(cols, steps):
    with col:
        st.metric(number, label)
        st.caption(text)

st.divider()

st.subheader("Template Portfolio")
template_rows = [
    {
        "template": template.name,
        "status": template.status,
        "mapping_required": "Yes" if template.mapping_required else "No",
        "purpose": template.purpose,
    }
    for template in list_templates(include_generic=True)
]
st.dataframe(template_rows, use_container_width=True, hide_index=True)

st.subheader("Data Handling Rules")
rules = [
    "raw_df keeps the original upload or sample unchanged.",
    "working_df is the only dataframe modified by user-triggered Data Preparation actions.",
    "Every user-triggered transformation is logged in transformation_log.",
    "Extra columns are preserved for profiling, preparation, generic analytics, and export.",
    "Analytics pages may create temporary derived columns internally, but they do not overwrite raw_df or working_df.",
]
for rule in rules:
    st.write(f"- {rule}")

with st.expander("Current readiness"):
    has_data = "raw_df" in st.session_state
    has_working = "working_df" in st.session_state
    has_retail_mapping = "column_mapping" in st.session_state
    has_manufacturing_mapping = "manufacturing_mapping" in st.session_state
    has_retail_analytics = "retail_analytics_result" in st.session_state
    has_manufacturing_analytics = "manufacturing_analytics_result" in st.session_state
    readiness_cols = st.columns(3)
    readiness_cols[0].checkbox("Dataset loaded", value=has_data, disabled=True)
    readiness_cols[0].checkbox("Working copy ready", value=has_working, disabled=True)
    readiness_cols[1].checkbox("Sales mapping saved", value=has_retail_mapping, disabled=True)
    readiness_cols[1].checkbox("Manufacturing mapping saved", value=has_manufacturing_mapping, disabled=True)
    readiness_cols[2].checkbox("Sales analytics calculated", value=has_retail_analytics, disabled=True)
    readiness_cols[2].checkbox("Manufacturing analytics calculated", value=has_manufacturing_analytics, disabled=True)
