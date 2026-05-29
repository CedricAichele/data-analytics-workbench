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


def _open_page_button(label: str, page: str, key: str, *, primary: bool = False) -> None:
    if st.button(label, type="primary" if primary else "secondary", key=key, use_container_width=True):
        try:
            st.switch_page(page)
        except Exception:
            st.info("Use the sidebar navigation if direct page switching is unavailable.")


def _open_analysis_label(recommendation: TemplateRecommendation) -> str:
    if recommendation.template_id == "generic":
        return "Open Generic Analytics"
    return f"Open {recommendation.template_name}"


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
                "Required missing": "None" if not item.required_missing else f"{len(item.required_missing)} missing",
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


def _render_primary_recommendation(recommendation: TemplateRecommendation) -> None:
    missing = ", ".join(recommendation.required_missing) or "None"
    required_total = len(recommendation.required_detected) + len(recommendation.required_missing)
    with st.container(border=True):
        st.caption("Recommended Analysis")
        st.markdown(f"### {recommendation.template_name}")
        st.write(recommendation.reason)
        summary_cols = st.columns(3)
        summary_cols[0].metric("Confidence", f"{recommendation.confidence_score:.1f}%")
        summary_cols[1].metric("Required fields detected", f"{len(recommendation.required_detected)}/{required_total}")
        summary_cols[2].metric("Missing required fields", missing)
        action_cols = st.columns([1.4, 1, 1])
        with action_cols[0]:
            _open_page_button(
                _open_analysis_label(recommendation),
                MODE_PAGE[recommendation.template_id],
                f"primary_open_{recommendation.template_id}",
                primary=True,
            )
        with action_cols[1]:
            _open_page_button("Review Column Mapping", "pages/4_column_mapping.py", "primary_mapping")
        with action_cols[2]:
            _open_page_button("Use Generic Analytics", "pages/6_generic_analytics.py", "primary_generic")


def _render_template_action(recommendation: TemplateRecommendation) -> None:
    template = get_template(recommendation.template_id)
    if recommendation.template_id == "generic" or not recommendation.mapping_required:
        _open_page_button(
            _open_analysis_label(recommendation),
            MODE_PAGE[recommendation.template_id],
            f"action_open_{recommendation.template_id}",
            primary=recommendation.status == "Recommended",
        )
    elif template.mapping_required:
        _open_page_button("Map columns", "pages/4_column_mapping.py", f"action_map_{recommendation.template_id}")
    else:
        st.caption("Use Generic Analytics first.")


def _render_secondary_actions(recommendation: TemplateRecommendation) -> None:
    template = get_template(recommendation.template_id)
    action_cols = st.columns(2)
    with action_cols[0]:
        if template.mapping_required:
            _open_page_button("Map columns", "pages/4_column_mapping.py", f"secondary_map_{recommendation.template_id}")
        else:
            st.caption("Mapping is not required.")
    with action_cols[1]:
        _open_page_button("Use Generic Analytics", "pages/6_generic_analytics.py", f"secondary_generic_{recommendation.template_id}")


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
    with st.container(border=True):
        st.caption("Recommended Analysis")
        st.markdown("### Generic Analytics")
        st.write("No domain template clearly fits this dataset. Start with Generic Analytics.")
        metric_cols = st.columns(3)
        metric_cols[0].metric("Confidence", "100.0%")
        metric_cols[1].metric("Required fields detected", "Not required")
        metric_cols[2].metric("Missing required fields", "None")
        action_cols = st.columns([1.4, 1])
        with action_cols[0]:
            _open_page_button("Open Generic Analytics", "pages/6_generic_analytics.py", "primary_generic_no_match", primary=True)
        with action_cols[1]:
            _open_page_button("Load another dataset", "pages/1_data_upload.py", "primary_upload_no_match")
else:
    _render_primary_recommendation(best)

st.subheader("Template Compatibility Overview")
st.dataframe(_recommendation_rows(recommendations), use_container_width=True, hide_index=True)
with st.expander("Show missing-field details"):
    missing_rows = [
        {
            "Template": item.template_name,
            "Missing required fields": ", ".join(item.required_missing) or "None",
            "Detected required fields": _format_fields(item.required_detected),
            "Detected optional fields": _format_fields(item.optional_detected),
        }
        for item in recommendations
        if item.template_id != "generic"
    ]
    st.dataframe(missing_rows, use_container_width=True, hide_index=True)

st.subheader("Analysis Modes")
mode_cols = st.columns(2)
for index, recommendation in enumerate(recommendations):
    with mode_cols[index % 2]:
        with st.container(border=True):
            header_cols = st.columns([1.2, 0.8])
            header_cols[0].markdown(f"**{recommendation.template_name}**")
            header_cols[1].metric("Confidence", f"{recommendation.confidence_score:.1f}%")
            st.caption(f"{recommendation.status} | {recommendation.reason}")
            if recommendation.required_missing:
                st.caption(f"Missing required fields: {len(recommendation.required_missing)}")
            else:
                st.caption("Missing required fields: None")
            _render_template_action(recommendation)

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
    with st.expander("Show field diagnostics"):
        st.dataframe(_diagnostic_table(selected_template_id, selected_recommendation), use_container_width=True, hide_index=True)
        st.write("Detected required fields")
        st.write(_format_fields(selected_recommendation.required_detected))
        st.write("Missing required fields")
        st.write(", ".join(selected_recommendation.required_missing) or "None")
        st.write("Detected optional fields")
        st.write(_format_fields(selected_recommendation.optional_detected))

st.subheader("Next Actions")
_render_secondary_actions(selected_recommendation)
