from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.services.dataset_workspace import set_active_analytics_result
from app.services.generic_analytics import (
    build_generic_analytics,
    get_categorical_columns,
    get_date_columns,
    get_numeric_columns,
)


configure_page("Generic Analytics")
page_title("Generic Analytics", "Exploratory multi-measure aggregation for any supported tabular dataset.")

df = get_working_dataframe()
if df is None:
    st.stop()

st.info(
    "This page does not assume sales, finance, logistics, or manufacturing meaning. "
    "It works with the active working dataframe and preserves all columns."
)

numeric_columns = get_numeric_columns(df)
if not numeric_columns:
    st.warning("No numeric columns were detected. Use Data Preparation to convert a column to numeric if needed.")
    st.stop()

categorical_columns = ["None"] + get_categorical_columns(df)
date_columns = ["None"] + get_date_columns(df)

controls = st.columns([1.4, 1, 1, 1, 1])
selected_measures = controls[0].multiselect(
    "Numeric measures",
    numeric_columns,
    default=[numeric_columns[0]],
)
category_choice = controls[1].selectbox("Group by category", categorical_columns)
date_choice = controls[2].selectbox("Group by date", date_columns)
aggregation = controls[3].selectbox("Aggregation", ["sum", "average", "count", "min", "max"])
chart_type = controls[4].selectbox("Chart type", ["bar chart", "line chart", "scatter plot", "histogram", "box plot"])

if not selected_measures:
    st.warning("Select at least one numeric measure.")
    st.stop()

category_column = None if category_choice == "None" else category_choice
date_column = None if date_choice == "None" else date_choice

try:
    result = build_generic_analytics(
        df,
        numeric_columns=selected_measures,
        aggregation=aggregation,
        category_column=category_column,
        date_column=date_column,
    )
except Exception as exc:
    st.error(f"Generic analytics could not be calculated: {exc}")
    st.stop()

set_active_analytics_result("generic_analytics_result", result)

st.subheader("Basic Insights")
for insight in result.insights:
    st.write(f"- {insight}")

st.subheader("Aggregated Result")
st.dataframe(result.aggregated, use_container_width=True, hide_index=True)

csv_bytes = result.aggregated.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download aggregated result as CSV",
    data=csv_bytes,
    file_name="generic_analytics_result.csv",
    mime="text/csv",
)

st.subheader("Chart")
chart_data = result.aggregated.copy()
measure_cols = [column for column in result.measure_columns if column in chart_data.columns]

if chart_type in {"histogram", "box plot"}:
    long_source = (
        df[selected_measures]
        .apply(pd.to_numeric, errors="coerce")
        .melt(var_name="measure", value_name="value")
        .dropna(subset=["value"])
    )
    if chart_type == "histogram":
        fig = px.histogram(long_source, x="value", color="measure", nbins=40, barmode="overlay", title="Distribution of Selected Measures")
    else:
        fig = px.box(long_source, x="measure", y="value", title="Box Plot of Selected Measures")
elif chart_type == "scatter plot":
    if len(selected_measures) < 2:
        st.info("Scatter plot works best with at least two measures. Showing aggregated value by selected grouping instead.")
        y_col = "value" if "value" in chart_data.columns else measure_cols[0]
        x_col = "period" if "period" in chart_data.columns else category_column if category_column and category_column in chart_data.columns else "rows"
        fig = px.scatter(chart_data, x=x_col, y=y_col)
    else:
        scatter_source = df[selected_measures[:2]].apply(pd.to_numeric, errors="coerce").dropna()
        fig = px.scatter(scatter_source, x=selected_measures[0], y=selected_measures[1], title=f"{selected_measures[0]} vs {selected_measures[1]}")
else:
    if not measure_cols:
        st.warning("No aggregated measure columns are available for this chart.")
        st.stop()
    id_vars = [column for column in ["period", category_column, "metric", "rows"] if column and column in chart_data.columns]
    long_chart = chart_data.melt(id_vars=id_vars, value_vars=measure_cols, var_name="measure", value_name="value")
    if "period" in long_chart.columns:
        x_col = "period"
    elif category_column and category_column in long_chart.columns:
        x_col = category_column
    elif "metric" in long_chart.columns:
        x_col = "metric"
    else:
        long_chart = long_chart.reset_index(names="row_index")
        x_col = "row_index"

    if chart_type == "line chart":
        fig = px.line(long_chart, x=x_col, y="value", color="measure", markers=True)
    else:
        fig = px.bar(long_chart, x=x_col, y="value", color="measure", barmode="group")

fig.update_layout(height=460)
st.plotly_chart(fig, use_container_width=True)
