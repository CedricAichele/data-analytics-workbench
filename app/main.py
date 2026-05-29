from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import configure_page, dataframe_status, page_title, render_process_steps
from app.config import APP_SUBTITLE, APP_TITLE
from app.services.dataset_workspace import get_active_analytics_result, get_active_dataset
from app.services.demo_flows import list_demo_flows, start_guided_demo
from app.services.project_state import compact_project_summary_rows, get_project_summary
from app.services.template_registry import list_templates
from app.services.workflow import build_workflow_steps, get_recommended_next_action


configure_page(APP_TITLE)
page_title(APP_TITLE, APP_SUBTITLE)
st.write(
    "Data Analytics Workbench helps turn raw CSV, Excel and JSON datasets into checked, "
    "prepared and exportable analytics results."
)

st.subheader("What You Can Do")
intro_cols = st.columns(4)
with intro_cols[0]:
    st.write("Create a project")
    st.caption("Document the goal, owner, template and desired outputs.")
with intro_cols[1]:
    st.write("Load and check data")
    st.caption("Upload a dataset, inspect structure and review quality.")
with intro_cols[2]:
    st.write("Prepare and analyze")
    st.caption("Rename columns, build a dictionary, map fields and run analytics.")
with intro_cols[3]:
    st.write("Export results")
    st.caption("Download a BI-ready package or save a Project Backup.")

dataframe_status()

active_dataset = get_active_dataset()
project_summary = get_project_summary(
    active_dataset=active_dataset,
    quality_report=get_active_analytics_result("generic_quality_report"),
)

st.subheader("Project Summary")
if project_summary["Project name"] == "No project created":
    st.info("Create a project to document your analysis workflow.")
if project_summary["Active dataset"] == "No dataset loaded":
    st.info("Load a dataset to start profiling, preparation and analytics.")
st.dataframe(compact_project_summary_rows(project_summary), use_container_width=True, hide_index=True)

st.subheader("Usage Modes")
mode_cols = st.columns(3)
with mode_cols[0]:
    st.write("Quick Data Check")
    st.caption("Upload data, inspect structure and quality, and export documentation.")
with mode_cols[1]:
    st.write("BI-ready Data Preparation")
    st.caption("Clean data, create a data dictionary, validate quality and export a BI-ready package.")
with mode_cols[2]:
    st.write("Domain KPI Analysis")
    st.caption("Map fields to Sales, Manufacturing, Logistics or Finance templates and review KPI outputs.")

st.subheader("Recommended Workflow")
workflow_steps = build_workflow_steps(
    st.session_state.get("project_metadata", {}),
    active_dataset,
    (active_dataset or {}).get("analytics_results", {}),
)
st.caption(f"Recommended next action: {get_recommended_next_action(workflow_steps)}")
render_process_steps(workflow_steps)
try:
    st.page_link("pages/project_setup.py", label="Create or update project", icon=":material/arrow_forward:")
    st.page_link("pages/workflow.py", label="Open guided workflow", icon=":material/checklist:")
except Exception:
    pass

st.divider()

st.subheader("Two-Layer Analytics Model")
layer_cols = st.columns(2)
with layer_cols[0]:
    st.write("Generic workflow")
    st.write(
        "Works with any supported tabular dataset: upload, profile, prepare, score quality, "
        "run generic analytics, and export the transformed working copy."
    )
    st.caption("No predefined business schema is required.")
with layer_cols[1]:
    st.write("Domain KPI templates")
    st.write(
        "Sales, Manufacturing, Logistics and Finance KPI pages require schema detection or manual column mapping "
        "so metrics are calculated from fields with clear business meaning."
    )
    st.caption("Templates use mapped fields for KPI logic but do not remove extra columns.")

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

st.subheader("Try a Guided Demo")
demo_feedback = st.session_state.pop("guided_demo_feedback", None)
if demo_feedback:
    st.success(demo_feedback)
    demo_links = st.columns(2)
    with demo_links[0]:
        try:
            st.page_link("pages/workflow.py", label="Open Workflow", icon=":material/checklist:")
        except Exception:
            pass
    with demo_links[1]:
        try:
            st.page_link("pages/analytics_hub.py", label="Open Analytics Hub", icon=":material/query_stats:")
        except Exception:
            pass
st.write("New to the app? Start with the Sales / Retail demo to see the full workflow.")
demo_cols = st.columns(4)
for index, demo in enumerate(list_demo_flows()):
    with demo_cols[index]:
        st.write(demo.label)
        st.caption(demo.description)
        if st.button(
            f"Start {demo.label}",
            type="primary" if demo.template_id == "sales_retail" else "secondary",
            key=f"guided_demo_{demo.template_id}",
        ):
            result = start_guided_demo(demo.template_id)
            st.session_state["guided_demo_feedback"] = (
                f"{result.message} Continue with Workflow or Analytics Hub."
            )
            st.rerun()

with st.expander("Current readiness"):
    has_data = "raw_df" in st.session_state
    has_working = "working_df" in st.session_state
    has_retail_mapping = "column_mapping" in st.session_state
    has_manufacturing_mapping = "manufacturing_mapping" in st.session_state
    has_logistics_mapping = "logistics_mapping" in st.session_state
    has_finance_mapping = "finance_mapping" in st.session_state
    has_retail_analytics = "retail_analytics_result" in st.session_state
    has_manufacturing_analytics = "manufacturing_analytics_result" in st.session_state
    has_logistics_analytics = "logistics_analytics_result" in st.session_state
    has_finance_analytics = "finance_analytics_result" in st.session_state
    readiness_cols = st.columns(4)
    readiness_cols[0].checkbox("Dataset loaded", value=has_data, disabled=True)
    readiness_cols[0].checkbox("Working copy ready", value=has_working, disabled=True)
    readiness_cols[1].checkbox("Sales mapping saved", value=has_retail_mapping, disabled=True)
    readiness_cols[1].checkbox("Manufacturing mapping saved", value=has_manufacturing_mapping, disabled=True)
    readiness_cols[2].checkbox("Logistics mapping saved", value=has_logistics_mapping, disabled=True)
    readiness_cols[2].checkbox("Finance mapping saved", value=has_finance_mapping, disabled=True)
    readiness_cols[3].checkbox("Sales analytics calculated", value=has_retail_analytics, disabled=True)
    readiness_cols[3].checkbox("Manufacturing analytics calculated", value=has_manufacturing_analytics, disabled=True)
    readiness_cols[3].checkbox("Logistics analytics calculated", value=has_logistics_analytics, disabled=True)
    readiness_cols[3].checkbox("Finance analytics calculated", value=has_finance_analytics, disabled=True)
