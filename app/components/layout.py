"""Shared Streamlit layout helpers."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app.config import APP_SUBTITLE, APP_TITLE, LOGO_PATH


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
]


def configure_page(title: str) -> None:
    page_title_text = APP_TITLE if title == APP_TITLE else f"{title} | {APP_TITLE}"
    st.set_page_config(page_title=page_title_text, layout="wide")
    render_sidebar_branding()
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
    if LOGO_PATH.exists():
        try:
            st.sidebar.image(str(LOGO_PATH), use_container_width=True)
        except TypeError:
            st.sidebar.image(str(LOGO_PATH), use_column_width=True)
        except Exception:
            st.sidebar.title(APP_TITLE)
    else:
        st.sidebar.title(APP_TITLE)
    st.sidebar.caption(APP_SUBTITLE)
    render_sidebar_navigation()


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
    if "raw_df" not in st.session_state:
        st.warning("Load a CSV, XLSX, JSON, or the bundled sample dataset first from the Data Upload page.")
        return False
    if "working_df" not in st.session_state:
        st.session_state["working_df"] = st.session_state["raw_df"].copy()
    if "transformation_log" not in st.session_state:
        st.session_state["transformation_log"] = []
    return True


def require_dataframe() -> bool:
    return ensure_working_dataframe()


def get_working_dataframe():
    if not ensure_working_dataframe():
        return None
    return st.session_state["working_df"]


def dataframe_status() -> None:
    raw_df = st.session_state.get("raw_df")
    working_df = st.session_state.get("working_df")
    if raw_df is None:
        st.info("No dataset is loaded yet.")
        return
    if working_df is None:
        working_df = raw_df.copy()
        st.session_state["working_df"] = working_df
    st.success(
        f"Loaded dataset: {st.session_state.get('dataset_name', 'Unnamed dataset')} "
        f"| raw: {len(raw_df):,} rows, {len(raw_df.columns):,} columns "
        f"| working: {len(working_df):,} rows, {len(working_df.columns):,} columns"
    )
