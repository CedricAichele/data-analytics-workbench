from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import RETAIL_OPTIONAL_FIELDS, RETAIL_REQUIRED_FIELDS
from app.services.column_mapper import initialize_retail_mapping, validate_retail_mapping
from app.services.schema_detector import detect_retail_schema


configure_page("Column Mapping")
page_title("Column Mapping", "Map the current working dataset to the Retail / Sales Analytics schema.")

df = get_working_dataframe()
if df is None:
    st.stop()

columns = list(df.columns)
detection = st.session_state.get("retail_schema_detection") or detect_retail_schema(columns)
st.session_state["retail_schema_detection"] = detection

st.subheader("Schema Detection")
metrics = st.columns(3)
metrics[0].metric("Template", detection.detected_template or "Not detected")
metrics[1].metric("Confidence", f"{detection.confidence_score:.1f}%")
metrics[2].metric("Manual mapping required", "Yes" if detection.requires_manual_mapping else "No")

with st.expander("Matched and missing fields"):
    st.dataframe(
        [{"field": field, "column": column} for field, column in detection.matched_fields.items()],
        use_container_width=True,
        hide_index=True,
    )
    if detection.missing_fields:
        st.warning(f"Missing required fields: {', '.join(detection.missing_fields)}")

existing_mapping = st.session_state.get("column_mapping")
base_mapping = existing_mapping or initialize_retail_mapping(columns, detection)

st.subheader("Retail Field Mapping")
options = [""] + columns
mapping: dict[str, str | None] = {}

required_cols = st.columns(2)
for index, field in enumerate(RETAIL_REQUIRED_FIELDS):
    current = base_mapping.get(field) or ""
    selected = required_cols[index % 2].selectbox(
        f"{field} (required)",
        options=options,
        index=options.index(current) if current in options else 0,
        key=f"mapping_{field}",
    )
    mapping[field] = selected or None

st.write("Optional fields")
optional_cols = st.columns(3)
for index, field in enumerate(RETAIL_OPTIONAL_FIELDS):
    current = base_mapping.get(field) or ""
    selected = optional_cols[index % 3].selectbox(
        f"{field} (optional)",
        options=options,
        index=options.index(current) if current in options else 0,
        key=f"mapping_{field}",
    )
    mapping[field] = selected or None

validation = validate_retail_mapping(mapping, columns)
if validation.is_valid:
    st.success(validation.messages[0])
else:
    for message in validation.messages:
        st.warning(message)

if st.button("Save retail mapping", type="primary", disabled=not validation.is_valid):
    st.session_state["column_mapping"] = mapping
    st.session_state.pop("retail_analytics_result", None)
    st.session_state.pop("retail_clean_result", None)
    st.success("Retail mapping saved.")

with st.expander("Current mapping JSON"):
    st.json(mapping)
