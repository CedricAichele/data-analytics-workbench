"""Manufacturing-specific cleaning and KPI analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.config import ALL_MANUFACTURING_FIELDS


@dataclass(frozen=True)
class ManufacturingCleanResult:
    prepared_operations: pd.DataFrame
    analysis_rows: pd.DataFrame
    issue_summary: pd.DataFrame


@dataclass(frozen=True)
class ManufacturingAnalyticsResult:
    metrics: dict[str, float | None]
    machine_performance: pd.DataFrame
    output_over_time: pd.DataFrame
    downtime_over_time: pd.DataFrame
    output_by_line: pd.DataFrame
    output_by_shift: pd.DataFrame
    issue_summary: pd.DataFrame


def _parse_mixed_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def _clean_text(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.replace("", pd.NA)


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def prepare_manufacturing_operations(df: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    """Standardize a mapped manufacturing dataframe without mutating the source."""
    prepared = pd.DataFrame(index=df.index)
    for field in ALL_MANUFACTURING_FIELDS:
        source_column = mapping.get(field)
        if source_column and source_column in df.columns:
            prepared[field] = df[source_column]
        else:
            prepared[field] = pd.NA

    prepared["original_timestamp"] = prepared["timestamp"]
    prepared["timestamp"] = _parse_mixed_dates(prepared["timestamp"])
    for field in ["machine_id", "line", "shift", "product", "quality_status"]:
        prepared[field] = _clean_text(prepared[field])
    for field in ["actual_output", "scrap_count", "downtime_minutes", "planned_output", "runtime_minutes"]:
        prepared[field] = _to_numeric(prepared[field])

    duplicate_columns = [
        "timestamp",
        "machine_id",
        "line",
        "shift",
        "product",
        "planned_output",
        "actual_output",
        "scrap_count",
        "downtime_minutes",
        "runtime_minutes",
        "quality_status",
    ]
    prepared["is_duplicate_row"] = prepared.duplicated(subset=duplicate_columns, keep="first")
    prepared["is_missing_machine"] = prepared["machine_id"].isna()
    prepared["is_invalid_timestamp"] = prepared["original_timestamp"].notna() & prepared["timestamp"].isna()
    prepared["is_invalid_output"] = prepared["actual_output"].isna() | (prepared["actual_output"] < 0)
    prepared["is_invalid_scrap"] = prepared["scrap_count"].isna() | (prepared["scrap_count"] < 0)
    prepared["is_high_scrap"] = (prepared["actual_output"] > 0) & (prepared["scrap_count"] / prepared["actual_output"] > 0.15)
    prepared["is_invalid_downtime"] = prepared["downtime_minutes"].isna() | (prepared["downtime_minutes"] < 0)
    prepared["is_zero_planned_output"] = prepared["planned_output"].notna() & (prepared["planned_output"] <= 0)
    prepared["is_missing_shift"] = prepared["shift"].isna()
    prepared["is_analysis_valid"] = (
        prepared["timestamp"].notna()
        & prepared["machine_id"].notna()
        & ~prepared["is_invalid_output"]
        & ~prepared["is_invalid_scrap"]
        & ~prepared["is_invalid_downtime"]
        & ~prepared["is_duplicate_row"]
    )
    return prepared


def build_issue_summary(prepared: pd.DataFrame) -> pd.DataFrame:
    """Summarize manufacturing data quality flags."""
    checks = [
        ("Duplicate rows", int(prepared["is_duplicate_row"].sum()), "Medium", "Duplicate production records are excluded from KPI calculations."),
        ("Missing machine IDs", int(prepared["is_missing_machine"].sum()), "High", "Rows cannot be attributed to a machine and are excluded from KPI calculations."),
        ("Timestamp parsing issues", int(prepared["is_invalid_timestamp"].sum()), "High", "Rows are excluded from time-series analytics until timestamps are corrected."),
        ("Invalid output values", int(prepared["is_invalid_output"].sum()), "High", "Rows are excluded from output KPIs."),
        ("Invalid scrap values", int(prepared["is_invalid_scrap"].sum()), "High", "Rows are excluded from scrap KPIs."),
        ("High scrap observations", int(prepared["is_high_scrap"].sum()), "Business review", "Rows are retained but should be investigated."),
        ("Invalid downtime values", int(prepared["is_invalid_downtime"].sum()), "High", "Rows are excluded from downtime KPIs."),
        ("Zero or missing planned output", int(prepared["is_zero_planned_output"].sum()), "Medium", "Rows are excluded from attainment calculations."),
        ("Missing shift values", int(prepared["is_missing_shift"].sum()), "Low", "Rows remain in core KPIs but are not useful for shift cuts."),
    ]
    return pd.DataFrame(checks, columns=["issue", "row_count", "severity", "analysis_handling"])


def clean_manufacturing_operations(df: pd.DataFrame, mapping: dict[str, str | None]) -> ManufacturingCleanResult:
    """Prepare and flag manufacturing records for analytics."""
    prepared = prepare_manufacturing_operations(df, mapping)
    issue_summary = build_issue_summary(prepared)
    analysis_rows = prepared[prepared["is_analysis_valid"]].copy()
    return ManufacturingCleanResult(
        prepared_operations=prepared,
        analysis_rows=analysis_rows,
        issue_summary=issue_summary,
    )


def _safe_rate(numerator: float, denominator: float) -> float | None:
    if denominator <= 0 or pd.isna(denominator):
        return None
    return round(float(numerator) / float(denominator), 4)


def _safe_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)


def calculate_manufacturing_kpis(rows: pd.DataFrame) -> dict[str, float | None]:
    """Calculate headline manufacturing KPIs from valid analysis rows."""
    total_output = _safe_float(rows["actual_output"].sum()) if not rows.empty else 0.0
    total_scrap = _safe_float(rows["scrap_count"].sum()) if not rows.empty else 0.0
    total_downtime = _safe_float(rows["downtime_minutes"].sum()) if not rows.empty else 0.0
    machine_count = rows["machine_id"].nunique(dropna=True) if not rows.empty else 0

    metrics: dict[str, float | None] = {
        "total_output": round(total_output, 2),
        "total_scrap": round(total_scrap, 2),
        "scrap_rate": _safe_rate(total_scrap, total_output),
        "total_downtime_minutes": round(total_downtime, 2),
        "average_downtime_per_machine": round(total_downtime / machine_count, 2) if machine_count else 0.0,
        "production_attainment": None,
        "availability_approximation": None,
        "quality_rate_approximation": _safe_rate(total_output - total_scrap, total_output),
        "simplified_oee_approximation": None,
    }

    planned_rows = rows[rows["planned_output"].notna() & (rows["planned_output"] > 0)]
    planned_output = _safe_float(planned_rows["planned_output"].sum()) if not planned_rows.empty else 0.0
    if planned_output:
        metrics["production_attainment"] = _safe_rate(_safe_float(planned_rows["actual_output"].sum()), planned_output)

    runtime_rows = rows[rows["runtime_minutes"].notna() & (rows["runtime_minutes"] >= 0)]
    runtime_total = _safe_float(runtime_rows["runtime_minutes"].sum()) if not runtime_rows.empty else 0.0
    downtime_for_runtime = _safe_float(runtime_rows["downtime_minutes"].sum()) if not runtime_rows.empty else 0.0
    if runtime_total + downtime_for_runtime > 0:
        metrics["availability_approximation"] = _safe_rate(runtime_total, runtime_total + downtime_for_runtime)

    if (
        metrics["production_attainment"] is not None
        and metrics["availability_approximation"] is not None
        and metrics["quality_rate_approximation"] is not None
    ):
        metrics["simplified_oee_approximation"] = round(
            metrics["production_attainment"]
            * metrics["availability_approximation"]
            * metrics["quality_rate_approximation"],
            4,
        )
    return metrics


def build_machine_performance(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(columns=["machine_id", "total_output", "total_scrap", "scrap_rate", "downtime_minutes", "record_count"])
    machine = (
        rows.groupby("machine_id", as_index=False)
        .agg(
            total_output=("actual_output", "sum"),
            total_scrap=("scrap_count", "sum"),
            downtime_minutes=("downtime_minutes", "sum"),
            record_count=("machine_id", "size"),
        )
    )
    machine["scrap_rate"] = np.where(
        machine["total_output"] > 0,
        machine["total_scrap"] / machine["total_output"],
        0,
    )
    return machine.sort_values(["downtime_minutes", "scrap_rate"], ascending=False).round(4)


def _time_series(rows: pd.DataFrame, value_column: str, output_column: str) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(columns=["period", output_column])
    data = rows.copy()
    data["period"] = data["timestamp"].dt.to_period("D").dt.to_timestamp()
    return (
        data.groupby("period", as_index=False)[value_column]
        .sum()
        .rename(columns={value_column: output_column})
        .sort_values("period")
    )


def _optional_group(rows: pd.DataFrame, group_column: str) -> pd.DataFrame:
    if rows.empty or rows[group_column].dropna().empty:
        return pd.DataFrame(columns=[group_column, "actual_output"])
    return (
        rows.dropna(subset=[group_column])
        .groupby(group_column, as_index=False)["actual_output"]
        .sum()
        .sort_values("actual_output", ascending=False)
    )


def build_manufacturing_analytics(clean_result: ManufacturingCleanResult) -> ManufacturingAnalyticsResult:
    """Build manufacturing metrics, charts, and issue summaries."""
    rows = clean_result.analysis_rows
    return ManufacturingAnalyticsResult(
        metrics=calculate_manufacturing_kpis(rows),
        machine_performance=build_machine_performance(rows),
        output_over_time=_time_series(rows, "actual_output", "actual_output"),
        downtime_over_time=_time_series(rows, "downtime_minutes", "downtime_minutes"),
        output_by_line=_optional_group(rows, "line"),
        output_by_shift=_optional_group(rows, "shift"),
        issue_summary=clean_result.issue_summary,
    )
