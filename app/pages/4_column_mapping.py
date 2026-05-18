from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.services.column_mapper import initialize_template_mapping, validate_template_mapping
from app.services.dataset_workspace import get_active_template_mapping, set_active_template_mapping
from app.services.schema_detector import detect_template_schema
from app.services.template_registry import implemented_domain_templates


configure_page("Column Mapping")
page_title("Column Mapping", "Map the current working dataset to implemented domain templates.")

df = get_working_dataframe()
if df is None:
    st.stop()

columns = list(df.columns)
templates = implemented_domain_templates()
template_ids = [template.template_id for template in templates]
template_by_id = {template.template_id: template for template in templates}
default_template_id = st.session_state.get("selected_template_id", "sales_retail")
if default_template_id not in template_ids:
    default_template_id = "sales_retail"

selected_template_id = st.selectbox(
    "Template to map",
    options=template_ids,
    index=template_ids.index(default_template_id),
    format_func=lambda template_id: template_by_id[template_id].name,
)
template = template_by_id[selected_template_id]
st.session_state["selected_template_id"] = selected_template_id

detection_key = f"{selected_template_id}_schema_detection"
detection = st.session_state.get(detection_key) or detect_template_schema(selected_template_id, columns)
st.session_state[detection_key] = detection
if selected_template_id == "sales_retail":
    st.session_state["retail_schema_detection"] = detection

st.subheader("Schema Detection")
metrics = st.columns(3)
metrics[0].metric("Template", detection.detected_template or "Not detected")
metrics[1].metric("Confidence", f"{detection.confidence_score:.1f}%")
metrics[2].metric("Manual mapping required", "Yes" if detection.requires_manual_mapping else "No")

with st.expander("Template requirements and detected fields"):
    st.write(template.purpose)
    st.write("Required fields")
    st.dataframe([{"field": field} for field in template.required_fields], use_container_width=True, hide_index=True)
    st.write("Matched fields")
    st.dataframe(
        [{"field": field, "column": column} for field, column in detection.matched_fields.items()],
        use_container_width=True,
        hide_index=True,
    )
    if detection.missing_fields:
        st.warning(f"Missing required fields: {', '.join(detection.missing_fields)}")

template_mappings = st.session_state.setdefault("template_mappings", {})
existing_mapping = get_active_template_mapping(selected_template_id) or template_mappings.get(selected_template_id)
if selected_template_id == "sales_retail":
    existing_mapping = st.session_state.get("column_mapping") or existing_mapping
elif selected_template_id == "manufacturing":
    existing_mapping = st.session_state.get("manufacturing_mapping") or existing_mapping
elif selected_template_id == "logistics":
    existing_mapping = st.session_state.get("logistics_mapping") or existing_mapping
elif selected_template_id == "finance":
    existing_mapping = st.session_state.get("finance_mapping") or existing_mapping

base_mapping = existing_mapping or initialize_template_mapping(selected_template_id, columns, detection)

st.subheader(f"{template.name} Field Mapping")
options = [""] + columns
mapping: dict[str, str | None] = {}

required_cols = st.columns(2)
for index, field in enumerate(template.required_fields):
    current = base_mapping.get(field) or ""
    selected = required_cols[index % 2].selectbox(
        f"{field} (required)",
        options=options,
        index=options.index(current) if current in options else 0,
        key=f"mapping_{selected_template_id}_{field}",
    )
    mapping[field] = selected or None

if template.optional_fields:
    st.write("Optional fields")
    optional_cols = st.columns(3)
    for index, field in enumerate(template.optional_fields):
        current = base_mapping.get(field) or ""
        selected = optional_cols[index % 3].selectbox(
            f"{field} (optional)",
            options=options,
            index=options.index(current) if current in options else 0,
            key=f"mapping_{selected_template_id}_{field}",
        )
        mapping[field] = selected or None

validation = validate_template_mapping(selected_template_id, mapping, columns)
if validation.is_valid:
    st.success(validation.messages[0])
else:
    for message in validation.messages:
        st.warning(message)

if st.button("Save mapping", type="primary", disabled=not validation.is_valid):
    set_active_template_mapping(selected_template_id, mapping)
    st.session_state["selected_template_id"] = selected_template_id
    if selected_template_id == "sales_retail":
        st.session_state.pop("retail_analytics_result", None)
        st.session_state.pop("retail_clean_result", None)
    elif selected_template_id == "manufacturing":
        st.session_state.pop("manufacturing_analytics_result", None)
        st.session_state.pop("manufacturing_clean_result", None)
    elif selected_template_id == "logistics":
        st.session_state.pop("logistics_analytics_result", None)
        st.session_state.pop("logistics_clean_result", None)
    elif selected_template_id == "finance":
        st.session_state.pop("finance_analytics_result", None)
        st.session_state.pop("finance_clean_result", None)
    st.success(f"{template.name} mapping saved.")

with st.expander("Current mapping JSON"):
    st.json(mapping)
