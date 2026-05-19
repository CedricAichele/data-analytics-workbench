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
    get_active_project,
    get_project_metadata,
    get_project_summary,
    initialize_project_state,
    list_projects,
    set_active_project,
    start_new_project_draft,
    update_project_metadata,
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

st.info(
    "Create a lightweight project first, or load data first and document the project later. "
    "Project details help make exports and handoffs easier to understand."
)

projects = list_projects()
if projects:
    st.subheader("Project Workspace")
    st.caption(f"{len(projects)} project{'s' if len(projects) != 1 else ''} loaded in this session. The app uses one active project at a time.")
    active_project = get_active_project()
    draft_option = "__new_project_draft__"
    project_options = [project["project_id"] for project in projects]
    options = project_options if active_project else [draft_option, *project_options]
    active_project_id = active_project["project_id"] if active_project else draft_option
    selected_project_id = st.selectbox(
        "Active project",
        options,
        index=options.index(active_project_id),
        format_func=lambda project_id: "New project draft"
        if project_id == draft_option
        else next(project["project_name"] for project in projects if project["project_id"] == project_id),
    )
    if selected_project_id != active_project_id and selected_project_id != draft_option:
        set_active_project(selected_project_id)
        st.rerun()
    if st.button("Start new project"):
        start_new_project_draft()
        st.session_state["project_action_feedback"] = ("info", "New project form ready.")
        st.rerun()

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
    if not project_name.strip() or not project_description.strip() or not analysis_goal.strip():
        st.warning("Project name, project description, and analysis goal are required to save a project.")
        st.stop()
    saved_metadata = update_project_metadata(
        project_name=project_name.strip(),
        project_description=project_description.strip(),
        analysis_goal=analysis_goal.strip(),
        company_department=company_department.strip(),
        data_owner=data_owner.strip(),
        reporting_period=reporting_period.strip(),
        selected_workflow=selected_workflow,
        suggested_template=suggested_template,
        desired_outputs=desired_outputs,
        notes=notes.strip(),
    )
    if active is not None:
        associate_dataset_with_active_project(active["dataset_id"])
    st.session_state["project_action_feedback"] = ("success", f"Project saved: {saved_metadata.get('project_name', 'Analytics Project')}")
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
