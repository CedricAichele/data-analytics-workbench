"""KPI card rendering helpers."""

from __future__ import annotations

import streamlit as st


def format_currency(value: float) -> str:
    return f"${value:,.0f}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def format_percent(value: float) -> str:
    return f"{value:.1%}"


def render_kpi_grid(items: list[tuple[str, str, str | None]], columns: int = 4) -> None:
    """Render KPI metrics in a responsive Streamlit grid."""
    for start in range(0, len(items), columns):
        cols = st.columns(columns)
        for col, item in zip(cols, items[start : start + columns]):
            label, value, help_text = item
            col.metric(label, value, help=help_text)

