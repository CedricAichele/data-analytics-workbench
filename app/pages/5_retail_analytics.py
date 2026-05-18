from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.charts import (
    category_revenue_chart,
    country_revenue_chart,
    customer_revenue_chart,
    monthly_order_count_chart,
    monthly_revenue_chart,
    returns_by_month_chart,
    segment_distribution_chart,
    top_products_chart,
)
from app.components.kpi_cards import format_currency, format_number, format_percent, render_kpi_grid
from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import RETAIL_REQUIRED_FIELDS
from app.services.column_mapper import initialize_template_mapping, validate_retail_mapping
from app.services.chart_controls import apply_date_range_filter, apply_value_filters, download_csv_bytes, monthly_sum, top_n
from app.services.dataset_workspace import get_active_template_mapping, set_active_analytics_result
from app.services.quality_score import calculate_quality_score
from app.services.retail_analytics import build_retail_analytics, clean_retail_orders
from app.services.schema_detector import detect_template_schema
from app.services.template_registry import get_template


configure_page("Retail Analytics")
page_title("Retail / Sales Analytics", "SQL-backed KPIs, product performance, customer value, and RFM segmentation.")

df = get_working_dataframe()
if df is None:
    st.stop()

template = get_template("sales_retail")
detection = detect_template_schema("sales_retail", list(df.columns))
mapping = get_active_template_mapping("sales_retail") or st.session_state.get("column_mapping") or st.session_state.get("template_mappings", {}).get("sales_retail")
if not mapping and not detection.requires_manual_mapping:
    mapping = initialize_template_mapping("sales_retail", list(df.columns), detection)
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
    st.info("Go to Column Mapping, use Generic Analytics, or load the retail sample dataset.")
    st.stop()

validation = validate_retail_mapping(mapping, list(df.columns))
if not validation.is_valid:
    st.warning("The active dataset is not mapped to this analytics template.")
    for message in validation.messages:
        st.write(f"- {message}")
    st.info("Go to Column Mapping, use Generic Analytics, or load the retail sample dataset.")
    st.stop()

quality = calculate_quality_score(
    df,
    mapping=mapping,
    required_fields=RETAIL_REQUIRED_FIELDS,
    date_fields=["order_date"],
    numeric_fields=["quantity", "unit_price"],
)

try:
    clean_result = clean_retail_orders(df, mapping)
    analytics = build_retail_analytics(clean_result)
except Exception as exc:
    st.error(f"Retail analytics could not be calculated: {exc}")
    st.stop()

set_active_analytics_result("retail_clean_result", clean_result)
set_active_analytics_result("retail_analytics_result", analytics)

st.subheader("Retail KPIs")
metrics = analytics.metrics
render_kpi_grid(
    [
        ("Gross sales revenue", format_currency(metrics["gross_revenue"]), "Positive sales revenue before return and cancellation exclusions; duplicate rows are excluded."),
        ("Net revenue", format_currency(metrics["net_revenue"]), "Revenue from valid positive sales excluding returns and cancellations."),
        ("Valid orders", format_number(metrics["number_of_orders"]), "Distinct orders included in net revenue."),
        ("Valid customers", format_number(metrics["number_of_customers"]), "Distinct customers included in net revenue."),
        ("Average order value", format_currency(metrics["average_order_value"]), None),
        ("Quantity sold", format_number(metrics["total_quantity_sold"]), "Valid positive quantity sold."),
        ("Return rate", format_percent(metrics["return_rate"]), "Share of rows with negative quantity."),
        ("Cancelled rate", format_percent(metrics["cancelled_order_rate"]), "Share of distinct orders marked cancelled."),
    ]
)
st.metric(
    "Revenue from top 10 customers",
    format_percent(metrics["share_revenue_top_10_customers"]),
    help="Top 10 customer net revenue divided by total net revenue.",
)

with st.expander("KPI definitions"):
    st.dataframe(
        [
            {"metric": "Gross sales revenue", "definition": "Sum of positive quantity * unit price for rows with valid dates and non-duplicate records, before return and cancellation exclusions."},
            {"metric": "Net revenue", "definition": "Sum of quantity * unit price for positive, valid, non-cancelled, non-duplicate sales rows."},
            {"metric": "Valid orders", "definition": "Distinct order IDs represented in net revenue."},
            {"metric": "Average order value", "definition": "Net revenue divided by valid orders."},
            {"metric": "Return rate", "definition": "Non-duplicate return rows divided by non-duplicate rows."},
            {"metric": "Cancelled rate", "definition": "Distinct cancelled orders divided by distinct non-duplicate orders."},
            {"metric": "Top 10 customer share", "definition": "Net revenue from the 10 highest-revenue customers divided by total net revenue."},
        ],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Template Quality Score")
st.progress(quality.overall_score / 100)
quality_cols = st.columns(len(quality.sub_scores))
for col, (name, score) in zip(quality_cols, quality.sub_scores.items()):
    col.metric(name.replace("_", " ").title(), f"{score:.1f}")
with st.expander("Quality explanations and recommended fixes"):
    st.write("Explanations")
    for explanation in quality.explanations:
        st.write(f"- {explanation}")
    st.write("Recommended fixes")
    for fix in quality.recommended_fixes:
        st.write(f"- {fix}")

st.subheader("Chart Controls")
controlled_orders = clean_result.cleaned_orders.copy()
date_values = pd.to_datetime(controlled_orders["order_date"], errors="coerce").dropna()
control_cols = st.columns([1, 1, 1, 1])
if not date_values.empty:
    selected_dates = control_cols[0].date_input(
        "Order date range",
        value=(date_values.min().date(), date_values.max().date()),
        min_value=date_values.min().date(),
        max_value=date_values.max().date(),
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        controlled_orders = apply_date_range_filter(controlled_orders, "order_date", selected_dates[0], selected_dates[1])

revenue_measure = control_cols[1].selectbox("Revenue measure", ["net_revenue", "gross_revenue"], format_func=lambda value: value.replace("_", " ").title())
trend_chart_type = control_cols[2].selectbox("Revenue trend chart", ["line", "bar", "area"])
top_n_value = control_cols[3].slider("Top N", min_value=5, max_value=25, value=10, step=5)

filter_cols = st.columns(3)
filter_values: dict[str, list[object]] = {}
for col, field, label in [
    (filter_cols[0], "country", "Country"),
    (filter_cols[1], "product_category", "Product category"),
    (filter_cols[2], "product_name", "Product"),
]:
    if field in controlled_orders.columns and controlled_orders[field].dropna().nunique() > 0:
        options = sorted(controlled_orders[field].dropna().astype(str).unique().tolist())[:100]
        filter_values[field] = col.multiselect(label, options)
controlled_orders = apply_value_filters(controlled_orders, filter_values)

controlled_trend = monthly_sum(controlled_orders, "order_date", revenue_measure, "revenue")
controlled_products = (
    controlled_orders.dropna(subset=["product_name"])
    .groupby("product_name", as_index=False)
    .agg(revenue=(revenue_measure, "sum"), quantity=("quantity", "sum"))
)
controlled_customers = (
    controlled_orders.dropna(subset=["customer_id"])
    .groupby("customer_id", as_index=False)
    .agg(revenue=(revenue_measure, "sum"), order_count=("order_id", "nunique"))
)
controlled_products = top_n(controlled_products, "revenue", top_n_value)
controlled_customers = top_n(controlled_customers, "revenue", top_n_value)
controlled_tables = {
    "trend": controlled_trend,
    "top_products": controlled_products,
    "top_customers": controlled_customers,
}
set_active_analytics_result("retail_controlled_chart_result", controlled_tables)

interactive_tabs = st.tabs(["Revenue Trend", "Top Products", "Top Customers"])
with interactive_tabs[0]:
    if controlled_trend.empty:
        st.info("No rows match the selected chart controls.")
    else:
        if trend_chart_type == "bar":
            fig = px.bar(controlled_trend, x="period", y="revenue", title="Controlled Revenue Trend")
        elif trend_chart_type == "area":
            fig = px.area(controlled_trend, x="period", y="revenue", title="Controlled Revenue Trend")
        else:
            fig = px.line(controlled_trend, x="period", y="revenue", markers=True, title="Controlled Revenue Trend")
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("Download controlled revenue trend CSV", download_csv_bytes(controlled_trend), "retail_controlled_revenue_trend.csv", "text/csv")
with interactive_tabs[1]:
    st.plotly_chart(px.bar(controlled_products.sort_values("revenue"), x="revenue", y="product_name", orientation="h", title="Controlled Top Products"), use_container_width=True)
    st.download_button("Download controlled top products CSV", download_csv_bytes(controlled_products), "retail_controlled_top_products.csv", "text/csv")
with interactive_tabs[2]:
    st.plotly_chart(px.bar(controlled_customers.sort_values("revenue"), x="revenue", y="customer_id", orientation="h", title="Controlled Top Customers"), use_container_width=True)
    st.download_button("Download controlled top customers CSV", download_csv_bytes(controlled_customers), "retail_controlled_top_customers.csv", "text/csv")

st.subheader("Revenue and Orders")
left, right = st.columns(2)
with left:
    st.plotly_chart(monthly_revenue_chart(analytics.monthly_revenue), use_container_width=True)
with right:
    st.plotly_chart(monthly_order_count_chart(analytics.monthly_revenue), use_container_width=True)

left, right = st.columns(2)
with left:
    st.plotly_chart(returns_by_month_chart(analytics.monthly_revenue), use_container_width=True)
with right:
    if not analytics.product_performance.empty and analytics.product_performance["product_category"].nunique() > 1:
        st.plotly_chart(category_revenue_chart(analytics.product_performance), use_container_width=True)
    else:
        st.info("Product category is not available or has only one usable value.")

st.subheader("Product and Customer Performance")
left, right = st.columns(2)
with left:
    st.plotly_chart(top_products_chart(analytics.product_performance), use_container_width=True)
with right:
    if not analytics.customer_rfm.empty:
        st.plotly_chart(customer_revenue_chart(analytics.customer_rfm), use_container_width=True)
    else:
        st.info("Customer revenue cannot be charted without valid customer IDs.")

if not analytics.country_performance.empty and analytics.country_performance["country"].nunique() > 1:
    st.subheader("Country Performance")
    st.plotly_chart(country_revenue_chart(analytics.country_performance), use_container_width=True)

st.subheader("RFM Customer Segmentation")
left, right = st.columns([1, 1])
with left:
    st.plotly_chart(segment_distribution_chart(analytics.segment_summary), use_container_width=True)
with right:
    st.dataframe(analytics.segment_summary, use_container_width=True, hide_index=True)

tables = st.tabs(["Top Products", "Customer RFM", "Country Performance", "Data Quality Issues", "Cleaned Orders Preview"])
with tables[0]:
    st.dataframe(analytics.product_performance.head(25), use_container_width=True, hide_index=True)
with tables[1]:
    st.dataframe(analytics.customer_rfm.head(100), use_container_width=True, hide_index=True)
with tables[2]:
    st.dataframe(analytics.country_performance, use_container_width=True, hide_index=True)
with tables[3]:
    st.dataframe(analytics.issue_summary, use_container_width=True, hide_index=True)
with tables[4]:
    st.dataframe(clean_result.cleaned_orders.head(100), use_container_width=True, hide_index=True)
