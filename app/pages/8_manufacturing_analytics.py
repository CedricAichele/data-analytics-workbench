from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.kpi_cards import format_number, format_percent, render_kpi_grid
from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import MANUFACTURING_REQUIRED_FIELDS
from app.services.chart_controls import apply_date_range_filter, apply_value_filters, download_csv_bytes, top_n
from app.services.column_mapper import initialize_template_mapping, validate_template_mapping
from app.services.dataset_workspace import get_active_template_mapping, set_active_analytics_result
from app.services.manufacturing_analytics import build_manufacturing_analytics, clean_manufacturing_operations
from app.services.quality_score import calculate_quality_score
from app.services.schema_detector import detect_template_schema
from app.services.template_registry import get_template


configure_page("Manufacturing Analytics")
page_title("Manufacturing Analytics", "Production output, scrap, downtime, and machine performance KPIs.")

df = get_working_dataframe()
if df is None:
    st.stop()

template = get_template("manufacturing")
detection = detect_template_schema("manufacturing", list(df.columns))
template_mappings = st.session_state.get("template_mappings", {})
mapping = get_active_template_mapping("manufacturing") or st.session_state.get("manufacturing_mapping") or template_mappings.get("manufacturing")
if not mapping and not detection.requires_manual_mapping:
    mapping = initialize_template_mapping("manufacturing", list(df.columns), detection)
if not mapping:
    st.warning("The active dataset is not mapped to this analytics template.")
    st.write("Required fields")
    st.dataframe([{"field": field} for field in template.required_fields], use_container_width=True, hide_index=True)
    st.write("Detected and missing fields")
    st.dataframe(
        [{"field": field, "matched_column": detection.matched_fields.get(field), "status": "matched" if field in detection.matched_fields else "missing"} for field in template.required_fields],
        use_container_width=True,
        hide_index=True,
    )
    st.info("Go to Column Mapping, use Generic Analytics, or load the manufacturing sample dataset.")
    st.stop()

validation = validate_template_mapping("manufacturing", mapping, list(df.columns))
if not validation.is_valid:
    st.warning("The active dataset is not mapped to this analytics template.")
    for message in validation.messages:
        st.write(f"- {message}")
    st.info("Go to Column Mapping, use Generic Analytics, or load the manufacturing sample dataset.")
    st.stop()

quality = calculate_quality_score(
    df,
    mapping=mapping,
    required_fields=MANUFACTURING_REQUIRED_FIELDS,
    date_fields=["timestamp"],
    numeric_fields=["actual_output", "scrap_count", "downtime_minutes"],
)

try:
    clean_result = clean_manufacturing_operations(df, mapping)
    analytics = build_manufacturing_analytics(clean_result)
except Exception as exc:
    st.error(f"Manufacturing analytics could not be calculated: {exc}")
    st.stop()

set_active_analytics_result("manufacturing_clean_result", clean_result)
set_active_analytics_result("manufacturing_analytics_result", analytics)

metrics = analytics.metrics
st.subheader("Manufacturing KPIs")
render_kpi_grid(
    [
        ("Total output", format_number(metrics["total_output"] or 0), "Sum of valid actual output."),
        ("Total scrap", format_number(metrics["total_scrap"] or 0), "Sum of valid scrap count."),
        ("Scrap rate", format_percent(metrics["scrap_rate"] or 0), "Scrap divided by actual output."),
        ("Downtime minutes", format_number(metrics["total_downtime_minutes"] or 0), "Sum of valid downtime minutes."),
        ("Avg downtime / machine", format_number(metrics["average_downtime_per_machine"] or 0), None),
        ("Production attainment", format_percent(metrics["production_attainment"] or 0), "Actual output divided by planned output when planned output is available."),
        ("Availability approximation", format_percent(metrics["availability_approximation"] or 0), "Runtime divided by runtime plus downtime."),
        ("Quality rate approximation", format_percent(metrics["quality_rate_approximation"] or 0), "Actual output minus scrap divided by actual output."),
    ]
)
if metrics["simplified_oee_approximation"] is not None:
    st.metric(
        "Simplified OEE approximation",
        format_percent(metrics["simplified_oee_approximation"] or 0),
        help="Attainment x availability approximation x quality rate approximation. This is not a certified OEE standard.",
    )

with st.expander("Calculation notes"):
    st.write(
        "Analytics pages create temporary derived analytical columns internally, but they do not overwrite raw_df or working_df. "
        "Simplified OEE is shown only when planned output, runtime, downtime, output, and scrap inputs are available."
    )

st.subheader("Template Quality Score")
st.progress(quality.overall_score / 100)
st.dataframe(
    [{"dimension": key.replace("_", " ").title(), "score": value} for key, value in quality.sub_scores.items()],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Chart Controls")
controlled_ops = clean_result.analysis_rows.copy()
date_values = controlled_ops["timestamp"].dropna()
control_cols = st.columns([1, 1, 1, 1])
if not date_values.empty:
    selected_dates = control_cols[0].date_input(
        "Timestamp range",
        value=(date_values.min().date(), date_values.max().date()),
        min_value=date_values.min().date(),
        max_value=date_values.max().date(),
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        controlled_ops = apply_date_range_filter(controlled_ops, "timestamp", selected_dates[0], selected_dates[1])

measure_options = ["actual_output", "scrap_count", "downtime_minutes"]
if "planned_output" in controlled_ops.columns and controlled_ops["planned_output"].notna().any():
    measure_options.append("production_attainment")
measure_options.append("scrap_rate")
selected_measure = control_cols[1].selectbox("Measure", measure_options, format_func=lambda value: value.replace("_", " ").title())
trend_chart_type = control_cols[2].selectbox("Trend chart", ["line", "bar", "area"])
top_n_value = control_cols[3].slider("Top N machines", min_value=5, max_value=25, value=10, step=5)

filter_cols = st.columns(4)
filter_values: dict[str, list[object]] = {}
for col, field, label in [
    (filter_cols[0], "machine_id", "Machine"),
    (filter_cols[1], "line", "Line"),
    (filter_cols[2], "shift", "Shift"),
    (filter_cols[3], "product", "Product"),
]:
    if field in controlled_ops.columns and controlled_ops[field].dropna().nunique() > 0:
        options = sorted(controlled_ops[field].dropna().astype(str).unique().tolist())[:100]
        filter_values[field] = col.multiselect(label, options)
controlled_ops = apply_value_filters(controlled_ops, filter_values)

trend_source = controlled_ops.copy()
trend_source["period"] = trend_source["timestamp"].dt.to_period("D").dt.to_timestamp()
if selected_measure == "scrap_rate":
    controlled_trend = trend_source.groupby("period", as_index=False).agg(actual_output=("actual_output", "sum"), scrap_count=("scrap_count", "sum"))
    controlled_trend["value"] = controlled_trend["scrap_count"] / controlled_trend["actual_output"].replace(0, pd.NA)
elif selected_measure == "production_attainment":
    controlled_trend = trend_source.groupby("period", as_index=False).agg(actual_output=("actual_output", "sum"), planned_output=("planned_output", "sum"))
    controlled_trend["value"] = controlled_trend["actual_output"] / controlled_trend["planned_output"].replace(0, pd.NA)
else:
    controlled_trend = trend_source.groupby("period", as_index=False).agg(value=(selected_measure, "sum"))
controlled_trend["value"] = controlled_trend["value"].fillna(0)

machine_controlled = (
    controlled_ops.groupby("machine_id", as_index=False)
    .agg(
        actual_output=("actual_output", "sum"),
        scrap_count=("scrap_count", "sum"),
        downtime_minutes=("downtime_minutes", "sum"),
        planned_output=("planned_output", "sum"),
    )
)
machine_controlled["scrap_rate"] = machine_controlled["scrap_count"] / machine_controlled["actual_output"].replace(0, pd.NA)
machine_controlled["production_attainment"] = machine_controlled["actual_output"] / machine_controlled["planned_output"].replace(0, pd.NA)
machine_controlled = machine_controlled.fillna(0)
controlled_machine_top = top_n(machine_controlled, selected_measure if selected_measure in machine_controlled.columns else "actual_output", top_n_value)
controlled_tables = {"trend": controlled_trend, "machine_performance": controlled_machine_top}
set_active_analytics_result("manufacturing_controlled_chart_result", controlled_tables)

interactive_tabs = st.tabs(["Controlled Trend", "Controlled Machine Ranking"])
with interactive_tabs[0]:
    if controlled_trend.empty:
        st.info("No rows match the selected chart controls.")
    else:
        title = f"{selected_measure.replace('_', ' ').title()} Over Time"
        if trend_chart_type == "bar":
            fig = px.bar(controlled_trend, x="period", y="value", title=title)
        elif trend_chart_type == "area":
            fig = px.area(controlled_trend, x="period", y="value", title=title)
        else:
            fig = px.line(controlled_trend, x="period", y="value", markers=True, title=title)
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("Download controlled trend CSV", download_csv_bytes(controlled_trend), "manufacturing_controlled_trend.csv", "text/csv")
with interactive_tabs[1]:
    st.plotly_chart(
        px.bar(
            controlled_machine_top.sort_values(selected_measure if selected_measure in controlled_machine_top.columns else "actual_output"),
            x=selected_measure if selected_measure in controlled_machine_top.columns else "actual_output",
            y="machine_id",
            orientation="h",
            title="Controlled Machine Ranking",
        ),
        use_container_width=True,
    )
    st.download_button("Download controlled machine ranking CSV", download_csv_bytes(controlled_machine_top), "manufacturing_controlled_machine_ranking.csv", "text/csv")

st.subheader("Production Trends")
left, right = st.columns(2)
with left:
    st.plotly_chart(
        px.line(analytics.output_over_time, x="period", y="actual_output", markers=True, title="Output Over Time"),
        use_container_width=True,
    )
with right:
    st.plotly_chart(
        px.line(analytics.downtime_over_time, x="period", y="downtime_minutes", markers=True, title="Downtime Over Time"),
        use_container_width=True,
    )

st.subheader("Machine Performance")
left, right = st.columns(2)
with left:
    st.plotly_chart(
        px.bar(
            analytics.machine_performance.sort_values("total_output", ascending=True),
            x="total_output",
            y="machine_id",
            orientation="h",
            title="Output by Machine",
        ),
        use_container_width=True,
    )
with right:
    st.plotly_chart(
        px.bar(
            analytics.machine_performance.sort_values("scrap_rate", ascending=True),
            x="scrap_rate",
            y="machine_id",
            orientation="h",
            title="Scrap Rate by Machine",
        ),
        use_container_width=True,
    )

st.plotly_chart(
    px.bar(
        analytics.machine_performance.sort_values("downtime_minutes", ascending=True),
        x="downtime_minutes",
        y="machine_id",
        orientation="h",
        title="Downtime by Machine",
    ),
    use_container_width=True,
)

optional_cols = st.columns(2)
with optional_cols[0]:
    if not analytics.output_by_line.empty:
        st.plotly_chart(px.bar(analytics.output_by_line, x="line", y="actual_output", title="Output by Line"), use_container_width=True)
    else:
        st.info("Line field is not mapped or has no usable values.")
with optional_cols[1]:
    if not analytics.output_by_shift.empty:
        st.plotly_chart(px.bar(analytics.output_by_shift, x="shift", y="actual_output", title="Output by Shift"), use_container_width=True)
    else:
        st.info("Shift field is not mapped or has no usable values.")

tables = st.tabs(["Machine Performance", "Issue Summary", "Top Downtime Machines", "Top Scrap Machines", "Prepared Data Preview"])
with tables[0]:
    st.dataframe(analytics.machine_performance, use_container_width=True, hide_index=True)
with tables[1]:
    st.dataframe(analytics.issue_summary, use_container_width=True, hide_index=True)
with tables[2]:
    st.dataframe(analytics.machine_performance.sort_values("downtime_minutes", ascending=False).head(10), use_container_width=True, hide_index=True)
with tables[3]:
    st.dataframe(analytics.machine_performance.sort_values("scrap_rate", ascending=False).head(10), use_container_width=True, hide_index=True)
with tables[4]:
    st.dataframe(clean_result.prepared_operations.head(100), use_container_width=True, hide_index=True)
