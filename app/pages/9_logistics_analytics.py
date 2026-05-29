from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components.kpi_cards import format_currency, format_number, format_percent, render_kpi_grid
from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import LOGISTICS_REQUIRED_FIELDS
from app.services.chart_controls import apply_date_range_filter, apply_value_filters, download_csv_bytes, top_n
from app.services.column_mapper import initialize_template_mapping, validate_template_mapping
from app.services.dataset_workspace import get_active_template_mapping, set_active_analytics_result
from app.services.logistics_analytics import build_logistics_analytics, clean_logistics_shipments
from app.services.quality_score import calculate_quality_score
from app.services.schema_detector import detect_template_schema
from app.services.template_registry import get_template


configure_page("Logistics Analytics")
template = get_template("logistics")
page_title("Logistics Analytics", "Shipment lead time, on-time delivery, carrier, and destination analytics.")

df = get_working_dataframe()
if df is None:
    st.stop()

detection = detect_template_schema("logistics", list(df.columns))
mapping = get_active_template_mapping("logistics") or st.session_state.get("logistics_mapping")
if not mapping and not detection.requires_manual_mapping:
    mapping = initialize_template_mapping("logistics", list(df.columns), detection)

if not mapping or not validate_template_mapping("logistics", mapping, list(df.columns)).is_valid:
    st.warning("The active dataset is not mapped to this analytics template.")
    st.write("Required fields")
    st.dataframe([{"field": field} for field in template.required_fields], use_container_width=True, hide_index=True)
    st.write("Detected and missing fields")
    st.dataframe(
        [
            {
                "field": field,
                "matched_column": detection.matched_fields.get(field),
                "status": "matched" if field in detection.matched_fields else "missing",
            }
            for field in template.required_fields
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.info("Go to Column Mapping, use Generic Analytics, or load the logistics sample dataset.")
    st.stop()

quality = calculate_quality_score(
    df,
    mapping=mapping,
    required_fields=LOGISTICS_REQUIRED_FIELDS,
    date_fields=["order_date", "delivery_date", "planned_delivery_date"],
    numeric_fields=["shipping_cost"],
)

try:
    clean_result = clean_logistics_shipments(df, mapping)
    analytics = build_logistics_analytics(clean_result)
except Exception as exc:
    st.error(f"Logistics analytics could not be calculated: {exc}")
    st.stop()

set_active_analytics_result("logistics_clean_result", clean_result)
set_active_analytics_result("logistics_analytics_result", analytics)

metrics = analytics.metrics
st.subheader("Logistics KPIs")
render_kpi_grid(
    [
        ("Shipments", format_number(metrics["shipment_count"]), "Distinct valid shipments."),
        ("Avg lead time", f"{metrics['average_lead_time_days']:,.1f} days", None),
        ("On-time rate", format_percent(metrics["on_time_delivery_rate"]), "Delivered on or before planned delivery date."),
        ("Delayed shipments", format_number(metrics["delayed_shipments"]), None),
        ("Avg delay", f"{metrics['average_delay_days']:,.1f} days", "Average delay among delayed shipments."),
        ("Total shipping cost", format_currency(metrics["total_shipping_cost"]), "Shown when shipping cost is mapped."),
        ("Avg cost / shipment", format_currency(metrics["average_cost_per_shipment"]), "Shown when shipping cost is mapped."),
    ]
)

st.subheader("Main Chart: Lead Time Trend")
st.plotly_chart(
    px.line(analytics.lead_time_over_time, x="order_month", y="average_lead_time_days", markers=True, title="Lead Time Over Time"),
    use_container_width=True,
)

with st.expander("Template Quality Score"):
    st.progress(quality.overall_score / 100)
    st.dataframe(
        [{"dimension": key.replace("_", " ").title(), "score": value} for key, value in quality.sub_scores.items()],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Explore with Chart Controls")
controlled_shipments = clean_result.analysis_rows.copy()
control_cols = st.columns([1, 1, 1, 1])
date_column = control_cols[0].selectbox("Date basis", ["order_date", "delivery_date"])
date_values = controlled_shipments[date_column].dropna()
if not date_values.empty:
    selected_dates = control_cols[0].date_input(
        "Date range",
        value=(date_values.min().date(), date_values.max().date()),
        min_value=date_values.min().date(),
        max_value=date_values.max().date(),
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        controlled_shipments = apply_date_range_filter(controlled_shipments, date_column, selected_dates[0], selected_dates[1])

measure_options = ["shipment_count", "average_lead_time_days", "delayed_shipments"]
if "shipping_cost" in controlled_shipments.columns and controlled_shipments["shipping_cost"].notna().any():
    measure_options.append("total_shipping_cost")
selected_measure = control_cols[1].selectbox("Measure", measure_options, format_func=lambda value: value.replace("_", " ").title())
trend_chart_type = control_cols[2].selectbox("Shipment trend chart", ["line", "bar", "area"])
top_n_value = control_cols[3].slider("Top N", min_value=5, max_value=25, value=10, step=5)

filter_cols = st.columns(4)
filter_values: dict[str, list[object]] = {}
for col, field, label in [
    (filter_cols[0], "carrier", "Carrier"),
    (filter_cols[1], "origin", "Origin"),
    (filter_cols[2], "destination", "Destination"),
    (filter_cols[3], "delivery_status", "Delivery status"),
]:
    if field in controlled_shipments.columns and controlled_shipments[field].dropna().nunique() > 0:
        options = sorted(controlled_shipments[field].dropna().astype(str).unique().tolist())[:100]
        filter_values[field] = col.multiselect(label, options)
controlled_shipments = apply_value_filters(controlled_shipments, filter_values)

trend_source = controlled_shipments.copy()
trend_source["period"] = trend_source[date_column].dt.to_period("M").dt.to_timestamp()
trend_group = trend_source.groupby("period", as_index=False)
if selected_measure == "shipment_count":
    controlled_trend = trend_group.agg(value=("shipment_id", "nunique"))
elif selected_measure == "average_lead_time_days":
    controlled_trend = trend_group.agg(value=("lead_time_days", "mean"))
elif selected_measure == "delayed_shipments":
    controlled_trend = trend_group.agg(value=("delay_days", lambda s: int((s > 0).sum())))
else:
    controlled_trend = trend_group.agg(value=("shipping_cost", "sum"))
controlled_trend["value"] = controlled_trend["value"].fillna(0)

carrier_controlled = (
    controlled_shipments.dropna(subset=["carrier"])
    .groupby("carrier", as_index=False)
    .agg(
        shipment_count=("shipment_id", "nunique"),
        average_lead_time_days=("lead_time_days", "mean"),
        delayed_shipments=("delay_days", lambda s: int((s > 0).sum())),
        total_shipping_cost=("shipping_cost", "sum"),
    )
    .fillna(0)
)
destination_controlled = (
    controlled_shipments.dropna(subset=["destination"])
    .groupby("destination", as_index=False)
    .agg(
        shipment_count=("shipment_id", "nunique"),
        average_lead_time_days=("lead_time_days", "mean"),
        delayed_shipments=("delay_days", lambda s: int((s > 0).sum())),
        total_shipping_cost=("shipping_cost", "sum"),
    )
    .fillna(0)
)
carrier_top = top_n(carrier_controlled, selected_measure, top_n_value)
destination_top = top_n(destination_controlled, selected_measure, top_n_value)
controlled_tables = {"trend": controlled_trend, "carrier": carrier_top, "destination": destination_top}
set_active_analytics_result("logistics_controlled_chart_result", controlled_tables)

interactive_tabs = st.tabs(["Controlled Trend", "Carrier Ranking", "Destination Ranking"])
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
        st.download_button("Download controlled trend CSV", download_csv_bytes(controlled_trend), "logistics_controlled_trend.csv", "text/csv")
with interactive_tabs[1]:
    st.plotly_chart(px.bar(carrier_top, x="carrier", y=selected_measure, title="Controlled Carrier Ranking"), use_container_width=True)
    st.download_button("Download controlled carrier ranking CSV", download_csv_bytes(carrier_top), "logistics_controlled_carrier.csv", "text/csv")
with interactive_tabs[2]:
    st.plotly_chart(px.bar(destination_top, x="destination", y=selected_measure, title="Controlled Destination Ranking"), use_container_width=True)
    st.download_button("Download controlled destination ranking CSV", download_csv_bytes(destination_top), "logistics_controlled_destination.csv", "text/csv")

st.subheader("Shipment Trends")
st.plotly_chart(px.line(analytics.shipments_over_time, x="order_month", y="shipment_count", markers=True, title="Shipments Over Time"), use_container_width=True)

left, right = st.columns(2)
with left:
    st.plotly_chart(px.bar(analytics.status_summary, x="delivery_result", y="shipments", title="On-Time vs Delayed Shipments"), use_container_width=True)
with right:
    if not analytics.carrier_performance.empty:
        st.plotly_chart(px.bar(analytics.carrier_performance, x="carrier", y="shipment_count", title="Shipments by Carrier"), use_container_width=True)
    else:
        st.info("Carrier field is not mapped or has no usable values.")

if not analytics.carrier_performance.empty:
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.bar(analytics.carrier_performance, x="carrier", y="average_delay_days", title="Average Delay by Carrier"), use_container_width=True)
    with right:
        st.plotly_chart(px.bar(analytics.carrier_performance, x="carrier", y="total_shipping_cost", title="Shipping Cost by Carrier"), use_container_width=True)

if not analytics.destination_performance.empty:
    st.plotly_chart(px.bar(analytics.destination_performance, x="destination", y="shipment_count", title="Shipments by Destination"), use_container_width=True)

tables = st.tabs(["Carrier Performance", "Delayed Shipments", "Destination Performance", "Issue Summary", "Prepared Data Preview"])
with tables[0]:
    st.dataframe(analytics.carrier_performance, use_container_width=True, hide_index=True)
with tables[1]:
    st.dataframe(analytics.delayed_shipments.head(100), use_container_width=True, hide_index=True)
with tables[2]:
    st.dataframe(analytics.destination_performance, use_container_width=True, hide_index=True)
with tables[3]:
    st.dataframe(analytics.issue_summary, use_container_width=True, hide_index=True)
with tables[4]:
    st.dataframe(clean_result.prepared_shipments.head(100), use_container_width=True, hide_index=True)
