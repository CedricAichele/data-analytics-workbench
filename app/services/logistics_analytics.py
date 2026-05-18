"""Logistics-specific cleaning and KPI analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.config import ALL_LOGISTICS_FIELDS


@dataclass(frozen=True)
class LogisticsCleanResult:
    prepared_shipments: pd.DataFrame
    analysis_rows: pd.DataFrame
    issue_summary: pd.DataFrame


@dataclass(frozen=True)
class LogisticsAnalyticsResult:
    metrics: dict[str, float]
    shipments_over_time: pd.DataFrame
    lead_time_over_time: pd.DataFrame
    status_summary: pd.DataFrame
    carrier_performance: pd.DataFrame
    destination_performance: pd.DataFrame
    delayed_shipments: pd.DataFrame
    issue_summary: pd.DataFrame


def _parse_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def _clean_text(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.replace("", pd.NA)


def prepare_logistics_shipments(df: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    """Standardize mapped logistics columns and derive shipment timing fields."""
    prepared = pd.DataFrame(index=df.index)
    for field in ALL_LOGISTICS_FIELDS:
        source_column = mapping.get(field)
        prepared[field] = df[source_column] if source_column and source_column in df.columns else pd.NA

    for field in ["shipment_id", "carrier", "origin", "destination", "delivery_status"]:
        prepared[field] = _clean_text(prepared[field])
    for field in ["order_date", "delivery_date", "planned_delivery_date"]:
        prepared[f"original_{field}"] = prepared[field]
        prepared[field] = _parse_dates(prepared[field])
    prepared["shipping_cost"] = pd.to_numeric(prepared["shipping_cost"], errors="coerce")

    duplicate_columns = ALL_LOGISTICS_FIELDS
    prepared["is_duplicate_row"] = prepared.duplicated(subset=duplicate_columns, keep="first")
    prepared["is_missing_carrier"] = prepared["carrier"].isna()
    prepared["is_missing_delivery_date"] = prepared["delivery_date"].isna()
    prepared["is_invalid_order_date"] = prepared["original_order_date"].notna() & prepared["order_date"].isna()
    prepared["is_invalid_planned_delivery_date"] = (
        prepared["original_planned_delivery_date"].notna() & prepared["planned_delivery_date"].isna()
    )
    prepared["lead_time_days"] = (prepared["delivery_date"] - prepared["order_date"]).dt.days
    prepared["delay_days"] = (prepared["delivery_date"] - prepared["planned_delivery_date"]).dt.days
    prepared["is_on_time"] = prepared["delay_days"] <= 0
    prepared["is_high_shipping_cost"] = False
    valid_costs = prepared["shipping_cost"].dropna()
    if not valid_costs.empty:
        threshold = valid_costs.quantile(0.98)
        prepared["is_high_shipping_cost"] = prepared["shipping_cost"] > threshold
    prepared["is_analysis_valid"] = (
        prepared["shipment_id"].notna()
        & prepared["order_date"].notna()
        & prepared["delivery_date"].notna()
        & prepared["planned_delivery_date"].notna()
        & ~prepared["is_duplicate_row"]
    )
    return prepared


def build_issue_summary(prepared: pd.DataFrame) -> pd.DataFrame:
    checks = [
        ("Duplicate rows", int(prepared["is_duplicate_row"].sum()), "Medium", "Duplicate shipments are excluded from KPI calculations."),
        ("Missing carrier", int(prepared["is_missing_carrier"].sum()), "Low", "Rows remain in core KPIs but are not useful for carrier cuts."),
        ("Missing delivery dates", int(prepared["is_missing_delivery_date"].sum()), "High", "Rows are excluded from lead-time and on-time metrics."),
        ("Order date parsing issues", int(prepared["is_invalid_order_date"].sum()), "High", "Rows are excluded from time-based shipment analytics."),
        ("Planned delivery date parsing issues", int(prepared["is_invalid_planned_delivery_date"].sum()), "High", "Rows are excluded from delay metrics."),
        ("High shipping cost outliers", int(prepared["is_high_shipping_cost"].sum()), "Business review", "Rows are retained but should be reviewed."),
    ]
    return pd.DataFrame(checks, columns=["issue", "row_count", "severity", "analysis_handling"])


def clean_logistics_shipments(df: pd.DataFrame, mapping: dict[str, str | None]) -> LogisticsCleanResult:
    prepared = prepare_logistics_shipments(df, mapping)
    return LogisticsCleanResult(
        prepared_shipments=prepared,
        analysis_rows=prepared[prepared["is_analysis_valid"]].copy(),
        issue_summary=build_issue_summary(prepared),
    )


def _safe_float(value: Any) -> float:
    return 0.0 if pd.isna(value) else float(value)


def _round_numeric(df: pd.DataFrame, decimals: int = 2) -> pd.DataFrame:
    rounded = df.copy()
    numeric_columns = rounded.select_dtypes(include="number").columns
    rounded[numeric_columns] = rounded[numeric_columns].round(decimals)
    return rounded


def calculate_logistics_kpis(rows: pd.DataFrame) -> dict[str, float]:
    shipment_count = int(rows["shipment_id"].nunique()) if not rows.empty else 0
    delayed_shipments = int((rows["delay_days"] > 0).sum()) if not rows.empty else 0
    on_time_rate = float(rows["is_on_time"].mean()) if not rows.empty else 0.0
    valid_costs = rows["shipping_cost"].dropna() if "shipping_cost" in rows else pd.Series(dtype=float)
    total_cost = _safe_float(valid_costs.sum()) if not valid_costs.empty else 0.0
    return {
        "shipment_count": float(shipment_count),
        "average_lead_time_days": round(_safe_float(rows["lead_time_days"].mean()) if not rows.empty else 0, 2),
        "on_time_delivery_rate": round(on_time_rate, 4),
        "delayed_shipments": float(delayed_shipments),
        "average_delay_days": round(_safe_float(rows.loc[rows["delay_days"] > 0, "delay_days"].mean()) if delayed_shipments else 0, 2),
        "total_shipping_cost": round(total_cost, 2),
        "average_cost_per_shipment": round(total_cost / shipment_count, 2) if shipment_count else 0.0,
    }


def build_logistics_analytics(clean_result: LogisticsCleanResult) -> LogisticsAnalyticsResult:
    rows = clean_result.analysis_rows.copy()
    if rows.empty:
        empty = pd.DataFrame()
        return LogisticsAnalyticsResult(
            metrics=calculate_logistics_kpis(rows),
            shipments_over_time=empty,
            lead_time_over_time=empty,
            status_summary=empty,
            carrier_performance=empty,
            destination_performance=empty,
            delayed_shipments=empty,
            issue_summary=clean_result.issue_summary,
        )

    rows["order_month"] = rows["order_date"].dt.to_period("M").dt.to_timestamp()
    shipments_over_time = rows.groupby("order_month", as_index=False).agg(shipment_count=("shipment_id", "nunique"))
    lead_time_over_time = rows.groupby("order_month", as_index=False).agg(average_lead_time_days=("lead_time_days", "mean"))
    status_summary = (
        rows.assign(delivery_result=rows["is_on_time"].map({True: "On time", False: "Delayed"}))
        .groupby("delivery_result", as_index=False)
        .agg(shipments=("shipment_id", "nunique"))
    )
    carrier_performance = (
        rows.dropna(subset=["carrier"])
        .groupby("carrier", as_index=False)
        .agg(
            shipment_count=("shipment_id", "nunique"),
            average_lead_time_days=("lead_time_days", "mean"),
            average_delay_days=("delay_days", lambda s: s[s > 0].mean() if (s > 0).any() else 0),
            on_time_rate=("is_on_time", "mean"),
            total_shipping_cost=("shipping_cost", "sum"),
        )
        .sort_values("shipment_count", ascending=False)
    )
    destination_performance = (
        rows.dropna(subset=["destination"])
        .groupby("destination", as_index=False)
        .agg(
            shipment_count=("shipment_id", "nunique"),
            delayed_shipments=("delay_days", lambda s: int((s > 0).sum())),
            average_delay_days=("delay_days", lambda s: s[s > 0].mean() if (s > 0).any() else 0),
        )
        .sort_values("shipment_count", ascending=False)
    )
    delayed_shipments = rows[rows["delay_days"] > 0].sort_values("delay_days", ascending=False)
    return LogisticsAnalyticsResult(
        metrics=calculate_logistics_kpis(rows),
        shipments_over_time=_round_numeric(shipments_over_time, 2),
        lead_time_over_time=_round_numeric(lead_time_over_time, 2),
        status_summary=status_summary,
        carrier_performance=_round_numeric(carrier_performance, 4),
        destination_performance=_round_numeric(destination_performance, 2),
        delayed_shipments=delayed_shipments,
        issue_summary=clean_result.issue_summary,
    )
