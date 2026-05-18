from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components.kpi_cards import format_number, format_percent, render_kpi_grid
from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import MANUFACTURING_REQUIRED_FIELDS
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
