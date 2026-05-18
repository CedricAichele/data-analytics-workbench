"""Shared Streamlit layout helpers."""

from __future__ import annotations

import streamlit as st

from app.config import APP_SUBTITLE, APP_TITLE, LOGO_PATH


def configure_page(title: str) -> None:
    page_title_text = APP_TITLE if title == APP_TITLE else f"{title} | {APP_TITLE}"
    st.set_page_config(page_title=page_title_text, layout="wide")
    render_sidebar_branding()
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.85rem 1rem;
        }
        .small-muted {color: #64748b; font-size: 0.9rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_branding() -> None:
    """Render consistent app branding in the sidebar."""
    if LOGO_PATH.exists():
        if hasattr(st, "logo"):
            try:
                st.logo(str(LOGO_PATH))
                st.sidebar.title(APP_TITLE)
                st.sidebar.caption(APP_SUBTITLE)
                return
            except Exception:
                pass
        try:
            st.sidebar.image(str(LOGO_PATH), use_container_width=True)
        except TypeError:
            st.sidebar.image(str(LOGO_PATH), use_column_width=True)
        except Exception:
            pass
    st.sidebar.title(APP_TITLE)
    st.sidebar.caption(APP_SUBTITLE)


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
