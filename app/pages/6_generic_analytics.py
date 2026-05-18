from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.services.generic_analytics import (
    build_generic_analytics,
    get_categorical_columns,
    get_date_columns,
    get_numeric_columns,
)


configure_page("Generic Analytics")
page_title("Generic Analytics", "Exploratory aggregation for any supported tabular dataset.")

df = get_working_dataframe()
if df is None:
    st.stop()

st.info(
    "This page does not assume sales, finance, logistics, or manufacturing meaning. "
    "It works with the current working dataframe and preserves all columns."
)

numeric_columns = get_numeric_columns(df)
if not numeric_columns:
    st.warning("No numeric columns were detected. Use Data Preparation to convert a column to numeric if needed.")
    st.stop()

categorical_columns = ["None"] + get_categorical_columns(df)
date_columns = ["None"] + get_date_columns(df)

controls = st.columns(5)
numeric_column = controls[0].selectbox("Numeric measure", numeric_columns)
category_choice = controls[1].selectbox("Group by category", categorical_columns)
date_choice = controls[2].selectbox("Group by date", date_columns)
aggregation = controls[3].selectbox("Aggregation", ["sum", "average", "count", "min", "max"])
chart_type = controls[4].selectbox("Chart type", ["bar chart", "line chart", "scatter plot", "histogram"])

category_column = None if category_choice == "None" else category_choice
date_column = None if date_choice == "None" else date_choice

try:
    result = build_generic_analytics(
        df,
        numeric_column=numeric_column,
        aggregation=aggregation,
        category_column=category_column,
        date_column=date_column,
    )
except Exception as exc:
    st.error(f"Generic analytics could not be calculated: {exc}")
    st.stop()

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
if chart_type == "histogram":
    source = pd.to_numeric(df[numeric_column], errors="coerce").dropna().to_frame(name=numeric_column)
    fig = px.histogram(source, x=numeric_column, nbins=40, title=f"Distribution of {numeric_column}")
elif chart_type == "scatter plot":
    if "period" in chart_data.columns:
        x_col = "period"
    elif category_column and category_column in chart_data.columns:
        x_col = category_column
    else:
        chart_data = chart_data.reset_index(names="row_index")
        x_col = "row_index"
    fig = px.scatter(chart_data, x=x_col, y="value", color=category_column if category_column in chart_data.columns else None)
elif chart_type == "line chart":
    if "period" in chart_data.columns:
        fig = px.line(chart_data, x="period", y="value", color=category_column if category_column in chart_data.columns else None, markers=True)
    elif category_column and category_column in chart_data.columns:
        fig = px.line(chart_data, x=category_column, y="value", markers=True)
    else:
        chart_data = chart_data.reset_index(names="row_index")
        fig = px.line(chart_data, x="row_index", y="value", markers=True)
else:
    if category_column and category_column in chart_data.columns:
        fig = px.bar(chart_data, x=category_column, y="value", color="period" if "period" in chart_data.columns else None)
    elif "period" in chart_data.columns:
        fig = px.bar(chart_data, x="period", y="value")
    else:
        fig = px.bar(chart_data, x="metric", y="value")

fig.update_layout(height=460)
st.plotly_chart(fig, use_container_width=True)
