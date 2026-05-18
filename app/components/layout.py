"""Shared Streamlit layout helpers."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app.config import APP_SUBTITLE, APP_TITLE, LOGO_MARK_PATH
from app.services.dataset_workspace import (
    get_active_dataset,
    get_active_working_df,
    initialize_workspace,
    list_datasets,
    set_active_dataset,
    sync_legacy_state,
)


@dataclass(frozen=True)
class NavItem:
    label: str
    page: str
    icon: str


NAV_ITEMS = [
    NavItem("Overview", "main.py", ":material/home:"),
    NavItem("Data Upload", "pages/1_data_upload.py", ":material/upload_file:"),
    NavItem("Data Profile", "pages/2_data_profile.py", ":material/table_view:"),
    NavItem("Data Preparation", "pages/3_data_preparation.py", ":material/tune:"),
    NavItem("Data Quality", "pages/5_data_quality.py", ":material/verified_user:"),
    NavItem("Generic Analytics", "pages/6_generic_analytics.py", ":material/query_stats:"),
    NavItem("Template Selection", "pages/7_template_selection.py", ":material/layers:"),
    NavItem("Column Mapping", "pages/4_column_mapping.py", ":material/link:"),
    NavItem("Sales Analytics", "pages/5_retail_analytics.py", ":material/bar_chart:"),
    NavItem("Manufacturing Analytics", "pages/8_manufacturing_analytics.py", ":material/factory:"),
    NavItem("Logistics Analytics", "pages/9_logistics_analytics.py", ":material/local_shipping:"),
    NavItem("Finance Analytics", "pages/10_finance_analytics.py", ":material/account_balance_wallet:"),
    NavItem("Management Summary", "pages/6_management_summary.py", ":material/description:"),
    NavItem("Export Center", "pages/export_center.py", ":material/download:"),
]


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
            margin-top: 0.35rem;
        }
        .daw-brand-subtitle {
            color: #475569;
            font-size: 0.78rem;
            font-weight: 500;
            line-height: 1.35;
            margin-bottom: 0.8rem;
        }
        .daw-sidebar-nav-title {
            color: #64748b;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin: 1rem 0 0.35rem;
            text-transform: uppercase;
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
            st.sidebar.image(str(LOGO_MARK_PATH), width=104)
        except TypeError:
            st.sidebar.image(str(LOGO_MARK_PATH), width=104)
        except Exception:
            pass
    st.sidebar.markdown(
        f"""
        <div class="daw-brand-title">{APP_TITLE}</div>
        <div class="daw-brand-subtitle">{APP_SUBTITLE}</div>
        """,
        unsafe_allow_html=True,
    )
    render_dataset_workspace_selector()
    render_sidebar_navigation()


def render_dataset_workspace_selector() -> None:
    """Render active dataset selector in the sidebar."""
    initialize_workspace()
    datasets = list_datasets()
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


def render_sidebar_navigation() -> None:
    """Render a stable custom navigation menu with professional icons."""
    st.sidebar.markdown('<div class="daw-sidebar-nav-title">Navigation</div>', unsafe_allow_html=True)
    for item in NAV_ITEMS:
        try:
            st.sidebar.page_link(item.page, label=item.label, icon=item.icon)
        except Exception:
            st.sidebar.page_link(item.page, label=item.label)


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
