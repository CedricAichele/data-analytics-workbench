"""Generic exploratory analytics for any tabular dataframe."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


AGGREGATIONS = {
    "sum": "sum",
    "average": "mean",
    "count": "count",
    "min": "min",
    "max": "max",
}


@dataclass(frozen=True)
class GenericAnalyticsResult:
    aggregated: pd.DataFrame
    insights: list[str]
    rows_used: int


def get_numeric_columns(df: pd.DataFrame) -> list[str]:
    """Return columns that can reasonably be used as numeric measures."""
    columns: list[str] = []
    for column in df.columns:
        parsed = pd.to_numeric(df[column], errors="coerce")
        if parsed.notna().sum() > 0:
            columns.append(column)
    return columns


def get_categorical_columns(df: pd.DataFrame) -> list[str]:
    """Return likely categorical columns for optional grouping."""
    return [
        column
        for column in df.columns
        if df[column].dtype == "object" or str(df[column].dtype).startswith("string") or df[column].nunique(dropna=True) <= 50
    ]


def get_date_columns(df: pd.DataFrame) -> list[str]:
    """Return columns with enough parseable date values for optional time grouping."""
    date_columns: list[str] = []
    for column in df.columns:
        if pd.api.types.is_numeric_dtype(df[column]) or pd.api.types.is_bool_dtype(df[column]):
            continue
        parsed = _parse_dates(df[column])
        non_null = df[column].dropna()
        if not non_null.empty and parsed.notna().sum() / len(non_null) >= 0.7:
            date_columns.append(column)
    return date_columns


def _parse_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def build_generic_analytics(
    df: pd.DataFrame,
    *,
    numeric_column: str,
    aggregation: str,
    category_column: str | None = None,
    date_column: str | None = None,
) -> GenericAnalyticsResult:
    """Aggregate an arbitrary dataframe without assuming domain meaning."""
    if aggregation not in AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation: {aggregation}")
    if numeric_column not in df.columns:
        raise ValueError(f"Numeric column not found: {numeric_column}")
    if category_column and category_column not in df.columns:
        raise ValueError(f"Category column not found: {category_column}")
    if date_column and date_column not in df.columns:
        raise ValueError(f"Date column not found: {date_column}")

    working = df.copy()
    working["_measure"] = pd.to_numeric(working[numeric_column], errors="coerce")
    selected_columns = [numeric_column]
    group_columns: list[str] = []

    if category_column:
        working["_category"] = working[category_column].astype("string").fillna("Missing")
        group_columns.append("_category")
        selected_columns.append(category_column)

    if date_column:
        working["_date"] = _parse_dates(working[date_column])
        working = working[working["_date"].notna()].copy()
        working["_period"] = working["_date"].dt.to_period("M").dt.to_timestamp()
        group_columns.insert(0, "_period")
        selected_columns.append(date_column)

    rows_before_measure_filter = len(working)
    working = working[working["_measure"].notna()].copy()
    rows_used = len(working)

    if working.empty:
        raise ValueError("No rows remain after parsing the selected numeric/date columns.")

    agg_method = AGGREGATIONS[aggregation]
    if group_columns:
        aggregated = (
            working.groupby(group_columns, dropna=False, as_index=False)
            .agg(value=("_measure", agg_method), rows=("_measure", "count"))
        )
    else:
        aggregated = pd.DataFrame(
            {
                "metric": [f"{aggregation}_{numeric_column}"],
                "value": [getattr(working["_measure"], agg_method)()],
                "rows": [rows_used],
            }
        )

    rename_map = {"_category": category_column or "category", "_period": "period"}
    aggregated = aggregated.rename(columns=rename_map)
    if "value" in aggregated.columns:
        aggregated["value"] = aggregated["value"].round(2)

    insights = build_generic_insights(
        df,
        aggregated,
        numeric_column=numeric_column,
        aggregation=aggregation,
        selected_columns=selected_columns,
        rows_used=rows_used,
        rows_after_date_filter=rows_before_measure_filter,
        category_column=category_column,
    )
    return GenericAnalyticsResult(aggregated=aggregated, insights=insights, rows_used=rows_used)


def build_generic_insights(
    source_df: pd.DataFrame,
    aggregated: pd.DataFrame,
    *,
    numeric_column: str,
    aggregation: str,
    selected_columns: list[str],
    rows_used: int,
    rows_after_date_filter: int,
    category_column: str | None,
) -> list[str]:
    """Create transparent observations from the generic aggregation."""
    insights = [
        f"Aggregation used: {aggregation} of {numeric_column}.",
        f"Rows used: {rows_used:,}.",
    ]
    if rows_after_date_filter != len(source_df):
        insights.append(f"Rows after date parsing filter: {rows_after_date_filter:,}.")

    missing_parts = []
    for column in dict.fromkeys(selected_columns):
        missing_parts.append(f"{column}: {int(source_df[column].isna().sum()):,}")
    insights.append("Missing values in selected columns: " + "; ".join(missing_parts) + ".")

    if category_column and category_column in aggregated.columns and not aggregated.empty:
        ranked = aggregated.sort_values("value", ascending=False)
        top = ranked.iloc[0]
        bottom = ranked.iloc[-1]
        insights.append(f"Highest {category_column}: {top[category_column]} ({top['value']:,.2f}).")
        insights.append(f"Lowest {category_column}: {bottom[category_column]} ({bottom['value']:,.2f}).")

    return insights
