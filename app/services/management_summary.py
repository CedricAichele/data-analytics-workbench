"""Deterministic management summary generation."""

from __future__ import annotations

import pandas as pd

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


def generate_llm_summary_placeholder(*args, enabled: bool = False, **kwargs) -> str:
    """Placeholder for a future LLM-based summary integration.

    The MVP intentionally avoids API keys and external LLM calls. A future
    implementation could pass deterministic metrics into a secured LLM service
    only when explicitly enabled by the user.
    """
    if not enabled:
        return "LLM summary generation is disabled in the MVP."
    raise NotImplementedError("LLM-based summaries are intentionally not implemented in this MVP.")

