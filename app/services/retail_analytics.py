"""Retail-specific cleaning, KPI analytics, and RFM segmentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.config import ALL_RETAIL_FIELDS
from app.services.duckdb_service import DuckDBService


@dataclass(frozen=True)
class RetailCleanResult:
    prepared_orders: pd.DataFrame
    cleaned_orders: pd.DataFrame
    issue_summary: pd.DataFrame


@dataclass(frozen=True)
class RetailAnalyticsResult:
    metrics: dict[str, float]
    monthly_revenue: pd.DataFrame
    product_performance: pd.DataFrame
    country_performance: pd.DataFrame
    customer_rfm: pd.DataFrame
    segment_summary: pd.DataFrame
    issue_summary: pd.DataFrame


def _parse_mixed_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def _clean_text(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.replace("", pd.NA)


def prepare_retail_orders(df: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    """Standardize a mapped retail dataframe without silently dropping rows."""
    standardized = pd.DataFrame(index=df.index)
    for field in ALL_RETAIL_FIELDS:
        source_column = mapping.get(field)
        if source_column and source_column in df.columns:
            standardized[field] = df[source_column]
        else:
            standardized[field] = pd.NA

    for field in ["order_id", "customer_id", "product_name", "country", "product_category", "invoice_status"]:
        standardized[field] = _clean_text(standardized[field])

    standardized["original_order_date"] = standardized["order_date"]
    standardized["order_date"] = _parse_mixed_dates(standardized["order_date"])
    standardized["quantity"] = pd.to_numeric(standardized["quantity"], errors="coerce")
    standardized["unit_price"] = pd.to_numeric(standardized["unit_price"], errors="coerce")

    status = standardized["invoice_status"].fillna("").str.lower()
    standardized["is_return"] = standardized["quantity"] < 0
    standardized["is_invalid_price"] = standardized["unit_price"].isna() | (standardized["unit_price"] <= 0)
    standardized["is_missing_customer"] = standardized["customer_id"].isna()
    standardized["is_invalid_date"] = standardized["original_order_date"].notna() & standardized["order_date"].isna()
    standardized["is_cancelled"] = (
        status.str.contains("cancel", na=False)
        | status.str.contains("void", na=False)
        | status.str.contains("rejected", na=False)
    )
    duplicate_check_columns = [
        "order_id",
        "order_date",
        "customer_id",
        "product_name",
        "product_category",
        "quantity",
        "unit_price",
        "country",
        "invoice_status",
    ]
    standardized["is_duplicate_row"] = standardized.duplicated(subset=duplicate_check_columns, keep="first")
    standardized["is_analysis_valid"] = (
        standardized["order_date"].notna()
        & standardized["quantity"].notna()
        & standardized["unit_price"].notna()
        & (standardized["quantity"] > 0)
        & (standardized["unit_price"] > 0)
        & ~standardized["is_cancelled"]
        & ~standardized["is_duplicate_row"]
    )
    standardized["gross_revenue"] = np.where(
        (standardized["quantity"] > 0)
        & (standardized["unit_price"] > 0)
        & standardized["order_date"].notna()
        & ~standardized["is_duplicate_row"],
        standardized["quantity"] * standardized["unit_price"],
        0.0,
    )
    standardized["net_revenue"] = np.where(
        standardized["is_analysis_valid"],
        standardized["quantity"] * standardized["unit_price"],
        0.0,
    )
    return standardized


def build_issue_summary(prepared_orders: pd.DataFrame) -> pd.DataFrame:
    """Summarize cleaning flags and the analysis handling for each issue."""
    checks = [
        ("Duplicate rows", int(prepared_orders["is_duplicate_row"].sum()), "Medium", "First occurrence retained; repeated exact rows are excluded from KPI calculations."),
        ("Missing customer IDs", int(prepared_orders["is_missing_customer"].sum()), "Medium", "Excluded from customer-level analytics, retained for sales totals."),
        ("Returns / negative quantities", int(prepared_orders["is_return"].sum()), "Business event", "Tracked as returns and excluded from net revenue KPIs."),
        ("Invalid unit prices", int(prepared_orders["is_invalid_price"].sum()), "High", "Excluded from revenue calculations."),
        ("Date parsing issues", int(prepared_orders["is_invalid_date"].sum()), "High", "Excluded from time-series analytics until dates are corrected."),
        ("Cancelled orders", int(prepared_orders["is_cancelled"].sum()), "Business event", "Excluded from net revenue KPIs."),
    ]
    return pd.DataFrame(
        checks,
        columns=["issue", "row_count", "severity", "analysis_handling"],
    )


def clean_retail_orders(df: pd.DataFrame, mapping: dict[str, str | None]) -> RetailCleanResult:
    """Run the retail cleaning pipeline and enrich it through the DuckDB SQL layer."""
    prepared_orders = prepare_retail_orders(df, mapping)
    issue_summary = build_issue_summary(prepared_orders)
    with DuckDBService() as db:
        cleaned_orders = db.run_sql_file(
            "retail_cleaned_orders.sql",
            {"retail_orders_prepared": prepared_orders},
        )
    return RetailCleanResult(
        prepared_orders=prepared_orders,
        cleaned_orders=cleaned_orders,
        issue_summary=issue_summary,
    )


def _safe_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)


def calculate_kpis(cleaned_orders: pd.DataFrame, customer_rfm_base: pd.DataFrame) -> dict[str, float]:
    """Calculate headline retail KPIs from cleaned orders."""
    query = """
    SELECT
        COALESCE(SUM(gross_revenue), 0) AS gross_revenue,
        COALESCE(SUM(net_revenue), 0) AS net_revenue,
        COUNT(DISTINCT CASE WHEN is_analysis_valid THEN order_id END) AS number_of_orders,
        COUNT(DISTINCT CASE WHEN is_analysis_valid AND customer_id IS NOT NULL AND TRIM(CAST(customer_id AS VARCHAR)) <> '' THEN customer_id END) AS number_of_customers,
        COALESCE(SUM(CASE WHEN is_analysis_valid THEN quantity ELSE 0 END), 0) AS total_quantity_sold,
        COALESCE(
            SUM(CASE WHEN is_return AND NOT is_duplicate_row THEN 1 ELSE 0 END) * 1.0
            / NULLIF(SUM(CASE WHEN NOT is_duplicate_row THEN 1 ELSE 0 END), 0),
            0
        ) AS return_rate,
        COALESCE(
            COUNT(DISTINCT CASE WHEN is_cancelled AND NOT is_duplicate_row THEN order_id END) * 1.0
            / NULLIF(COUNT(DISTINCT CASE WHEN NOT is_duplicate_row THEN order_id END), 0),
            0
        ) AS cancelled_order_rate
    FROM cleaned_orders
    """
    with DuckDBService() as db:
        metrics_row = db.run_query(query, {"cleaned_orders": cleaned_orders}).iloc[0].to_dict()

    net_revenue = _safe_float(metrics_row["net_revenue"])
    order_count = int(metrics_row["number_of_orders"] or 0)
    top_10_customer_revenue = (
        customer_rfm_base.sort_values("monetary", ascending=False)
        .head(10)["monetary"]
        .sum()
        if not customer_rfm_base.empty
        else 0
    )
    share_top_10 = float(top_10_customer_revenue / net_revenue) if net_revenue else 0.0

    return {
        "gross_revenue": round(_safe_float(metrics_row["gross_revenue"]), 2),
        "net_revenue": round(net_revenue, 2),
        "number_of_orders": float(order_count),
        "number_of_customers": float(metrics_row["number_of_customers"] or 0),
        "average_order_value": round(net_revenue / order_count, 2) if order_count else 0.0,
        "total_quantity_sold": round(_safe_float(metrics_row["total_quantity_sold"]), 2),
        "return_rate": round(_safe_float(metrics_row["return_rate"]), 4),
        "cancelled_order_rate": round(_safe_float(metrics_row["cancelled_order_rate"]), 4),
        "share_revenue_top_10_customers": round(share_top_10, 4),
    }


def _score_quintile(series: pd.Series, *, higher_is_better: bool = True) -> pd.Series:
    """Convert a metric into stable 1-5 percentile scores."""
    if series.empty:
        return pd.Series(dtype="Int64")
    percentile = series.rank(method="average", pct=True)
    if not higher_is_better:
        percentile = 1 - percentile + (1 / max(len(series), 1))
    scores = np.ceil(percentile * 5).clip(1, 5).astype(int)
    return pd.Series(scores, index=series.index)


def assign_rfm_segments(rfm_base: pd.DataFrame) -> pd.DataFrame:
    """Score and segment customers using simple documented RFM rules.

    Rules:
    - Champions: recent buyers with high frequency and high monetary value.
    - Loyal Customers: high frequency and solid monetary value.
    - Potential Loyalists: recent customers with moderate repeat behavior.
    - New Customers: recent customers with low frequency.
    - At Risk: historically active customers with poor recent activity.
    - Low Value: fallback for low monetary/frequency profiles.
    """
    if rfm_base.empty:
        columns = list(rfm_base.columns) + ["r_score", "f_score", "m_score", "rfm_score", "segment"]
        return pd.DataFrame(columns=columns)

    rfm = rfm_base.copy()
    rfm["r_score"] = _score_quintile(rfm["recency_days"], higher_is_better=False)
    rfm["f_score"] = _score_quintile(rfm["frequency"], higher_is_better=True)
    rfm["m_score"] = _score_quintile(rfm["monetary"], higher_is_better=True)
    rfm["rfm_score"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)

    conditions = [
        (rfm["r_score"] >= 4) & (rfm["f_score"] >= 4) & (rfm["m_score"] >= 4),
        (rfm["f_score"] >= 4) & (rfm["m_score"] >= 3),
        (rfm["r_score"] >= 4) & (rfm["f_score"] >= 2),
        (rfm["r_score"] >= 4) & (rfm["f_score"] <= 2),
        (rfm["r_score"] <= 2) & (rfm["f_score"] >= 3),
    ]
    choices = [
        "Champions",
        "Loyal Customers",
        "Potential Loyalists",
        "New Customers",
        "At Risk",
    ]
    rfm["segment"] = np.select(conditions, choices, default="Low Value")
    return rfm.sort_values(["monetary", "frequency"], ascending=False).reset_index(drop=True)


def summarize_segments(customer_rfm: pd.DataFrame) -> pd.DataFrame:
    if customer_rfm.empty:
        return pd.DataFrame(columns=["segment", "customer_count", "revenue"])
    return (
        customer_rfm.groupby("segment", as_index=False)
        .agg(customer_count=("customer_id", "nunique"), revenue=("monetary", "sum"))
        .sort_values("revenue", ascending=False)
    )


def build_retail_analytics(clean_result: RetailCleanResult) -> RetailAnalyticsResult:
    """Run SQL-backed retail analytics and RFM segmentation."""
    cleaned_orders = clean_result.cleaned_orders
    with DuckDBService() as db:
        db.register("cleaned_orders", cleaned_orders)
        monthly_revenue = db.run_sql_file("retail_monthly_revenue.sql")
        product_performance = db.run_sql_file("retail_product_performance.sql")
        country_performance = db.run_sql_file("retail_country_performance.sql")
        rfm_base = db.run_sql_file("retail_customer_rfm.sql")

    customer_rfm = assign_rfm_segments(rfm_base)
    segment_summary = summarize_segments(customer_rfm)
    metrics = calculate_kpis(cleaned_orders, rfm_base)

    return RetailAnalyticsResult(
        metrics=metrics,
        monthly_revenue=monthly_revenue,
        product_performance=product_performance,
        country_performance=country_performance,
        customer_rfm=customer_rfm,
        segment_summary=segment_summary,
        issue_summary=clean_result.issue_summary,
    )
