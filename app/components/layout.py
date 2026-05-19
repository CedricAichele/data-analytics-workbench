"""Shared Streamlit layout helpers."""

from __future__ import annotations

import base64
from dataclasses import dataclass

import streamlit as st

from app.config import APP_SUBTITLE, APP_TITLE, LOGO_MARK_PATH
from app.services.dataset_workspace import (
    clear_all_datasets,
    get_active_dataset,
    get_active_dataset_summary,
    get_active_working_df,
    initialize_workspace,
    list_datasets,
    remove_dataset,
    reset_active_working_dataset,
    set_active_dataset,
    sync_legacy_state,
)
from app.services.project_state import (
    get_active_project,
    initialize_project_state,
    list_projects,
    set_active_project,
)


@dataclass(frozen=True)
class NavItem:
    label: str
    page: str
    icon: str


NAV_GROUPS = {
    "Core": [
        NavItem("Overview", "main.py", ":material/home:"),
        NavItem("Project Setup", "pages/project_setup.py", ":material/workspace_premium:"),
        NavItem("Workflow", "pages/workflow.py", ":material/checklist:"),
    ],
    "Data": [
        NavItem("Data Upload", "pages/1_data_upload.py", ":material/upload_file:"),
        NavItem("Data Profile", "pages/2_data_profile.py", ":material/table_view:"),
        NavItem("Data Preparation", "pages/3_data_preparation.py", ":material/tune:"),
        NavItem("Data Dictionary", "pages/data_dictionary.py", ":material/menu_book:"),
        NavItem("Data Quality", "pages/5_data_quality.py", ":material/verified_user:"),
    ],
    "Analytics": [
        NavItem("Analytics Hub", "pages/analytics_hub.py", ":material/query_stats:"),
    ],
    "Results": [
        NavItem("Management Summary", "pages/6_management_summary.py", ":material/description:"),
        NavItem("Export Center", "pages/export_center.py", ":material/download:"),
    ],
}


def configure_page(title: str) -> None:
    page_title_text = APP_TITLE if title == APP_TITLE else f"{title} | {APP_TITLE}"
    st.set_page_config(page_title=page_title_text, layout="wide")
    inject_layout_css()
    render_sidebar_branding()


def inject_layout_css() -> None:
    """Load shared CSS before any custom sidebar or page content is rendered."""
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        div[data-testid="stSidebarNav"] {display: none;}
        .daw-logo-wrap {
            display: flex;
            justify-content: center;
            padding: 0.15rem 0 0.15rem;
            width: 100%;
        }
        .daw-logo-wrap img {
            display: block;
            height: auto;
            max-width: 74px;
            width: 74px;
        }
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.85rem 1rem;
        }
        .small-muted {color: #64748b; font-size: 0.9rem;}
        .daw-brand-title {
            color: #0f172a;
            font-size: 1.25rem;
            font-weight: 800;
            line-height: 1.15;
            margin-top: 0.15rem;
        }
        .daw-brand-subtitle {
            color: #475569;
            font-size: 0.78rem;
            font-weight: 500;
            line-height: 1.35;
            margin-bottom: 0.45rem;
        }
        .daw-sidebar-nav-title {
            color: #64748b;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin: 0.8rem 0 0.3rem;
            text-transform: uppercase;
        }
        .daw-sidebar-panel-title {
            color: #0f172a;
            font-size: 0.9rem;
            font-weight: 750;
            margin-top: 0.75rem;
        }
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            font-size: 0.92rem;
            font-weight: 650;
            margin-bottom: 0.35rem;
            min-height: 2.4rem;
        }
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
            background: #eff6ff;
            border-color: #bfdbfe;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_branding() -> None:
    """Render consistent app branding in the sidebar."""
    if LOGO_MARK_PATH.exists():
        try:
            encoded_logo = base64.b64encode(LOGO_MARK_PATH.read_bytes()).decode("ascii")
            st.sidebar.markdown(
                f'<div class="daw-logo-wrap"><img src="data:image/svg+xml;base64,{encoded_logo}" alt="{APP_TITLE} logo mark"></div>',
                unsafe_allow_html=True,
            )
        except Exception:
            pass
    st.sidebar.markdown(
        f"""
        <div class="daw-brand-title">{APP_TITLE}</div>
        <div class="daw-brand-subtitle">{APP_SUBTITLE}</div>
        """,
        unsafe_allow_html=True,
    )
    render_project_workspace_selector()
    render_dataset_workspace_selector()
    render_sidebar_navigation()


def render_project_workspace_selector() -> None:
    """Render compact active project status in the sidebar."""
    initialize_project_state()
    projects = list_projects()
    st.sidebar.markdown('<div class="daw-sidebar-panel-title">Active Project</div>', unsafe_allow_html=True)
    if not projects:
        st.sidebar.info("No active project. Create or load a project to document your workflow.")
        return

    active_project = get_active_project()
    project_ids = [project["project_id"] for project in projects]
    draft_option = "__new_project_draft__"
    options = project_ids if active_project else [draft_option, *project_ids]
    current_id = active_project["project_id"] if active_project else draft_option
    selected_id = st.sidebar.selectbox(
        "Active project",
        options,
        index=options.index(current_id) if current_id in options else 0,
        format_func=lambda project_id: "New project draft"
        if project_id == draft_option
        else next(project["project_name"] for project in projects if project["project_id"] == project_id),
        key="sidebar_active_project_selector",
    )
    if selected_id != current_id and selected_id != draft_option:
        set_active_project(selected_id)
        st.rerun()

    active_project = get_active_project()
    if active_project:
        metadata = active_project.get("metadata", {})
        st.sidebar.caption(
            f"Workflow: {metadata.get('selected_workflow', 'Quick Data Check')}  \n"
            f"Template: {metadata.get('suggested_template', 'Generic')}"
        )
    else:
        st.sidebar.caption("Create or save the draft on Project Setup.")


def render_dataset_workspace_selector() -> None:
    """Render active dataset selector in the sidebar."""
    initialize_workspace()
    feedback = st.session_state.pop("dataset_action_feedback", None)
    if feedback:
        feedback_type, feedback_message = feedback
        if feedback_type == "success":
            st.sidebar.success(feedback_message)
        else:
            st.sidebar.info(feedback_message)
    datasets = list_datasets()
    st.sidebar.markdown('<div class="daw-sidebar-panel-title">Active Dataset</div>', unsafe_allow_html=True)
    if not datasets:
        st.sidebar.info("No active dataset.")
        return
    active = get_active_dataset()
    dataset_ids = [dataset["dataset_id"] for dataset in datasets]
    current_id = active["dataset_id"] if active else dataset_ids[0]
    selected_id = st.sidebar.selectbox(
        "Active dataset",
        dataset_ids,
        index=dataset_ids.index(current_id) if current_id in dataset_ids else 0,
        format_func=lambda dataset_id: next(dataset["name"] for dataset in datasets if dataset["dataset_id"] == dataset_id),
        key="sidebar_active_dataset_selector",
    )
    if selected_id != current_id:
        set_active_dataset(selected_id)
        st.rerun()
    active = get_active_dataset()
    if active:
        metadata = active.get("metadata", {})
        st.sidebar.caption(
            f"{metadata.get('source', 'dataset')} | {metadata.get('file_type', 'data')} | "
            f"{len(active['working_df']):,} rows x {len(active['working_df'].columns):,} cols"
        )
        summary = get_active_dataset_summary()
        if summary.get("is_large_dataset"):
            st.sidebar.warning("Large dataset: some operations may take longer.")
        with st.sidebar.expander("Dataset actions", expanded=False):
            if st.button("Reset working dataset", key="sidebar-reset-active-dataset"):
                reset_active_working_dataset()
                st.session_state["dataset_action_feedback"] = ("success", "Working dataset reset to raw data.")
                st.rerun()
            if st.button("Remove active dataset", key="sidebar-remove-active-dataset"):
                remove_dataset(active["dataset_id"])
                st.session_state["dataset_action_feedback"] = ("success", "Active dataset removed.")
                st.rerun()
            confirm_clear_all = st.checkbox("Confirm clear all datasets", key="sidebar-confirm-clear-all-datasets")
            if st.button("Clear all datasets", key="sidebar-clear-all-datasets", disabled=not confirm_clear_all):
                clear_all_datasets()
                st.session_state["dataset_action_feedback"] = ("success", "All datasets cleared. Active project was kept.")
                st.rerun()


def render_sidebar_navigation() -> None:
    """Render a stable custom navigation menu with professional icons."""
    for group, items in NAV_GROUPS.items():
        st.sidebar.markdown(f'<div class="daw-sidebar-nav-title">{group}</div>', unsafe_allow_html=True)
        for item in items:
            try:
                st.sidebar.page_link(item.page, label=item.label, icon=item.icon)
            except Exception:
                st.sidebar.page_link(item.page, label=item.label)


def render_process_steps(steps: list[dict[str, str]]) -> None:
    """Render workflow steps in a readable two-column process layout."""
    for index, step in enumerate(steps, start=1):
        with st.container(border=True):
            cols = st.columns([0.12, 0.28, 0.18, 0.42])
            cols[0].metric("Step", str(index))
            cols[1].markdown(f"**{step['step']}**")
            cols[1].caption(step["status"])
            cols[2].write(step["explanation"])
            with cols[3]:
                st.caption(step["recommended_next_action"])
                try:
                    st.page_link(step["page"], label="Open page", icon=":material/arrow_forward:")
                except Exception:
                    st.caption("Use the sidebar to open this page.")


def page_title(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def ensure_working_dataframe() -> bool:
    """Ensure working_df exists when raw_df is loaded."""
    initialize_workspace()
    active_dataset = get_active_dataset()
    if active_dataset is None:
        st.warning("Load a CSV, XLSX, JSON, or the bundled sample dataset first from the Data Upload page.")
        return False
    sync_legacy_state()
    return True


def require_dataframe() -> bool:
    return ensure_working_dataframe()


def get_working_dataframe():
    if not ensure_working_dataframe():
        return None
    return get_active_working_df()


def dataframe_status() -> None:
    initialize_workspace()
    active = get_active_dataset()
    if active is None:
        st.info("No dataset is loaded yet.")
        return
    raw_df = active["raw_df"]
    working_df = active["working_df"]
    st.success(
        f"Active dataset: {active.get('name', 'Unnamed dataset')} "
        f"| raw: {len(raw_df):,} rows, {len(raw_df.columns):,} columns "
        f"| working: {len(working_df):,} rows, {len(working_df.columns):,} columns"
    )
