"""Finance-specific cleaning and KPI analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.config import ALL_FINANCE_FIELDS


@dataclass(frozen=True)
class FinanceCleanResult:
    prepared_transactions: pd.DataFrame
    analysis_rows: pd.DataFrame
    issue_summary: pd.DataFrame


@dataclass(frozen=True)
class FinanceAnalyticsResult:
    metrics: dict[str, float]
    monthly_summary: pd.DataFrame
    category_summary: pd.DataFrame
    cost_center_summary: pd.DataFrame
    largest_transactions: pd.DataFrame
    issue_summary: pd.DataFrame


REVENUE_TYPES = {"revenue", "income", "sales"}
COST_TYPES = {"cost", "expense", "spend", "cogs"}


def _parse_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def _clean_text(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.replace("", pd.NA)


def _normalize_type(value: Any) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in REVENUE_TYPES:
        return "revenue"
    if normalized in COST_TYPES:
        return "cost"
    return None


def prepare_finance_transactions(df: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    """Standardize mapped finance columns and normalize transaction type."""
    prepared = pd.DataFrame(index=df.index)
    for field in ALL_FINANCE_FIELDS:
        source_column = mapping.get(field)
        prepared[field] = df[source_column] if source_column and source_column in df.columns else pd.NA

    for field in ["transaction_id", "type", "category", "account", "cost_center"]:
        prepared[field] = _clean_text(prepared[field])
    prepared["original_date"] = prepared["date"]
    prepared["date"] = _parse_dates(prepared["date"])
    for field in ["amount", "budget", "actual"]:
        prepared[field] = pd.to_numeric(prepared[field], errors="coerce")

    prepared["normalized_type"] = prepared["type"].map(_normalize_type)
    duplicate_columns = ALL_FINANCE_FIELDS
    prepared["is_duplicate_row"] = prepared.duplicated(subset=duplicate_columns, keep="first")
    prepared["is_invalid_date"] = prepared["original_date"].notna() & prepared["date"].isna()
    prepared["is_invalid_amount"] = prepared["amount"].isna()
    prepared["is_zero_amount"] = prepared["amount"].fillna(0) == 0
    prepared["is_uninterpretable_type"] = prepared["normalized_type"].isna()
    prepared["is_missing_category"] = prepared["category"].isna()
    prepared["abs_amount"] = prepared["amount"].abs()
    prepared["signed_result"] = prepared.apply(
        lambda row: row["abs_amount"] if row["normalized_type"] == "revenue" else -row["abs_amount"],
        axis=1,
    )
    prepared["is_analysis_valid"] = (
        prepared["transaction_id"].notna()
        & prepared["date"].notna()
        & ~prepared["is_invalid_amount"]
        & ~prepared["is_zero_amount"]
        & ~prepared["is_uninterpretable_type"]
        & ~prepared["is_duplicate_row"]
    )
    return prepared


def build_issue_summary(prepared: pd.DataFrame) -> pd.DataFrame:
    checks = [
        ("Duplicate rows", int(prepared["is_duplicate_row"].sum()), "Medium", "Duplicate transactions are excluded from KPI calculations."),
        ("Date parsing issues", int(prepared["is_invalid_date"].sum()), "High", "Rows are excluded from time-series analytics."),
        ("Invalid amounts", int(prepared["is_invalid_amount"].sum()), "High", "Rows are excluded from KPI calculations."),
        ("Zero amounts", int(prepared["is_zero_amount"].sum()), "Medium", "Rows are excluded from financial totals."),
        ("Uninterpretable type values", int(prepared["is_uninterpretable_type"].sum()), "High", "Rows are excluded because revenue/cost meaning is ambiguous."),
        ("Missing categories", int(prepared["is_missing_category"].sum()), "Low", "Rows remain in totals but are less useful for category reporting."),
    ]
    return pd.DataFrame(checks, columns=["issue", "row_count", "severity", "analysis_handling"])


def clean_finance_transactions(df: pd.DataFrame, mapping: dict[str, str | None]) -> FinanceCleanResult:
    prepared = prepare_finance_transactions(df, mapping)
    return FinanceCleanResult(
        prepared_transactions=prepared,
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


def calculate_finance_kpis(rows: pd.DataFrame) -> dict[str, float]:
    revenue = _safe_float(rows.loc[rows["normalized_type"] == "revenue", "abs_amount"].sum()) if not rows.empty else 0.0
    cost = _safe_float(rows.loc[rows["normalized_type"] == "cost", "abs_amount"].sum()) if not rows.empty else 0.0
    net_result = revenue - cost
    valid_budget = rows["budget"].notna() & rows["actual"].notna() if not rows.empty else pd.Series(dtype=bool)
    budget_variance = _safe_float((rows.loc[valid_budget, "actual"] - rows.loc[valid_budget, "budget"]).sum()) if valid_budget.any() else 0.0
    return {
        "total_revenue": round(revenue, 2),
        "total_cost": round(cost, 2),
        "net_result": round(net_result, 2),
        "margin": round(net_result / revenue, 4) if revenue else 0.0,
        "transaction_count": float(len(rows)),
        "average_transaction_amount": round(_safe_float(rows["abs_amount"].mean()) if not rows.empty else 0, 2),
        "budget_variance": round(budget_variance, 2),
    }


def build_finance_analytics(clean_result: FinanceCleanResult) -> FinanceAnalyticsResult:
    rows = clean_result.analysis_rows.copy()
    if rows.empty:
        empty = pd.DataFrame()
        return FinanceAnalyticsResult(
            metrics=calculate_finance_kpis(rows),
            monthly_summary=empty,
            category_summary=empty,
            cost_center_summary=empty,
            largest_transactions=empty,
            issue_summary=clean_result.issue_summary,
        )

    rows["month"] = rows["date"].dt.to_period("M").dt.to_timestamp()
    monthly_summary = (
        rows.pivot_table(index="month", columns="normalized_type", values="abs_amount", aggfunc="sum", fill_value=0)
        .reset_index()
        .rename_axis(None, axis=1)
    )
    if "revenue" not in monthly_summary.columns:
        monthly_summary["revenue"] = 0.0
    if "cost" not in monthly_summary.columns:
        monthly_summary["cost"] = 0.0
    monthly_summary["net_result"] = monthly_summary["revenue"] - monthly_summary["cost"]

    category_summary = (
        rows.assign(category=rows["category"].fillna("Missing"))
        .groupby(["category", "normalized_type"], as_index=False)
        .agg(amount=("abs_amount", "sum"), transaction_count=("transaction_id", "nunique"))
        .sort_values("amount", ascending=False)
    )
    cost_center_summary = (
        rows.assign(cost_center=rows["cost_center"].fillna("Missing"))
        .groupby("cost_center", as_index=False)
        .agg(
            revenue=("abs_amount", lambda s: s[rows.loc[s.index, "normalized_type"] == "revenue"].sum()),
            cost=("abs_amount", lambda s: s[rows.loc[s.index, "normalized_type"] == "cost"].sum()),
            transaction_count=("transaction_id", "nunique"),
        )
    )
    cost_center_summary["net_result"] = cost_center_summary["revenue"] - cost_center_summary["cost"]
    largest_transactions = rows.sort_values("abs_amount", ascending=False).head(25)

    return FinanceAnalyticsResult(
        metrics=calculate_finance_kpis(rows),
        monthly_summary=_round_numeric(monthly_summary, 2),
        category_summary=_round_numeric(category_summary, 2),
        cost_center_summary=_round_numeric(cost_center_summary, 2),
        largest_transactions=largest_transactions,
        issue_summary=clean_result.issue_summary,
    )
