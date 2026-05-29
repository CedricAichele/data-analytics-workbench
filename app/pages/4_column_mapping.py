from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.services.column_mapper import initialize_template_mapping, validate_template_mapping
from app.services.dataset_workspace import get_active_template_mapping, set_active_template_mapping
from app.services.mapping_profiles import (
    apply_mapping_profile,
    build_mapping_profile_backup,
    import_mapping_profile,
    initialize_mapping_profiles,
    list_mapping_profiles,
    load_mapping_profile_backup,
    save_mapping_profile,
    validate_mapping_profile,
)
from app.services.schema_detector import detect_template_schema
from app.services.template_registry import implemented_domain_templates


configure_page("Column Mapping")
page_title("Column Mapping", "Map the current working dataset to implemented domain templates.")

df = get_working_dataframe()
if df is None:
    st.stop()

initialize_mapping_profiles()
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

st.subheader("Mapping Profiles")
st.caption("Save a reusable profile when recurring files use the same or similar column names.")
profile_feedback = st.session_state.pop("mapping_profile_feedback", None)
if profile_feedback:
    feedback_type, feedback_message = profile_feedback
    if feedback_type == "success":
        st.success(feedback_message)
    else:
        st.info(feedback_message)

save_cols = st.columns([1, 1, 1])
profile_name = save_cols[0].text_input("Profile name", value=f"{template.name} Mapping", key=f"profile_name_{selected_template_id}")
profile_notes = save_cols[1].text_input("Notes", value="", key=f"profile_notes_{selected_template_id}")
if save_cols[2].button("Save Mapping Profile", disabled=not validation.is_valid, key=f"save_profile_{selected_template_id}"):
    try:
        _, created = save_mapping_profile(
            profile_name=profile_name,
            template_id=selected_template_id,
            mapping=mapping,
            notes=profile_notes,
        )
        st.session_state["mapping_profile_feedback"] = (
            "success" if created else "info",
            f"{'Saved' if created else 'Activated existing'} Mapping Profile: {profile_name.strip() or template.name}",
        )
        st.rerun()
    except Exception as exc:
        st.error(f"Mapping Profile could not be saved: {exc}")

profiles = list_mapping_profiles(selected_template_id)
if profiles:
    selected_profile_id = st.selectbox(
        "Saved Mapping Profiles",
        [profile["profile_id"] for profile in profiles],
        format_func=lambda profile_id: next(profile["profile_name"] for profile in profiles if profile["profile_id"] == profile_id),
        key=f"profile_select_{selected_template_id}",
    )
    selected_profile = next(profile for profile in profiles if profile["profile_id"] == selected_profile_id)
    profile_validation = validate_mapping_profile(selected_profile, columns)
    if profile_validation.is_valid:
        st.success(profile_validation.messages[0])
    else:
        for message in profile_validation.messages:
            st.warning(message)
    profile_cols = st.columns(3)
    if profile_cols[0].button("Apply Mapping Profile", disabled=not profile_validation.is_valid, key=f"apply_profile_{selected_template_id}"):
        try:
            profile_mapping = apply_mapping_profile(selected_profile, columns)
            set_active_template_mapping(selected_template_id, profile_mapping)
            for field, column in profile_mapping.items():
                st.session_state[f"mapping_{selected_template_id}_{field}"] = column or ""
            st.session_state["mapping_profile_feedback"] = ("success", f"Applied Mapping Profile: {selected_profile['profile_name']}")
            st.rerun()
        except Exception as exc:
            st.error(f"Mapping Profile could not be applied: {exc}")
    profile_cols[1].download_button(
        "Download Mapping Profile Backup",
        data=build_mapping_profile_backup(selected_profile),
        file_name=f"{selected_profile['profile_id']}_mapping_profile_backup.json",
        mime="application/json",
        key=f"download_profile_{selected_template_id}",
    )
else:
    st.info("No Mapping Profiles saved for this template yet.")

profile_upload = st.file_uploader("Load Mapping Profile Backup", type=["json"], key=f"profile_upload_{selected_template_id}")
if profile_upload is not None and st.button("Load Mapping Profile", key=f"load_profile_{selected_template_id}"):
    try:
        loaded_profile = load_mapping_profile_backup(profile_upload)
        _, created = import_mapping_profile(loaded_profile)
        st.session_state["mapping_profile_feedback"] = (
            "success" if created else "info",
            f"{'Loaded' if created else 'Activated existing'} Mapping Profile: {loaded_profile['profile_name']}",
        )
        st.rerun()
    except Exception as exc:
        st.error(f"Mapping Profile Backup could not be loaded: {exc}")

with st.expander("Current mapping details"):
    st.json(mapping)
