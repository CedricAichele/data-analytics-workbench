from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import configure_page, page_title
from app.config import APP_SUBTITLE, APP_TITLE
from app.services.dataset_workspace import get_active_analytics_result, get_active_dataset
from app.services.demo_flows import list_demo_flows, start_guided_demo
from app.services.project_state import get_project_summary
from app.services.template_registry import list_templates


configure_page(APP_TITLE)
active_dataset = get_active_dataset()
project_summary = get_project_summary(
    active_dataset=active_dataset,
    quality_report=get_active_analytics_result("generic_quality_report"),
)

page_title(APP_TITLE, "Turn CSV, Excel and JSON datasets into checked, prepared and exportable analytics results.")
st.write(
    "Use this app to create an analytics project, upload or select a dataset, check data quality, "
    "prepare and map columns, run generic or template-based analytics, export a BI-ready package, "
    "and save a Project Backup."
)

action_cols = st.columns(3)
with action_cols[0]:
    try:
        st.page_link("pages/project_setup.py", label="Create Project", icon=":material/workspace_premium:")
    except Exception:
        pass
with action_cols[1]:
    try:
        st.page_link("pages/1_data_upload.py", label="Load Dataset", icon=":material/upload_file:")
    except Exception:
        pass
with action_cols[2]:
    try:
        st.page_link("pages/workflow.py", label="Open Workflow", icon=":material/checklist:")
    except Exception:
        pass

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
st.write("For a quick review, start with the Sales/Retail demo.")
st.caption("New to the app? The demo shows the full workflow from sample data to Analytics Hub and Export Center.")
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

st.subheader("Current Status")
has_project = project_summary["Project name"] != "No project created"
has_dataset = project_summary["Active dataset"] != "No dataset loaded"
if not has_project and not has_dataset:
    with st.container(border=True):
        status_cols = st.columns(2)
        status_cols[0].write("No active project yet.")
        status_cols[1].write("No dataset loaded yet.")
        st.caption("Start with the Sales / Retail demo, create a project, or load your own dataset.")
        try:
            st.page_link("pages/project_setup.py", label="Create Project", icon=":material/workspace_premium:")
            st.page_link("pages/1_data_upload.py", label="Load Dataset", icon=":material/upload_file:")
        except Exception:
            pass
else:
    with st.container(border=True):
        summary_cols = st.columns(3)
        summary_cols[0].write(f"**Project name**  \n{project_summary['Project name']}")
        summary_cols[1].write(f"**Active dataset**  \n{project_summary['Active dataset']}")
        summary_cols[2].write(f"**Quality score**  \n{project_summary['Data quality score']}")
        summary_cols = st.columns(3)
        summary_cols[0].write(f"**Selected workflow**  \n{project_summary['Selected workflow']}")
        summary_cols[1].write(f"**Selected template**  \n{project_summary['Selected template']}")
        summary_cols[2].write(f"**Recommended next action**  \n{project_summary['Recommended next action']}")

st.subheader("How It Works")
process_steps = [
    ("1", "Load data", "Upload CSV, XLSX or JSON, or start with a sample."),
    ("2", "Check quality", "Review missingness, duplicates and rule findings."),
    ("3", "Prepare and map", "Transform the working copy and map business fields."),
    ("4", "Analyze", "Use Generic Analytics or a domain template."),
    ("5", "Export package", "Download documentation, results and backups."),
]
process_cols = st.columns(5)
for column, (number, title, description) in zip(process_cols, process_steps):
    with column:
        with st.container(border=True):
            st.caption(f"Step {number}")
            st.write(title)
            st.caption(description)
try:
    st.page_link("pages/workflow.py", label="Open full workflow", icon=":material/checklist:")
except Exception:
    pass

with st.expander("How the analytics model works"):
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

with st.expander("Available templates"):
    st.write(
        "Generic Analytics works with any supported tabular dataset. Domain templates are available for "
        "Sales / Retail, Manufacturing, Logistics and Finance."
    )
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

with st.expander("Data handling rules"):
    rules = [
        "raw_df keeps the original upload or sample unchanged.",
        "working_df is the only dataframe modified by user-triggered Data Preparation actions.",
        "Every user-triggered transformation is logged in transformation_log.",
        "Extra columns are preserved for profiling, preparation, generic analytics, and export.",
        "Analytics pages may create temporary derived columns internally, but they do not overwrite raw_df or working_df.",
    ]
    for rule in rules:
        st.write(f"- {rule}")
