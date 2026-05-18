from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components.kpi_cards import format_currency, format_number, format_percent, render_kpi_grid
from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import LOGISTICS_REQUIRED_FIELDS
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

st.subheader("Template Quality Score")
st.progress(quality.overall_score / 100)
st.dataframe(
    [{"dimension": key.replace("_", " ").title(), "score": value} for key, value in quality.sub_scores.items()],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Shipment Trends")
left, right = st.columns(2)
with left:
    st.plotly_chart(px.line(analytics.shipments_over_time, x="order_month", y="shipment_count", markers=True, title="Shipments Over Time"), use_container_width=True)
with right:
    st.plotly_chart(px.line(analytics.lead_time_over_time, x="order_month", y="average_lead_time_days", markers=True, title="Lead Time Over Time"), use_container_width=True)

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
