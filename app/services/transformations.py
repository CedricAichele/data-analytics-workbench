"""Reusable dataframe transformation functions for the preparation workflow."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype


SUPPORTED_TARGET_TYPES = {"string", "integer", "float", "datetime", "boolean"}
SUPPORTED_MISSING_STRATEGIES = {"fill_numeric_zero", "fill_numeric_median", "fill_text_unknown", "drop_rows"}
SUPPORTED_FILTER_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "greater_than",
    "greater_or_equal",
    "less_than",
    "less_or_equal",
}


def _require_column(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        raise ValueError(f"Column not found: {column}")


def _parse_datetime(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def rename_column(df: pd.DataFrame, old_name: str, new_name: str) -> pd.DataFrame:
    """Return a copy of df with one column renamed."""
    _require_column(df, old_name)
    cleaned_name = new_name.strip()
    if not cleaned_name:
        raise ValueError("New column name cannot be blank.")
    if cleaned_name != old_name and cleaned_name in df.columns:
        raise ValueError(f"Column already exists: {cleaned_name}")
    return df.copy().rename(columns={old_name: cleaned_name})


def drop_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Return a copy of df without the selected columns."""
    selected = list(columns)
    if not selected:
        raise ValueError("Select at least one column to drop.")
    missing = [column for column in selected if column not in df.columns]
    if missing:
        raise ValueError(f"Columns not found: {', '.join(missing)}")
    return df.copy().drop(columns=selected)


def change_column_type(df: pd.DataFrame, column: str, target_type: str) -> pd.DataFrame:
    """Return a copy of df with a selected column converted to a supported type."""
    _require_column(df, column)
    if target_type not in SUPPORTED_TARGET_TYPES:
        raise ValueError(f"Unsupported target type: {target_type}")

    transformed = df.copy()
    if target_type == "string":
        transformed[column] = transformed[column].astype("string")
    elif target_type == "integer":
        transformed[column] = pd.to_numeric(transformed[column], errors="coerce").round().astype("Int64")
    elif target_type == "float":
        transformed[column] = pd.to_numeric(transformed[column], errors="coerce")
    elif target_type == "datetime":
        transformed[column] = _parse_datetime(transformed[column])
    elif target_type == "boolean":
        transformed[column] = _convert_to_boolean(transformed[column])
    return transformed


def _convert_to_boolean(series: pd.Series) -> pd.Series:
    if is_bool_dtype(series):
        return series.astype("boolean")

    truthy = {"true", "t", "yes", "y", "1"}
    falsy = {"false", "f", "no", "n", "0"}

    def convert(value: Any) -> Any:
        if pd.isna(value):
            return pd.NA
        normalized = str(value).strip().lower()
        if normalized in truthy:
            return True
        if normalized in falsy:
            return False
        return pd.NA

    return series.map(convert).astype("boolean")


def parse_datetime_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return a copy of df with a selected column parsed as datetime."""
    _require_column(df, column)
    transformed = df.copy()
    transformed[column] = _parse_datetime(transformed[column])
    return transformed


def remove_duplicate_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with exact duplicate rows removed, keeping the first row."""
    return df.copy().drop_duplicates().reset_index(drop=True)


def fill_missing_values(df: pd.DataFrame, column: str, strategy: str) -> pd.DataFrame:
    """Return a copy of df after applying a supported missing-value strategy."""
    _require_column(df, column)
    if strategy not in SUPPORTED_MISSING_STRATEGIES:
        raise ValueError(f"Unsupported missing value strategy: {strategy}")
    if strategy == "drop_rows":
        return drop_missing_rows(df, column)

    transformed = df.copy()
    if strategy == "fill_numeric_zero":
        numeric = pd.to_numeric(transformed[column], errors="coerce")
        transformed[column] = numeric.fillna(0)
    elif strategy == "fill_numeric_median":
        numeric = pd.to_numeric(transformed[column], errors="coerce")
        median = numeric.median()
        if pd.isna(median):
            raise ValueError(f"Cannot calculate a numeric median for column: {column}")
        transformed[column] = numeric.fillna(median)
    elif strategy == "fill_text_unknown":
        transformed[column] = transformed[column].astype("string").fillna("Unknown")
    return transformed


def drop_missing_rows(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return a copy of df after removing rows with missing values in one column."""
    _require_column(df, column)
    return df.copy().dropna(subset=[column]).reset_index(drop=True)


def filter_rows(df: pd.DataFrame, column: str, operator: str, value: Any) -> pd.DataFrame:
    """Return a copy of df filtered by a simple comparison operator."""
    _require_column(df, column)
    if operator not in SUPPORTED_FILTER_OPERATORS:
        raise ValueError(f"Unsupported filter operator: {operator}")

    series = df[column]
    if operator == "contains":
        mask = series.astype("string").str.contains(str(value), case=False, na=False, regex=False)
    elif operator in {"equals", "not_equals"}:
        mask = _equals_mask(series, value)
        if operator == "not_equals":
            mask = ~mask
    else:
        mask = _comparison_mask(series, operator, value)

    return df.loc[mask].copy().reset_index(drop=True)


def _equals_mask(series: pd.Series, value: Any) -> pd.Series:
    if is_numeric_dtype(series):
        numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.isna(numeric_value):
            return pd.Series(False, index=series.index)
        return pd.to_numeric(series, errors="coerce") == numeric_value
    return series.astype("string") == str(value)


def _comparison_mask(series: pd.Series, operator: str, value: Any) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce")
    numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric_value):
        raise ValueError("Comparison filters require a numeric comparison value.")

    if operator == "greater_than":
        return numeric_series > numeric_value
    if operator == "greater_or_equal":
        return numeric_series >= numeric_value
    if operator == "less_than":
        return numeric_series < numeric_value
    if operator == "less_or_equal":
        return numeric_series <= numeric_value
    raise ValueError(f"Unsupported comparison operator: {operator}")


def create_revenue_column(
    df: pd.DataFrame,
    quantity_column: str,
    unit_price_column: str,
    revenue_column: str = "revenue",
) -> pd.DataFrame:
    """Return a copy of df with revenue = quantity * unit price."""
    _require_column(df, quantity_column)
    _require_column(df, unit_price_column)
    output_column = revenue_column.strip() or "revenue"
    transformed = df.copy()
    quantity = pd.to_numeric(transformed[quantity_column], errors="coerce")
    unit_price = pd.to_numeric(transformed[unit_price_column], errors="coerce")
    transformed[output_column] = quantity * unit_price
    return transformed


def create_transformation_log_entry(action: str, details: str) -> str:
    """Create a concise, human-readable transformation log entry."""
    return f"{action}: {details}"
