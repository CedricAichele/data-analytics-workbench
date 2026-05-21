"""Deterministic management summary generation."""

from __future__ import annotations

import pandas as pd

from app.services.finance_analytics import FinanceAnalyticsResult
from app.services.logistics_analytics import LogisticsAnalyticsResult
from app.services.manufacturing_analytics import ManufacturingAnalyticsResult
from app.services.quality_score import DataQualityReport
from app.services.retail_analytics import RetailAnalyticsResult


def _format_currency(value: float) -> str:
    return f"${value:,.0f}"


def _trend_sentence(monthly_revenue: pd.DataFrame) -> str:
    if monthly_revenue.empty or len(monthly_revenue) < 2:
        return "Revenue trend cannot be assessed because fewer than two monthly periods are available."

    first = float(monthly_revenue.iloc[0]["net_revenue"])
    last = float(monthly_revenue.iloc[-1]["net_revenue"])
    if first == 0:
        return "Revenue trend improved from a zero baseline in the first available month."
    change = (last - first) / abs(first)
    direction = "increased" if change >= 0 else "decreased"
    return f"Net revenue {direction} by {abs(change):.1%} from the first to the latest available month."


def generate_retail_management_summary(result: RetailAnalyticsResult) -> str:
    """Create a deterministic executive-style summary from calculated metrics."""
    metrics = result.metrics
    issue_rows = result.issue_summary[result.issue_summary["row_count"] > 0]
    top_product = (
        result.product_performance.iloc[0]
        if not result.product_performance.empty
        else None
    )
    top_segment = (
        result.segment_summary.iloc[0]
        if not result.segment_summary.empty
        else None
    )

    top_customer_share = metrics.get("share_revenue_top_10_customers", 0)
    concentration_note = (
        f"The top 10 customers account for {top_customer_share:.1%} of net revenue, indicating meaningful customer concentration."
        if top_customer_share >= 0.35
        else f"The top 10 customers account for {top_customer_share:.1%} of net revenue, suggesting revenue is not overly concentrated."
    )

    product_note = (
        f"The strongest product is {top_product['product_name']} with {_format_currency(float(top_product['net_revenue']))} in net revenue."
        if top_product is not None
        else "Product concentration cannot be assessed because no valid product revenue was available."
    )

    segment_note = (
        f"The largest revenue customer segment is {top_segment['segment']} with {_format_currency(float(top_segment['revenue']))} in net revenue."
        if top_segment is not None
        else "Customer segments could not be calculated because customer-level revenue was unavailable."
    )

    quality_note = (
        f"Data quality review found {len(issue_rows)} issue categories requiring attention before production reporting."
        if not issue_rows.empty
        else "The current quality checks did not find major issues."
    )

    lines = [
        "Management Summary",
        "",
        f"Net revenue is {_format_currency(metrics.get('net_revenue', 0))} across {int(metrics.get('number_of_orders', 0))} valid orders.",
        _trend_sentence(result.monthly_revenue),
        concentration_note,
        product_note,
        segment_note,
        quality_note,
        f"Return rate is {metrics.get('return_rate', 0):.1%}; cancelled order rate is {metrics.get('cancelled_order_rate', 0):.1%}.",
    ]
    return "\n".join(lines)


def generate_manufacturing_management_summary(result: ManufacturingAnalyticsResult) -> str:
    """Create a deterministic summary from manufacturing metrics."""
    metrics = result.metrics
    issue_rows = result.issue_summary[result.issue_summary["row_count"] > 0]
    top_downtime_machine = (
        result.machine_performance.sort_values("downtime_minutes", ascending=False).iloc[0]
        if not result.machine_performance.empty
        else None
    )
    lines = [
        "Manufacturing Management Summary",
        "",
        f"Total valid output is {metrics.get('total_output', 0):,.0f} units with a scrap rate of {metrics.get('scrap_rate') or 0:.1%}.",
        f"Total downtime is {metrics.get('total_downtime_minutes', 0):,.0f} minutes, averaging {metrics.get('average_downtime_per_machine', 0):,.1f} minutes per machine.",
        f"Production attainment is {(metrics.get('production_attainment') or 0):.1%} where planned output is available.",
        f"Quality rate approximation is {(metrics.get('quality_rate_approximation') or 0):.1%}.",
        (
            f"The highest downtime machine is {top_downtime_machine['machine_id']} with {top_downtime_machine['downtime_minutes']:,.0f} downtime minutes."
            if top_downtime_machine is not None
            else "Machine-level downtime cannot be assessed because no valid machine performance rows were available."
        ),
        (
            f"Data quality review found {len(issue_rows)} issue categories requiring attention."
            if not issue_rows.empty
            else "The current quality checks did not find major manufacturing data issues."
        ),
    ]
    if metrics.get("simplified_oee_approximation") is not None:
        lines.insert(5, f"Simplified OEE approximation is {metrics['simplified_oee_approximation']:.1%}; this is not a certified OEE standard.")
    return "\n".join(lines)


def generate_logistics_management_summary(result: LogisticsAnalyticsResult) -> str:
    """Create a deterministic summary from logistics metrics."""
    metrics = result.metrics
    issue_rows = result.issue_summary[result.issue_summary["row_count"] > 0]
    best_carrier = (
        result.carrier_performance.sort_values("on_time_rate", ascending=False).iloc[0]
        if not result.carrier_performance.empty
        else None
    )
    lines = [
        "Logistics Management Summary",
        "",
        f"The active dataset contains {metrics.get('shipment_count', 0):,.0f} valid shipments.",
        f"Average lead time is {metrics.get('average_lead_time_days', 0):,.1f} days and on-time delivery rate is {metrics.get('on_time_delivery_rate', 0):.1%}.",
        f"Delayed shipments total {metrics.get('delayed_shipments', 0):,.0f}, with an average delay of {metrics.get('average_delay_days', 0):,.1f} days.",
        f"Total mapped shipping cost is {_format_currency(metrics.get('total_shipping_cost', 0))}.",
        (
            f"The strongest carrier by on-time rate is {best_carrier['carrier']} at {best_carrier['on_time_rate']:.1%}."
            if best_carrier is not None
            else "Carrier performance cannot be assessed because no usable carrier values were available."
        ),
        (
            f"Data quality review found {len(issue_rows)} logistics issue categories requiring attention."
            if not issue_rows.empty
            else "The current quality checks did not find major logistics data issues."
        ),
    ]
    return "\n".join(lines)


def generate_finance_management_summary(result: FinanceAnalyticsResult) -> str:
    """Create a deterministic summary from finance metrics."""
    metrics = result.metrics
    issue_rows = result.issue_summary[result.issue_summary["row_count"] > 0]
    largest_category = (
        result.category_summary.iloc[0]
        if not result.category_summary.empty
        else None
    )
    lines = [
        "Finance Management Summary",
        "",
        f"Total revenue is {_format_currency(metrics.get('total_revenue', 0))} and total cost is {_format_currency(metrics.get('total_cost', 0))}.",
        f"Net result is {_format_currency(metrics.get('net_result', 0))} with a margin of {metrics.get('margin', 0):.1%}.",
        f"The dataset includes {metrics.get('transaction_count', 0):,.0f} valid finance transactions.",
        f"Budget variance is {_format_currency(metrics.get('budget_variance', 0))} where budget and actual fields are available.",
        (
            f"The largest mapped category is {largest_category['category']} with {_format_currency(float(largest_category['amount']))}."
            if largest_category is not None
            else "Category-level performance cannot be assessed because no valid categories were available."
        ),
        (
            f"Data quality review found {len(issue_rows)} finance issue categories requiring attention."
            if not issue_rows.empty
            else "The current quality checks did not find major finance data issues."
        ),
    ]
    return "\n".join(lines)


def generate_generic_data_summary(df: pd.DataFrame, quality: DataQualityReport, generic_result=None) -> str:
    """Create a generic summary when no mapped domain template is available."""
    duplicate_rows = int(df.duplicated().sum())
    missing_cells = int(df.isna().sum().sum())
    lines = [
        "Generic Data Summary",
        "",
        f"The active dataset has {len(df):,} rows and {len(df.columns):,} columns.",
        f"Data quality score is {quality.overall_score:.1f}/100.",
        f"Missing values total {missing_cells:,} cells and duplicate rows total {duplicate_rows:,}.",
    ]
    if generic_result is not None:
        lines.append(f"The latest generic analytics result used {generic_result.rows_used:,} rows and measures: {', '.join(generic_result.measure_columns)}.")
    lines.extend(
        [
            "",
            "Recommended next actions:",
            "- Review high-missing columns in Data Profile or Data Quality.",
            "- Use Data Preparation for logged cleaning steps.",
            "- Use Generic Analytics for exploratory cuts.",
            "- Map a domain template only when the dataset has clear business fields.",
        ]
    )
    return "\n".join(lines)
