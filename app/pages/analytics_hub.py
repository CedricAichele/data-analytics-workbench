from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.layout import configure_page, page_title
from app.services.dataset_workspace import get_active_dataset, get_active_template_mapping
from app.services.schema_detector import detect_template_schema
from app.services.template_registry import get_template, list_templates


MODE_PAGE = {
    "generic": "pages/6_generic_analytics.py",
    "sales_retail": "pages/5_retail_analytics.py",
    "manufacturing": "pages/8_manufacturing_analytics.py",
    "logistics": "pages/9_logistics_analytics.py",
    "finance": "pages/10_finance_analytics.py",
}


def _compatibility_for_mode(mode_id: str, df: pd.DataFrame) -> dict[str, object]:
    if mode_id == "generic":
        return {
            "status": "Available",
            "confidence": "100%",
            "matched_fields": {},
            "message": "Generic Analytics works with any active tabular dataset and does not require mapping.",
        }

    mapping = get_active_template_mapping(mode_id)
    if mapping:
        mapped_required = {field: column for field, column in mapping.items() if column in df.columns}
        return {
            "status": "Mapped",
            "confidence": "Saved mapping",
            "matched_fields": mapped_required,
            "message": "This dataset has a saved mapping for the selected analytics mode.",
        }

    detection = detect_template_schema(mode_id, list(df.columns))
    if not detection.requires_manual_mapping:
        status = "Likely compatible"
        message = "The active dataset appears compatible. You can run this mode or save a mapping first if you want to adjust matches."
    elif detection.confidence_score > 0:
        status = "Mapping needed"
        message = "Some required fields were detected, but mapping is incomplete. Open Column Mapping before using this domain mode."
    else:
        status = "Not mapped"
        message = "The active dataset is not mapped to this analytics template. Use Generic Analytics or load a compatible sample dataset."

    return {
        "status": status,
        "confidence": f"{detection.confidence_score:.1f}%",
        "matched_fields": detection.matched_fields,
        "message": message,
    }


configure_page("Analytics Hub")
page_title("Analytics Hub", "Choose the right analysis mode for the active dataset.")

active = get_active_dataset()
templates = list_templates(include_generic=True)
template_by_id = {template.template_id: template for template in templates}

st.write(
    "Use Generic Analytics for any supported dataset. Use a domain mode when your dataset has mapped fields "
    "for Sales / Retail, Manufacturing, Logistics or Finance KPIs."
)

if active is None:
    st.warning("Load a dataset first to run analytics. Generic Analytics and domain compatibility checks become available after upload.")
    try:
        st.page_link("pages/1_data_upload.py", label="Open Data Upload", icon=":material/upload_file:")
    except Exception:
        pass
    st.stop()

working_df = active["working_df"]
st.caption(f"Active dataset: {active.get('name', 'Dataset')} | {len(working_df):,} rows x {len(working_df.columns):,} columns")

mode_id = st.selectbox(
    "Choose analysis mode",
    [template.template_id for template in templates],
    format_func=lambda template_id: template_by_id[template_id].name,
)
template = get_template(mode_id)

st.subheader(template.name)
st.write(template.purpose)
st.caption(template.when_to_use)

compatibility = _compatibility_for_mode(mode_id, working_df)
metric_cols = st.columns(4)
metric_cols[0].metric("Status", template.status)
metric_cols[1].metric("Mapping", "Required" if template.mapping_required else "Not required")
metric_cols[2].metric("Compatibility", compatibility["status"])
metric_cols[3].metric("Confidence", compatibility["confidence"])

if template.required_fields:
    st.write("Required fields")
    st.dataframe(
        pd.DataFrame(
            {
                "required field": template.required_fields,
                "matched column": [compatibility["matched_fields"].get(field, "") for field in template.required_fields],
                "status": ["Matched" if field in compatibility["matched_fields"] else "Missing" for field in template.required_fields],
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

if compatibility["message"]:
    st.info(compatibility["message"])

action_cols = st.columns(3)
with action_cols[0]:
    try:
        st.page_link(MODE_PAGE[mode_id], label=f"Open {template.name}", icon=":material/arrow_forward:")
    except Exception:
        st.caption("Use the direct page URL if navigation is unavailable.")
with action_cols[1]:
    if template.mapping_required:
        try:
            st.page_link("pages/4_column_mapping.py", label="Open Column Mapping", icon=":material/link:")
        except Exception:
            pass
with action_cols[2]:
    try:
        st.page_link("pages/6_generic_analytics.py", label="Use Generic Analytics", icon=":material/query_stats:")
    except Exception:
        pass

with st.expander("All analysis modes"):
    rows = []
    for candidate in templates:
        candidate_status = _compatibility_for_mode(candidate.template_id, working_df)
        rows.append(
            {
                "mode": candidate.name,
                "purpose": candidate.purpose,
                "mapping required": "Yes" if candidate.mapping_required else "No",
                "current dataset": candidate_status["status"],
                "confidence": candidate_status["confidence"],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
