from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components.kpi_cards import format_currency, format_number, format_percent, render_kpi_grid
from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import FINANCE_REQUIRED_FIELDS
from app.services.column_mapper import initialize_template_mapping, validate_template_mapping
from app.services.dataset_workspace import get_active_template_mapping, set_active_analytics_result
from app.services.finance_analytics import build_finance_analytics, clean_finance_transactions
from app.services.quality_score import calculate_quality_score
from app.services.schema_detector import detect_template_schema
from app.services.template_registry import get_template


configure_page("Finance Analytics")
template = get_template("finance")
page_title("Finance Analytics", "Revenue, cost, net result, margin, and budget variance analytics.")

df = get_working_dataframe()
if df is None:
    st.stop()

detection = detect_template_schema("finance", list(df.columns))
mapping = get_active_template_mapping("finance") or st.session_state.get("finance_mapping")
if not mapping and not detection.requires_manual_mapping:
    mapping = initialize_template_mapping("finance", list(df.columns), detection)

if not mapping or not validate_template_mapping("finance", mapping, list(df.columns)).is_valid:
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
    st.info("Go to Column Mapping, use Generic Analytics, or load the finance sample dataset.")
    st.stop()

quality = calculate_quality_score(
    df,
    mapping=mapping,
    required_fields=FINANCE_REQUIRED_FIELDS,
    date_fields=["date"],
    numeric_fields=["amount", "budget", "actual"],
)

try:
    clean_result = clean_finance_transactions(df, mapping)
    analytics = build_finance_analytics(clean_result)
except Exception as exc:
    st.error(f"Finance analytics could not be calculated: {exc}")
    st.stop()

uninterpretable = clean_result.issue_summary.loc[
    clean_result.issue_summary["issue"] == "Uninterpretable type values",
    "row_count",
].iloc[0]
if uninterpretable and analytics.metrics["transaction_count"] == 0:
    st.warning("Type values could not be interpreted as revenue or cost. Check the mapped type column before using finance KPIs.")
    st.stop()

set_active_analytics_result("finance_clean_result", clean_result)
set_active_analytics_result("finance_analytics_result", analytics)

metrics = analytics.metrics
st.subheader("Finance KPIs")
render_kpi_grid(
    [
        ("Total revenue", format_currency(metrics["total_revenue"]), None),
        ("Total cost", format_currency(metrics["total_cost"]), None),
        ("Net result", format_currency(metrics["net_result"]), "Revenue minus cost."),
        ("Margin", format_percent(metrics["margin"]), "Net result divided by revenue."),
        ("Transactions", format_number(metrics["transaction_count"]), None),
        ("Avg transaction", format_currency(metrics["average_transaction_amount"]), None),
        ("Budget variance", format_currency(metrics["budget_variance"]), "Actual minus budget when both are mapped."),
    ]
)

st.subheader("Template Quality Score")
st.progress(quality.overall_score / 100)
st.dataframe(
    [{"dimension": key.replace("_", " ").title(), "score": value} for key, value in quality.sub_scores.items()],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Monthly Performance")
left, right = st.columns(2)
with left:
    st.plotly_chart(px.line(analytics.monthly_summary, x="month", y=["revenue", "cost"], markers=True, title="Monthly Revenue and Cost"), use_container_width=True)
with right:
    st.plotly_chart(px.line(analytics.monthly_summary, x="month", y="net_result", markers=True, title="Net Result Over Time"), use_container_width=True)

if not analytics.category_summary.empty:
    category_cost = analytics.category_summary[analytics.category_summary["normalized_type"] == "cost"]
    category_revenue = analytics.category_summary[analytics.category_summary["normalized_type"] == "revenue"]
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.bar(category_cost, x="category", y="amount", title="Cost by Category"), use_container_width=True)
    with right:
        st.plotly_chart(px.bar(category_revenue, x="category", y="amount", title="Revenue by Category"), use_container_width=True)

if not analytics.cost_center_summary.empty:
    st.plotly_chart(px.bar(analytics.cost_center_summary, x="cost_center", y=["revenue", "cost"], barmode="group", title="Amount by Cost Center"), use_container_width=True)

if {"budget", "actual"} <= set(clean_result.analysis_rows.columns):
    valid_budget = clean_result.analysis_rows.dropna(subset=["budget", "actual"])
    if not valid_budget.empty:
        budget_actual = valid_budget.groupby("cost_center", dropna=False, as_index=False).agg(budget=("budget", "sum"), actual=("actual", "sum"))
        st.plotly_chart(px.bar(budget_actual, x="cost_center", y=["budget", "actual"], barmode="group", title="Budget vs Actual"), use_container_width=True)

tables = st.tabs(["Category Summary", "Cost Center Summary", "Largest Transactions", "Issue Summary", "Prepared Data Preview"])
with tables[0]:
    st.dataframe(analytics.category_summary, use_container_width=True, hide_index=True)
with tables[1]:
    st.dataframe(analytics.cost_center_summary, use_container_width=True, hide_index=True)
with tables[2]:
    st.dataframe(analytics.largest_transactions, use_container_width=True, hide_index=True)
with tables[3]:
    st.dataframe(analytics.issue_summary, use_container_width=True, hide_index=True)
with tables[4]:
    st.dataframe(clean_result.prepared_transactions.head(100), use_container_width=True, hide_index=True)
