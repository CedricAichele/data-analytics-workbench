from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import configure_page, dataframe_status, page_title
from app.config import APP_DESCRIPTION, APP_SUBTITLE, APP_TITLE, OPERATIONS_TEMPLATE_PLACEHOLDER, RETAIL_TEMPLATE_NAME


configure_page(APP_TITLE)
page_title(
    APP_TITLE,
    APP_SUBTITLE,
)
st.write(APP_DESCRIPTION)

dataframe_status()

st.subheader("Workflow")
cols = st.columns(6)
steps = [
    ("1", "Data Upload", "Load CSV, XLSX, JSON, or the bundled retail sample."),
    ("2", "Data Profile", "Inspect the current working dataset."),
    ("3", "Data Preparation", "Apply controlled transformations to a working copy."),
    ("4", "Column Mapping", "Confirm required retail fields or map them manually."),
    ("5", "Retail Analytics", "Run SQL-backed KPIs, trends, and RFM segmentation."),
    ("6", "Summary", "Generate a deterministic management summary."),
]
for col, (number, label, text) in zip(cols, steps):
    with col:
        st.metric(number, label)
        st.caption(text)

st.divider()

left, right = st.columns([2, 1])
with left:
    st.subheader("Template Architecture")
    st.write(
        "Generic profiling works for supported tabular uploads. Business KPIs require a valid "
        "domain schema or a saved manual mapping so the app can interpret columns consistently."
    )
    st.dataframe(
        [
            {"template": RETAIL_TEMPLATE_NAME, "status": "Implemented", "purpose": "Sales KPIs, product/customer analytics, RFM"},
            {
                "template": OPERATIONS_TEMPLATE_PLACEHOLDER["name"],
                "status": "Planned",
                "purpose": "Future production, downtime, quality, and throughput analytics",
            },
        ],
        use_container_width=True,
        hide_index=True,
    )

with right:
    st.subheader("Readiness")
    has_data = "raw_df" in st.session_state
    has_working = "working_df" in st.session_state
    has_mapping = "column_mapping" in st.session_state
    has_analytics = "retail_analytics_result" in st.session_state
    st.checkbox("Dataset loaded", value=has_data, disabled=True)
    st.checkbox("Working copy ready", value=has_working, disabled=True)
    st.checkbox("Retail mapping saved", value=has_mapping, disabled=True)
    st.checkbox("Retail analytics calculated", value=has_analytics, disabled=True)
