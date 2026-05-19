from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, page_title
from app.services.data_dictionary import generate_data_dictionary
from app.services.dataset_workspace import add_or_activate_dataset, get_active_analytics_result, get_active_dataset, sync_legacy_state
from app.services.project_backup import build_project_backup_zip, load_project_backup_zip, safe_project_filename
from app.services.project_state import (
    OUTPUT_OPTIONS,
    TEMPLATE_OPTIONS,
    WORKFLOW_OPTIONS,
    compact_project_summary_rows,
    get_project_metadata,
    get_project_summary,
    initialize_project_state,
    set_project_metadata,
    update_project_metadata,
)
from app.services.quality_score import calculate_quality_score


configure_page("Project Setup")
page_title("Project Setup", "Define the business context for this analytics project.")

initialize_project_state()
metadata = get_project_metadata()
active = get_active_dataset()

st.info(
    "Create a lightweight project first, or load data first and document the project later. "
    "Project details help make exports and handoffs easier to understand."
)

st.subheader("Project Details")
with st.form("project_setup_form"):
    project_name = st.text_input("Project name", value=metadata.get("project_name", ""))
    project_description = st.text_area("Project description", value=metadata.get("project_description", ""), height=90)
    analysis_goal = st.text_area("Analysis goal", value=metadata.get("analysis_goal", ""), height=90)
    optional_cols = st.columns(3)
    company_department = optional_cols[0].text_input("Company / department", value=metadata.get("company_department", ""))
    data_owner = optional_cols[1].text_input("Data owner or responsible person", value=metadata.get("data_owner", ""))
    reporting_period = optional_cols[2].text_input("Reporting period", value=metadata.get("reporting_period", ""))
    workflow_cols = st.columns(3)
    selected_workflow = workflow_cols[0].selectbox(
        "Workflow",
        WORKFLOW_OPTIONS,
        index=WORKFLOW_OPTIONS.index(metadata.get("selected_workflow", "Quick Data Check"))
        if metadata.get("selected_workflow") in WORKFLOW_OPTIONS
        else 0,
    )
    suggested_template = workflow_cols[1].selectbox(
        "Suggested domain template",
        TEMPLATE_OPTIONS,
        index=TEMPLATE_OPTIONS.index(metadata.get("suggested_template", "Generic"))
        if metadata.get("suggested_template") in TEMPLATE_OPTIONS
        else 0,
    )
    desired_outputs = workflow_cols[2].multiselect(
        "Desired output",
        OUTPUT_OPTIONS,
        default=[output for output in metadata.get("desired_outputs", []) if output in OUTPUT_OPTIONS] or ["Data Quality Report"],
    )
    notes = st.text_area("Notes", value=metadata.get("notes", ""), height=90)
    submitted = st.form_submit_button("Save Project")

if submitted:
    update_project_metadata(
        project_name=project_name,
        project_description=project_description,
        analysis_goal=analysis_goal,
        company_department=company_department,
        data_owner=data_owner,
        reporting_period=reporting_period,
        selected_workflow=selected_workflow,
        suggested_template=suggested_template,
        desired_outputs=desired_outputs,
        notes=notes,
    )
    st.success("Project saved.")
    st.rerun()

st.subheader("Project Summary")
summary = get_project_summary(
    active_dataset=active,
    quality_report=get_active_analytics_result("generic_quality_report") or (calculate_quality_score(active["working_df"]) if active else None),
)
st.dataframe(compact_project_summary_rows(summary), use_container_width=True, hide_index=True)

st.subheader("Continue Previous Project")
backup_upload = st.file_uploader("Load Project Backup", type=["zip"], help="Upload a Project Backup ZIP created by Data Analytics Workbench.")
if backup_upload is not None:
    try:
        loaded = load_project_backup_zip(backup_upload)
        set_project_metadata(loaded.project_metadata)
        if loaded.cleaned_dataset is not None:
            restored_metadata = dict(loaded.dataset_metadata or {})
            restored_metadata.update({"source": "project backup", "file_type": "csv"})
            add_or_activate_dataset(
                loaded.project_metadata.get("project_name", "Restored project dataset"),
                loaded.cleaned_dataset,
                restored_metadata,
            )
            restored_active = get_active_dataset()
            if restored_active is not None:
                restored_active["transformation_log"] = list(loaded.transformation_log)
                restored_active["template_mappings"] = dict(loaded.column_mappings)
                sync_legacy_state()
        else:
            st.session_state["restored_column_mappings"] = loaded.column_mappings
            st.session_state["restored_transformation_log"] = loaded.transformation_log
        for message in loaded.messages:
            st.info(message)
        st.success("Project Backup loaded.")
    except Exception as exc:
        st.error(f"Project Backup could not be loaded: {exc}")

st.subheader("Download Project Backup")
current_metadata = get_project_metadata()
if not current_metadata.get("project_name"):
    st.info("Save a project name before downloading a Project Backup.")
else:
    dictionary_df = None
    quality_report = None
    if active is not None:
        dictionary_df = generate_data_dictionary(active["working_df"], template_mappings=active.get("template_mappings", {}))
        quality_report = get_active_analytics_result("generic_quality_report") or calculate_quality_score(active["working_df"])
    backup_bytes = build_project_backup_zip(
        project_metadata=current_metadata,
        active_dataset=active,
        data_dictionary=dictionary_df,
        quality_report=quality_report,
        quality_rules=get_active_analytics_result("quality_rules_result"),
    )
    st.download_button(
        "Download Project Backup",
        data=backup_bytes,
        file_name=safe_project_filename(current_metadata.get("project_name", "analytics_project")),
        mime="application/zip",
    )

st.caption(
    "Project Backup stores workflow details, mappings and available working context for continuing later. "
    "Use the BI-ready Export Package when you want to share analysis outputs."
)
