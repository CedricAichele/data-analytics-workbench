"""Generic dataframe profiling functions.

These functions are intentionally domain-neutral and work with any loaded tabular dataframe.
Retail-specific metrics live in app.services.retail_analytics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype, is_string_dtype


@dataclass(frozen=True)
class DataProfile:
    row_count: int
    column_count: int
    columns: list[str]
    dtype_table: pd.DataFrame
    missing_table: pd.DataFrame
    duplicate_row_count: int
    unique_table: pd.DataFrame
    numeric_summary: pd.DataFrame
    categorical_summary: pd.DataFrame
    detected_date_columns: list[str]
    detected_numeric_columns: list[str]
    detected_categorical_columns: list[str]
    data_type_distribution: pd.DataFrame


def _parseable_ratio(series: pd.Series, parser: str) -> float:
    non_null = series.dropna()
    if non_null.empty:
        return 0.0

    if parser == "numeric":
        parsed = pd.to_numeric(non_null, errors="coerce")
    elif parser == "date":
        parsed = _parse_dates(non_null)
    else:
        raise ValueError(f"Unsupported parser: {parser}")

    return float(parsed.notna().mean())


def _parse_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def detect_numeric_columns(df: pd.DataFrame, *, threshold: float = 0.9) -> list[str]:
    """Detect numeric columns, including string columns that are mostly numeric."""
    numeric_columns: list[str] = []
    for column in df.columns:
        series = df[column]
        if is_numeric_dtype(series):
            numeric_columns.append(column)
            continue
        if is_bool_dtype(series):
            continue
        if _parseable_ratio(series, "numeric") >= threshold:
            numeric_columns.append(column)
    return numeric_columns


def detect_date_like_columns(df: pd.DataFrame, *, threshold: float = 0.75) -> list[str]:
    """Detect columns that can plausibly be parsed as dates."""
    date_columns: list[str] = []
    for column in df.columns:
        series = df[column]
        if is_datetime64_any_dtype(series):
            date_columns.append(column)
            continue
        if is_numeric_dtype(series) or is_bool_dtype(series):
            continue
        if _parseable_ratio(series, "date") >= threshold:
            date_columns.append(column)
    return date_columns


def detect_categorical_columns(
    df: pd.DataFrame,
    numeric_columns: list[str] | None = None,
    date_columns: list[str] | None = None,
) -> list[str]:
    """Detect likely categorical columns for generic profiling charts."""
    numeric_columns = numeric_columns or detect_numeric_columns(df)
    date_columns = date_columns or detect_date_like_columns(df)
    excluded = set(numeric_columns) | set(date_columns)
    categorical_columns: list[str] = []
    for column in df.columns:
        if column in excluded:
            continue
        series = df[column]
        if is_bool_dtype(series) or series.dtype == "object" or is_string_dtype(series):
            categorical_columns.append(column)
    return categorical_columns


def build_missing_table(df: pd.DataFrame) -> pd.DataFrame:
    missing_count = df.isna().sum()
    missing_percentage = (missing_count / max(len(df), 1) * 100).round(2)
    return pd.DataFrame(
        {
            "column": missing_count.index,
            "missing_count": missing_count.values,
            "missing_percentage": missing_percentage.values,
        }
    ).sort_values(["missing_count", "column"], ascending=[False, True])


def build_dtype_table(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "column": df.columns,
            "detected_dtype": [str(dtype) for dtype in df.dtypes],
        }
    )


def build_unique_table(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "column": df.columns,
            "unique_values": [df[column].nunique(dropna=True) for column in df.columns],
        }
    ).sort_values(["unique_values", "column"], ascending=[False, True])


def build_numeric_summary(df: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    if not numeric_columns:
        return pd.DataFrame(columns=["column", "count", "mean", "std", "min", "25%", "50%", "75%", "max"])

    numeric_df = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    summary = numeric_df.describe().transpose().reset_index(names="column")
    return summary.round(2)


def build_categorical_summary(df: pd.DataFrame, categorical_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in categorical_columns:
        counts = df[column].value_counts(dropna=True)
        if counts.empty:
            most_common = pd.NA
            most_common_count = 0
        else:
            most_common = counts.index[0]
            most_common_count = int(counts.iloc[0])
        rows.append(
            {
                "column": column,
                "unique_values": int(df[column].nunique(dropna=True)),
                "most_common": most_common,
                "most_common_count": most_common_count,
            }
        )
    return pd.DataFrame(rows)


def profile_dataframe(df: pd.DataFrame) -> DataProfile:
    """Create a transparent, generic profile for any dataframe."""
    numeric_columns = detect_numeric_columns(df)
    date_columns = detect_date_like_columns(df)
    categorical_columns = detect_categorical_columns(df, numeric_columns, date_columns)
    dtype_table = build_dtype_table(df)

    data_type_distribution = (
        dtype_table["detected_dtype"]
        .value_counts()
        .reset_index()
        .rename(columns={"detected_dtype": "dtype", "count": "column_count"})
    )

    return DataProfile(
        row_count=len(df),
        column_count=len(df.columns),
        columns=list(df.columns),
        dtype_table=dtype_table,
        missing_table=build_missing_table(df),
        duplicate_row_count=int(df.duplicated().sum()),
        unique_table=build_unique_table(df),
        numeric_summary=build_numeric_summary(df, numeric_columns),
        categorical_summary=build_categorical_summary(df, categorical_columns),
        detected_date_columns=date_columns,
        detected_numeric_columns=numeric_columns,
        detected_categorical_columns=categorical_columns,
        data_type_distribution=data_type_distribution,
    )
