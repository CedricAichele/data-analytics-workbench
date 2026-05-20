from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.layout import configure_page, page_title
from app.services.dataset_workspace import get_active_dataset
from app.services.project_state import get_active_project, get_project_metadata
from app.services.template_recommendations import (
    TemplateRecommendation,
    build_template_recommendations,
    no_dataset_guidance,
    recommend_best_template,
)
from app.services.template_registry import get_template, list_templates


MODE_PAGE = {
    "generic": "pages/6_generic_analytics.py",
    "sales_retail": "pages/5_retail_analytics.py",
    "manufacturing": "pages/8_manufacturing_analytics.py",
    "logistics": "pages/9_logistics_analytics.py",
    "finance": "pages/10_finance_analytics.py",
}


def _format_fields(fields: dict[str, str]) -> str:
    return ", ".join(f"{field} -> {column}" for field, column in fields.items()) or "None"


def _recommendation_rows(recommendations: list[TemplateRecommendation]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in recommendations:
        rows.append(
            {
                "Template": item.template_name,
                "Status": item.status,
                "Confidence": f"{item.confidence_score:.1f}%",
                "Required detected": f"{len(item.required_detected)}",
                "Required missing": ", ".join(item.required_missing) or "None",
                "Optional detected": len(item.optional_detected),
                "Mapping required": "Yes" if item.mapping_required else "No",
                "Recommended next action": item.recommended_next_action,
            }
        )
    return rows


def _diagnostic_table(template_id: str, recommendation: TemplateRecommendation) -> pd.DataFrame:
    template = get_template(template_id)
    rows = []
    for field in template.required_fields:
        rows.append(
            {
                "field type": "Required",
                "template field": field,
                "dataset column": recommendation.required_detected.get(field, ""),
                "status": "Detected" if field in recommendation.required_detected else "Missing",
            }
        )
    for field in template.optional_fields:
        rows.append(
            {
                "field type": "Optional",
                "template field": field,
                "dataset column": recommendation.optional_detected.get(field, ""),
                "status": "Detected" if field in recommendation.optional_detected else "Not detected",
            }
        )
    return pd.DataFrame(rows)


def _render_actions(recommendation: TemplateRecommendation) -> None:
    action_cols = st.columns(3)
    template = get_template(recommendation.template_id)
    with action_cols[0]:
        if recommendation.template_id == "generic" or not recommendation.mapping_required:
            try:
                st.page_link(MODE_PAGE[recommendation.template_id], label="Open analysis", icon=":material/arrow_forward:")
            except Exception:
                st.caption("Use the direct page URL if navigation is unavailable.")
        else:
            st.caption("Open analysis after required fields are mapped.")
    with action_cols[1]:
        if template.mapping_required:
            try:
                st.page_link("pages/4_column_mapping.py", label="Map columns", icon=":material/link:")
            except Exception:
                st.caption("Use the sidebar to open Column Mapping.")
        else:
            st.caption("Mapping is not required.")
    with action_cols[2]:
        try:
            st.page_link("pages/6_generic_analytics.py", label="Use Generic Analytics", icon=":material/query_stats:")
        except Exception:
            pass


configure_page("Analytics Hub")
page_title("Analytics Hub", "Choose the right analysis mode for the active dataset.")

st.write(
    "Generic Analytics works with any tabular dataset. Domain templates require matching or mapped fields "
    "so KPIs are calculated with clear business meaning."
)

active = get_active_dataset()
if active is None:
    st.warning(no_dataset_guidance())
    try:
        st.page_link("pages/1_data_upload.py", label="Open Data Upload", icon=":material/upload_file:")
    except Exception:
        pass
    st.stop()

working_df = active["working_df"]
project_metadata = get_project_metadata()
active_project = get_active_project()
template_mappings = active.get("template_mappings", {})
recommendations = build_template_recommendations(list(working_df.columns), mappings=template_mappings)
recommendation_by_id = {item.template_id: item for item in recommendations}
best = recommend_best_template(recommendations)

st.subheader("Active Context")
context_cols = st.columns(4)
context_cols[0].metric("Dataset", active.get("name", "Dataset"))
context_cols[1].metric("Rows", f"{len(working_df):,}")
context_cols[2].metric("Columns", f"{len(working_df.columns):,}")
context_cols[3].metric("Active project", project_metadata.get("project_name") if active_project else "No active project")
if active_project:
    st.caption(
        f"Project template: {project_metadata.get('suggested_template', 'Generic')} | "
        f"Workflow: {project_metadata.get('selected_workflow', 'Quick Data Check')}"
    )

st.subheader("Recommended Analysis")
if best is None:
    st.info("No domain template clearly fits this dataset. Start with Generic Analytics.")
    try:
        st.page_link("pages/6_generic_analytics.py", label="Open Generic Analytics", icon=":material/query_stats:")
    except Exception:
        pass
else:
    st.success(f"Recommended template: {best.template_name}")
    st.write(f"Why: {best.reason}")
    st.metric("Confidence", f"{best.confidence_score:.1f}%")
    _render_actions(best)

st.subheader("Template Compatibility Overview")
st.dataframe(_recommendation_rows(recommendations), use_container_width=True, hide_index=True)

st.subheader("Field Diagnostics")
templates = list_templates(include_generic=True)
template_by_id = {template.template_id: template for template in templates}
default_template_id = best.template_id if best is not None else "generic"
selected_template_id = st.selectbox(
    "Review template",
    [template.template_id for template in templates],
    index=[template.template_id for template in templates].index(default_template_id),
    format_func=lambda template_id: template_by_id[template_id].name,
)
selected_recommendation = recommendation_by_id[selected_template_id]
selected_template = get_template(selected_template_id)

st.write(selected_template.purpose)
st.caption(selected_template.when_to_use)

diag_cols = st.columns(4)
diag_cols[0].metric("Status", selected_recommendation.status)
diag_cols[1].metric("Confidence", f"{selected_recommendation.confidence_score:.1f}%")
diag_cols[2].metric("Required detected", len(selected_recommendation.required_detected))
diag_cols[3].metric("Required missing", len(selected_recommendation.required_missing))

if selected_template_id == "generic":
    st.info("Generic Analytics has no required business fields. It can be used with the current dataset immediately.")
else:
    st.dataframe(_diagnostic_table(selected_template_id, selected_recommendation), use_container_width=True, hide_index=True)
    with st.expander("Detected field details"):
        st.write("Detected required fields")
        st.write(_format_fields(selected_recommendation.required_detected))
        st.write("Missing required fields")
        st.write(", ".join(selected_recommendation.required_missing) or "None")
        st.write("Detected optional fields")
        st.write(_format_fields(selected_recommendation.optional_detected))

st.subheader("Next Actions")
_render_actions(selected_recommendation)
