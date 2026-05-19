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
    add_or_activate_project,
    associate_dataset_with_active_project,
    compact_project_summary_rows,
    create_project,
    get_active_project,
    get_project_metadata,
    get_project_summary,
    initialize_project_state,
    list_projects,
    set_active_project,
    update_active_project,
)
from app.services.quality_score import calculate_quality_score


configure_page("Project Setup")
page_title("Project Setup", "Define the business context for this analytics project.")

initialize_project_state()
project_feedback = st.session_state.pop("project_action_feedback", None)
if project_feedback:
    feedback_type, feedback_message = project_feedback
    if feedback_type == "success":
        st.success(feedback_message)
    elif feedback_type == "info":
        st.info(feedback_message)
    else:
        st.warning(feedback_message)

metadata = get_project_metadata()
active = get_active_dataset()
active_project = get_active_project()

st.info(
    "Create a lightweight project first, or load data first and document the project later. "
    "Project details help make exports and handoffs easier to understand."
)

projects = list_projects()
st.subheader("Current Active Project")
if active_project:
    active_metadata = active_project.get("metadata", {})
    st.success(f"Active project: {active_metadata.get('project_name', 'Untitled project')}")
    project_status_cols = st.columns(3)
    project_status_cols[0].metric("Workflow", active_metadata.get("selected_workflow", "Quick Data Check"))
    project_status_cols[1].metric("Template", active_metadata.get("suggested_template", "Generic"))
    project_status_cols[2].metric("Loaded projects", len(projects))
else:
    st.info("No active project. Create or load a project to document your workflow.")

if projects:
    st.subheader("Switch Project")
    st.caption(f"{len(projects)} project{'s' if len(projects) != 1 else ''} loaded in this session. The app uses one active project at a time.")
    project_options = [project["project_id"] for project in projects]
    active_project_id = active_project["project_id"] if active_project else project_options[0]
    selected_project_id = st.selectbox(
        "Choose active project",
        project_options,
        index=project_options.index(active_project_id) if active_project_id in project_options else 0,
        format_func=lambda project_id: next(project["project_name"] for project in projects if project["project_id"] == project_id),
    )
    if selected_project_id != active_project_id:
        selected_name = next(project["project_name"] for project in projects if project["project_id"] == selected_project_id)
        set_active_project(selected_project_id)
        st.session_state["project_action_feedback"] = ("success", f"Switched to project: {selected_name}")
        st.rerun()

st.subheader("Create New Project")
with st.form("create_project_form"):
    project_name = st.text_input("Project name", value="", key="create_project_name")
    project_description = st.text_area("Project description", value="", height=90, key="create_project_description")
    analysis_goal = st.text_area("Analysis goal", value="", height=90, key="create_analysis_goal")
    optional_cols = st.columns(3)
    company_department = optional_cols[0].text_input("Company / department", value="", key="create_company_department")
    data_owner = optional_cols[1].text_input("Data owner or responsible person", value="", key="create_data_owner")
    reporting_period = optional_cols[2].text_input("Reporting period", value="", key="create_reporting_period")
    workflow_cols = st.columns(3)
    selected_workflow = workflow_cols[0].selectbox(
        "Workflow",
        WORKFLOW_OPTIONS,
        index=0,
        key="create_selected_workflow",
    )
    suggested_template = workflow_cols[1].selectbox(
        "Suggested domain template",
        TEMPLATE_OPTIONS,
        index=0,
        key="create_suggested_template",
    )
    desired_outputs = workflow_cols[2].multiselect(
        "Desired output",
        OUTPUT_OPTIONS,
        default=["Data Quality Report", "Data Dictionary"],
        key="create_desired_outputs",
    )
    notes = st.text_area("Notes", value="", height=90, key="create_notes")
    create_submitted = st.form_submit_button("Create New Project")

if create_submitted:
    if not project_name.strip() or not project_description.strip() or not analysis_goal.strip():
        st.warning("Project name, project description, and analysis goal are required to create a project.")
        st.stop()
    project_id, created = create_project(
        {
            "project_name": project_name.strip(),
            "project_description": project_description.strip(),
            "analysis_goal": analysis_goal.strip(),
            "company_department": company_department.strip(),
            "data_owner": data_owner.strip(),
            "reporting_period": reporting_period.strip(),
            "selected_workflow": selected_workflow,
            "suggested_template": suggested_template,
            "desired_outputs": desired_outputs,
            "notes": notes.strip(),
        }
    )
    if active is not None:
        associate_dataset_with_active_project(active["dataset_id"])
    created_metadata = get_project_metadata()
    if created:
        st.session_state["project_action_feedback"] = ("success", f"Project created and activated: {created_metadata.get('project_name', project_name.strip())}")
    else:
        st.session_state["project_action_feedback"] = ("info", "Project already loaded. Activated existing project.")
    st.rerun()

st.subheader("Update Active Project")
if not active_project:
    st.info("Create or switch to a project before updating project details.")
else:
    active_metadata = get_project_metadata()
    with st.form("update_active_project_form"):
        update_project_name = st.text_input("Project name", value=active_metadata.get("project_name", ""), key="update_project_name")
        update_project_description = st.text_area("Project description", value=active_metadata.get("project_description", ""), height=90, key="update_project_description")
        update_analysis_goal = st.text_area("Analysis goal", value=active_metadata.get("analysis_goal", ""), height=90, key="update_analysis_goal")
        update_optional_cols = st.columns(3)
        update_company_department = update_optional_cols[0].text_input("Company / department", value=active_metadata.get("company_department", ""), key="update_company_department")
        update_data_owner = update_optional_cols[1].text_input("Data owner or responsible person", value=active_metadata.get("data_owner", ""), key="update_data_owner")
        update_reporting_period = update_optional_cols[2].text_input("Reporting period", value=active_metadata.get("reporting_period", ""), key="update_reporting_period")
        update_workflow_cols = st.columns(3)
        update_selected_workflow = update_workflow_cols[0].selectbox(
            "Workflow",
            WORKFLOW_OPTIONS,
            index=WORKFLOW_OPTIONS.index(active_metadata.get("selected_workflow", "Quick Data Check"))
            if active_metadata.get("selected_workflow") in WORKFLOW_OPTIONS
            else 0,
            key="update_selected_workflow",
        )
        update_suggested_template = update_workflow_cols[1].selectbox(
            "Suggested domain template",
            TEMPLATE_OPTIONS,
            index=TEMPLATE_OPTIONS.index(active_metadata.get("suggested_template", "Generic"))
            if active_metadata.get("suggested_template") in TEMPLATE_OPTIONS
            else 0,
            key="update_suggested_template",
        )
        update_desired_outputs = update_workflow_cols[2].multiselect(
            "Desired output",
            OUTPUT_OPTIONS,
            default=[output for output in active_metadata.get("desired_outputs", []) if output in OUTPUT_OPTIONS] or ["Data Quality Report"],
            key="update_desired_outputs",
        )
        update_notes = st.text_area("Notes", value=active_metadata.get("notes", ""), height=90, key="update_notes")
        update_submitted = st.form_submit_button("Update Active Project")

    if update_submitted:
        if not update_project_name.strip() or not update_project_description.strip() or not update_analysis_goal.strip():
            st.warning("Project name, project description, and analysis goal are required to update a project.")
            st.stop()
        updated_metadata = update_active_project(
            project_name=update_project_name.strip(),
            project_description=update_project_description.strip(),
            analysis_goal=update_analysis_goal.strip(),
            company_department=update_company_department.strip(),
            data_owner=update_data_owner.strip(),
            reporting_period=update_reporting_period.strip(),
            selected_workflow=update_selected_workflow,
            suggested_template=update_suggested_template,
            desired_outputs=update_desired_outputs,
            notes=update_notes.strip(),
        )
        if active is not None:
            associate_dataset_with_active_project(active["dataset_id"])
        st.session_state["project_action_feedback"] = ("success", f"Active project updated: {updated_metadata.get('project_name', 'Analytics Project')}")
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
        project_id, created = add_or_activate_project(loaded.project_metadata, backup_hash=loaded.backup_hash)
        if loaded.cleaned_dataset is not None:
            restored_metadata = dict(loaded.dataset_metadata or {})
            restored_metadata.update({"source": "project backup", "file_type": "csv"})
            dataset_id, _ = add_or_activate_dataset(
                loaded.project_metadata.get("project_name", "Restored project dataset"),
                loaded.cleaned_dataset,
                restored_metadata,
            )
            associate_dataset_with_active_project(dataset_id)
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
        if created:
            st.success(f"Project Backup loaded: {loaded.project_metadata.get('project_name', 'Analytics Project')}")
        else:
            st.info("Project already loaded. Activated existing project.")
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
