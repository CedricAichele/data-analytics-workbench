"""Plotly chart builders for profiler and retail analytics pages."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def missing_values_chart(missing_table: pd.DataFrame) -> go.Figure:
    data = missing_table[missing_table["missing_count"] > 0].copy()
    if data.empty:
        data = missing_table.copy()
    fig = px.bar(
        data,
        x="column",
        y="missing_count",
        title="Missing Values by Column",
        labels={"column": "Column", "missing_count": "Missing values"},
    )
    fig.update_layout(xaxis_tickangle=-35, height=420)
    return fig


def dtype_distribution_chart(dtype_distribution: pd.DataFrame) -> go.Figure:
    fig = px.pie(
        dtype_distribution,
        names="dtype",
        values="column_count",
        title="Detected Data Type Distribution",
        hole=0.45,
    )
    fig.update_layout(height=380)
    return fig


def numeric_distribution_chart(df: pd.DataFrame, column: str) -> go.Figure:
    fig = px.histogram(
        df,
        x=column,
        nbins=40,
        title=f"Distribution of {column}",
        labels={column: column},
    )
    fig.update_layout(height=420)
    return fig


def categorical_frequency_chart(df: pd.DataFrame, column: str, top_n: int = 15) -> go.Figure:
    counts = df[column].value_counts(dropna=True).head(top_n).reset_index()
    counts.columns = [column, "count"]
    fig = px.bar(
        counts,
        x=column,
        y="count",
        title=f"Top {top_n} Values for {column}",
        labels={column: column, "count": "Rows"},
    )
    fig.update_layout(xaxis_tickangle=-35, height=420)
    return fig


def monthly_revenue_chart(monthly_revenue: pd.DataFrame) -> go.Figure:
    fig = px.line(
        monthly_revenue,
        x="month",
        y=["gross_revenue", "net_revenue"],
        markers=True,
        title="Revenue by Month",
        labels={"value": "Revenue", "month": "Month", "variable": "Metric"},
    )
    fig.update_layout(height=430)
    return fig


def monthly_order_count_chart(monthly_revenue: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        monthly_revenue,
        x="month",
        y="order_count",
        title="Order Count by Month",
        labels={"month": "Month", "order_count": "Orders"},
    )
    fig.update_layout(height=380)
    return fig


def returns_by_month_chart(monthly_revenue: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        monthly_revenue,
        x="month",
        y="return_rows",
        title="Returns by Month",
        labels={"month": "Month", "return_rows": "Return rows"},
    )
    fig.update_layout(height=380)
    return fig


def top_products_chart(product_performance: pd.DataFrame, top_n: int = 10) -> go.Figure:
    data = product_performance.head(top_n).sort_values("net_revenue", ascending=True)
    fig = px.bar(
        data,
        x="net_revenue",
        y="product_name",
        orientation="h",
        title=f"Top {top_n} Products by Net Revenue",
        labels={"net_revenue": "Net revenue", "product_name": "Product"},
    )
    fig.update_layout(height=430)
    return fig


def category_revenue_chart(product_performance: pd.DataFrame) -> go.Figure:
    category = (
        product_performance.groupby("product_category", as_index=False)["net_revenue"]
        .sum()
        .sort_values("net_revenue", ascending=False)
    )
    fig = px.bar(
        category,
        x="product_category",
        y="net_revenue",
        title="Revenue by Product Category",
        labels={"product_category": "Category", "net_revenue": "Net revenue"},
    )
    fig.update_layout(xaxis_tickangle=-25, height=420)
    return fig


def country_revenue_chart(country_performance: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        country_performance,
        x="country",
        y="net_revenue",
        title="Revenue by Country",
        labels={"country": "Country", "net_revenue": "Net revenue"},
    )
    fig.update_layout(xaxis_tickangle=-25, height=420)
    return fig


def customer_revenue_chart(customer_rfm: pd.DataFrame, top_n: int = 10) -> go.Figure:
    data = customer_rfm.head(top_n).sort_values("monetary", ascending=True)
    fig = px.bar(
        data,
        x="monetary",
        y="customer_id",
        orientation="h",
        title=f"Top {top_n} Customers by Net Revenue",
        labels={"monetary": "Net revenue", "customer_id": "Customer"},
    )
    fig.update_layout(height=430)
    return fig


def segment_distribution_chart(segment_summary: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        segment_summary,
        x="segment",
        y="customer_count",
        title="Customer Segment Distribution",
        labels={"segment": "Segment", "customer_count": "Customers"},
    )
    fig.update_layout(xaxis_tickangle=-25, height=420)
    return fig

