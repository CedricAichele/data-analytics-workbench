from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.components.kpi_cards import format_currency, format_number, format_percent, render_kpi_grid
from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import FINANCE_REQUIRED_FIELDS
from app.services.chart_controls import apply_date_range_filter, apply_value_filters, download_csv_bytes, top_n
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

st.subheader("Main Chart: Monthly Revenue, Cost and Net Result")
st.plotly_chart(
    px.line(analytics.monthly_summary, x="month", y=["revenue", "cost", "net_result"], markers=True, title="Monthly Revenue, Cost and Net Result"),
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
controlled_transactions = clean_result.analysis_rows.copy()
date_values = controlled_transactions["date"].dropna()
control_cols = st.columns([1, 1, 1, 1])
if not date_values.empty:
    selected_dates = control_cols[0].date_input(
        "Date range",
        value=(date_values.min().date(), date_values.max().date()),
        min_value=date_values.min().date(),
        max_value=date_values.max().date(),
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        controlled_transactions = apply_date_range_filter(controlled_transactions, "date", selected_dates[0], selected_dates[1])

measure_options = ["revenue", "cost", "net_result", "amount"]
if {"budget", "actual"} <= set(controlled_transactions.columns) and controlled_transactions[["budget", "actual"]].notna().any().any():
    measure_options.append("budget_variance")
selected_measure = control_cols[1].selectbox("Measure", measure_options, format_func=lambda value: value.replace("_", " ").title())
trend_chart_type = control_cols[2].selectbox("Monthly chart", ["line", "bar", "area"])
top_n_value = control_cols[3].slider("Top N categories", min_value=5, max_value=25, value=10, step=5)

filter_cols = st.columns(4)
filter_values: dict[str, list[object]] = {}
for col, field, label in [
    (filter_cols[0], "normalized_type", "Type"),
    (filter_cols[1], "category", "Category"),
    (filter_cols[2], "account", "Account"),
    (filter_cols[3], "cost_center", "Cost center"),
]:
    if field in controlled_transactions.columns and controlled_transactions[field].dropna().nunique() > 0:
        options = sorted(controlled_transactions[field].dropna().astype(str).unique().tolist())[:100]
        filter_values[field] = col.multiselect(label, options)
controlled_transactions = apply_value_filters(controlled_transactions, filter_values)

trend_source = controlled_transactions.copy()
trend_source["period"] = trend_source["date"].dt.to_period("M").dt.to_timestamp()
monthly = trend_source.groupby("period", as_index=False).agg(
    revenue=("abs_amount", lambda s: s[trend_source.loc[s.index, "normalized_type"] == "revenue"].sum()),
    cost=("abs_amount", lambda s: s[trend_source.loc[s.index, "normalized_type"] == "cost"].sum()),
    amount=("abs_amount", "sum"),
    budget=("budget", "sum"),
    actual=("actual", "sum"),
)
monthly["net_result"] = monthly["revenue"] - monthly["cost"]
monthly["budget_variance"] = monthly["actual"] - monthly["budget"]
value_columns = ["revenue", "cost"] if selected_measure in {"revenue", "cost"} else [selected_measure]

category_controlled = (
    controlled_transactions.assign(category=controlled_transactions["category"].fillna("Missing"))
    .groupby("category", as_index=False)
    .agg(
        revenue=("abs_amount", lambda s: s[controlled_transactions.loc[s.index, "normalized_type"] == "revenue"].sum()),
        cost=("abs_amount", lambda s: s[controlled_transactions.loc[s.index, "normalized_type"] == "cost"].sum()),
        amount=("abs_amount", "sum"),
        budget=("budget", "sum"),
        actual=("actual", "sum"),
    )
)
category_controlled["net_result"] = category_controlled["revenue"] - category_controlled["cost"]
category_controlled["budget_variance"] = category_controlled["actual"] - category_controlled["budget"]
category_top = top_n(category_controlled, selected_measure, top_n_value)
controlled_tables = {"monthly": monthly, "category": category_top}
set_active_analytics_result("finance_controlled_chart_result", controlled_tables)

interactive_tabs = st.tabs(["Controlled Monthly View", "Controlled Category Ranking"])
with interactive_tabs[0]:
    if monthly.empty:
        st.info("No rows match the selected chart controls.")
    else:
        title = f"{selected_measure.replace('_', ' ').title()} Monthly View"
        if trend_chart_type == "bar":
            fig = px.bar(monthly, x="period", y=value_columns, barmode="group", title=title)
        elif trend_chart_type == "area":
            fig = px.area(monthly, x="period", y=value_columns, title=title)
        else:
            fig = px.line(monthly, x="period", y=value_columns, markers=True, title=title)
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("Download controlled monthly CSV", download_csv_bytes(monthly), "finance_controlled_monthly.csv", "text/csv")
with interactive_tabs[1]:
    st.plotly_chart(px.bar(category_top, x="category", y=selected_measure, title="Controlled Category Ranking"), use_container_width=True)
    st.download_button("Download controlled category CSV", download_csv_bytes(category_top), "finance_controlled_category.csv", "text/csv")

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
