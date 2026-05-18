from __future__ import annotations

import streamlit as st

from app.components.charts import (
    categorical_frequency_chart,
    dtype_distribution_chart,
    missing_values_chart,
    numeric_distribution_chart,
)
from app.components.layout import configure_page, get_working_dataframe, page_title
from app.components.kpi_cards import render_kpi_grid
from app.services.profiler import profile_dataframe
from app.services.quality_score import calculate_quality_score


configure_page("Data Profile")
page_title("Generic Data Profiler", "Inspect the current working dataset before or after preparation.")

df = get_working_dataframe()
if df is None:
    st.stop()
profile = profile_dataframe(df)
quality = calculate_quality_score(df)

render_kpi_grid(
    [
        ("Rows", f"{profile.row_count:,}", None),
        ("Columns", f"{profile.column_count:,}", None),
        ("Duplicate rows", f"{profile.duplicate_row_count:,}", None),
        ("Quality score", f"{quality.overall_score:.1f}/100", "Generic score before domain schema validation."),
    ]
)

st.subheader("Quality Score")
st.progress(quality.overall_score / 100)
st.dataframe(
    [{"dimension": key.replace("_", " ").title(), "score": value} for key, value in quality.sub_scores.items()],
    use_container_width=True,
    hide_index=True,
)
with st.expander("Quality explanations and recommended fixes"):
    st.write("Explanations")
    for explanation in quality.explanations:
        st.write(f"- {explanation}")
    st.write("Recommended fixes")
    for fix in quality.recommended_fixes:
        st.write(f"- {fix}")

st.subheader("Column Overview")
tabs = st.tabs(["Types and Missingness", "Unique Values", "Numeric Summary", "Categorical Summary", "Detected Column Groups"])

with tabs[0]:
    left, right = st.columns(2)
    with left:
        st.dataframe(profile.dtype_table, use_container_width=True, hide_index=True)
    with right:
        st.dataframe(profile.missing_table, use_container_width=True, hide_index=True)

with tabs[1]:
    st.dataframe(profile.unique_table, use_container_width=True, hide_index=True)

with tabs[2]:
    st.dataframe(profile.numeric_summary, use_container_width=True, hide_index=True)

with tabs[3]:
    st.dataframe(profile.categorical_summary, use_container_width=True, hide_index=True)

with tabs[4]:
    col1, col2, col3 = st.columns(3)
    col1.write("Date-like columns")
    col1.dataframe([{"column": c} for c in profile.detected_date_columns], hide_index=True, use_container_width=True)
    col2.write("Numeric columns")
    col2.dataframe([{"column": c} for c in profile.detected_numeric_columns], hide_index=True, use_container_width=True)
    col3.write("Categorical columns")
    col3.dataframe([{"column": c} for c in profile.detected_categorical_columns], hide_index=True, use_container_width=True)

st.subheader("Visual Profile")
chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.plotly_chart(missing_values_chart(profile.missing_table), use_container_width=True)
with chart_col2:
    st.plotly_chart(dtype_distribution_chart(profile.data_type_distribution), use_container_width=True)

chart_col3, chart_col4 = st.columns(2)
with chart_col3:
    if profile.detected_numeric_columns:
        selected_numeric = st.selectbox("Numeric column", profile.detected_numeric_columns)
        st.plotly_chart(numeric_distribution_chart(df, selected_numeric), use_container_width=True)
    else:
        st.info("No numeric columns were detected.")
with chart_col4:
    if profile.detected_categorical_columns:
        selected_category = st.selectbox("Categorical column", profile.detected_categorical_columns)
        st.plotly_chart(categorical_frequency_chart(df, selected_category), use_container_width=True)
    else:
        st.info("No categorical columns were detected.")
