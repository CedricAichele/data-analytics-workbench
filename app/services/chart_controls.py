"""Small helpers for interactive chart controls on analytics pages."""

from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd


def apply_date_range_filter(
    df: pd.DataFrame,
    date_column: str,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    """Filter rows between inclusive date boundaries."""
    if df.empty or date_column not in df.columns:
        return df.copy()
    filtered = df.copy()
    dates = pd.to_datetime(filtered[date_column], errors="coerce")
    mask = dates.notna()
    if start_date is not None:
        mask &= dates.dt.date >= start_date
    if end_date is not None:
        mask &= dates.dt.date <= end_date
    return filtered[mask].copy()


def apply_value_filters(df: pd.DataFrame, filters: dict[str, Iterable[object]]) -> pd.DataFrame:
    """Apply simple inclusion filters while ignoring empty selections."""
    filtered = df.copy()
    for column, selected_values in filters.items():
        values = list(selected_values or [])
        if column in filtered.columns and values:
            filtered = filtered[filtered[column].isin(values)]
    return filtered.copy()


def top_n(df: pd.DataFrame, sort_column: str, n: int, *, ascending: bool = False) -> pd.DataFrame:
    """Return top-N rows by a selected sort column."""
    if df.empty or sort_column not in df.columns:
        return df.copy()
    return df.sort_values(sort_column, ascending=ascending).head(n).copy()


def monthly_sum(df: pd.DataFrame, date_column: str, value_column: str, output_column: str | None = None) -> pd.DataFrame:
    """Aggregate a numeric column by calendar month."""
    if df.empty or date_column not in df.columns or value_column not in df.columns:
        return pd.DataFrame(columns=["period", output_column or value_column])
    data = df.copy()
    data["period"] = pd.to_datetime(data[date_column], errors="coerce").dt.to_period("M").dt.to_timestamp()
    data[value_column] = pd.to_numeric(data[value_column], errors="coerce").fillna(0)
    return (
        data.dropna(subset=["period"])
        .groupby("period", as_index=False)[value_column]
        .sum()
        .rename(columns={value_column: output_column or value_column})
        .sort_values("period")
    )


def download_csv_bytes(df: pd.DataFrame) -> bytes:
    """Return CSV bytes for small controlled chart result exports."""
    return df.to_csv(index=False).encode("utf-8")
