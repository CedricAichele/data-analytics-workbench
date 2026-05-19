from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.services.dataset_workspace import set_active_analytics_result
from app.services.generic_analytics import (
    build_generic_analytics,
    create_long_chart_data,
    get_categorical_columns,
    get_date_columns,
    get_numeric_columns,
    is_chart_config_supported,
    validate_generic_selection,
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

measure_key = "generic_numeric_measures"
category_key = "generic_category_choice"
date_key = "generic_date_choice"
aggregation_key = "generic_aggregation"
chart_key = "generic_chart_type"

valid_existing_measures = [
    measure for measure in st.session_state.get(measure_key, [numeric_columns[0]]) if measure in numeric_columns
]
st.session_state[measure_key] = valid_existing_measures or [numeric_columns[0]]
for key, options, default in [
    (category_key, categorical_columns, "None"),
    (date_key, date_columns, "None"),
    (aggregation_key, ["sum", "average", "count", "min", "max"], "sum"),
    (chart_key, ["bar chart", "line chart", "area chart", "scatter plot", "histogram", "box plot"], "bar chart"),
]:
    if st.session_state.get(key, default) not in options:
        st.session_state[key] = default

controls = st.columns([1.4, 1, 1, 1, 1])
selected_measures = controls[0].multiselect(
    "Numeric measures",
    numeric_columns,
    key=measure_key,
)
category_choice = controls[1].selectbox("Group by category", categorical_columns, key=category_key)
date_choice = controls[2].selectbox("Group by date", date_columns, key=date_key)
aggregation = controls[3].selectbox("Aggregation", ["sum", "average", "count", "min", "max"], key=aggregation_key)
chart_type = controls[4].selectbox("Chart type", ["bar chart", "line chart", "area chart", "scatter plot", "histogram", "box plot"], key=chart_key)

if not selected_measures:
    set_active_analytics_result("generic_analytics_result", None)
    set_active_analytics_result("generic_controlled_chart_result", None)
    st.warning("Select at least one numeric measure.")
    st.stop()

category_column = None if category_choice == "None" else category_choice
date_column = None if date_choice == "None" else date_choice
validation = validate_generic_selection(df, selected_measures, category_column, date_column)
if not validation.valid:
    set_active_analytics_result("generic_analytics_result", None)
    set_active_analytics_result("generic_controlled_chart_result", None)
    st.warning("The selected chart configuration is not valid for the current dataset.")
    for message in validation.messages:
        st.write(f"- {message}")
    st.stop()

try:
    result = build_generic_analytics(
        df,
        numeric_columns=validation.measures,
        aggregation=aggregation,
        category_column=validation.category_column,
        date_column=validation.date_column,
    )
except Exception as exc:
    set_active_analytics_result("generic_analytics_result", None)
    set_active_analytics_result("generic_controlled_chart_result", None)
    st.error(f"Generic analytics could not be calculated: {exc}")
    st.stop()

set_active_analytics_result("generic_analytics_result", result)
set_active_analytics_result(
    "generic_controlled_chart_result",
    {"aggregated_result": result.aggregated},
)

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
fig = None
chart_export_tables = {"aggregated_result": result.aggregated}

supported, support_messages = is_chart_config_supported(
    chart_type,
    validation.measures,
    validation.category_column,
    validation.date_column,
)
if not supported:
    st.warning("The selected chart configuration is not valid for the current dataset.")
    for message in support_messages:
        st.write(f"- {message}")
    set_active_analytics_result("generic_controlled_chart_result", chart_export_tables)
    st.stop()

if chart_type in {"histogram", "box plot"}:
    long_source = (
        df[validation.measures]
        .apply(pd.to_numeric, errors="coerce")
        .melt(var_name="measure", value_name="metric_value")
        .dropna(subset=["metric_value"])
    )
    chart_export_tables["chart_data"] = long_source
    if chart_type == "histogram":
        fig = px.histogram(long_source, x="metric_value", color="measure", nbins=40, barmode="overlay", title="Distribution of Selected Measures")
    else:
        fig = px.box(long_source, x="measure", y="metric_value", title="Box Plot of Selected Measures")
elif chart_type == "scatter plot":
    scatter_source = df[validation.measures[:2]].apply(pd.to_numeric, errors="coerce").dropna()
    if scatter_source.empty:
        st.warning("The selected chart configuration is not valid for the current dataset.")
        st.write("- No rows remain after parsing the selected scatter measures.")
    else:
        chart_export_tables["chart_data"] = scatter_source
        fig = px.scatter(scatter_source, x=validation.measures[0], y=validation.measures[1], title=f"{validation.measures[0]} vs {validation.measures[1]}")
else:
    if not measure_cols:
        st.warning("No aggregated measure columns are available for this chart.")
    id_vars = [column for column in ["period", validation.category_column, "metric", "rows"] if column]
    long_result = create_long_chart_data(chart_data, id_vars, measure_cols)
    for message in long_result.messages:
        st.caption(message)
    long_chart = long_result.data
    if long_chart.empty:
        st.warning("The selected chart configuration is not valid for the current dataset.")
    elif "period" in long_chart.columns:
        x_col = "period"
    elif validation.category_column and validation.category_column in long_chart.columns:
        x_col = validation.category_column
    elif "metric" in long_chart.columns:
        x_col = "metric"
    else:
        long_chart = long_chart.reset_index(names="row_index")
        x_col = "row_index"

    if not long_chart.empty:
        chart_export_tables["chart_data"] = long_chart
        if chart_type == "line chart":
            fig = px.line(long_chart, x=x_col, y=long_result.value_column, color="measure", markers=True)
        elif chart_type == "area chart":
            fig = px.area(long_chart, x=x_col, y=long_result.value_column, color="measure")
        else:
            fig = px.bar(long_chart, x=x_col, y=long_result.value_column, color="measure", barmode="group")

set_active_analytics_result("generic_controlled_chart_result", chart_export_tables)

if fig is not None:
    fig.update_layout(height=460)
    st.plotly_chart(fig, use_container_width=True)
