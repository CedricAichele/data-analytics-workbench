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
    measure_columns: list[str]


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


def _normalize_measures(numeric_columns: str | list[str]) -> list[str]:
    if isinstance(numeric_columns, str):
        return [numeric_columns]
    return list(dict.fromkeys(numeric_columns))


def build_generic_analytics(
    df: pd.DataFrame,
    *,
    numeric_column: str | None = None,
    numeric_columns: list[str] | None = None,
    aggregation: str,
    category_column: str | None = None,
    date_column: str | None = None,
) -> GenericAnalyticsResult:
    """Aggregate an arbitrary dataframe without assuming domain meaning."""
    if aggregation not in AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation: {aggregation}")
    measures = _normalize_measures(numeric_columns or numeric_column or [])
    if not measures:
        raise ValueError("Select at least one numeric measure.")
    missing_measures = [column for column in measures if column not in df.columns]
    if missing_measures:
        raise ValueError(f"Numeric columns not found: {', '.join(missing_measures)}")
    if category_column and category_column not in df.columns:
        raise ValueError(f"Category column not found: {category_column}")
    if date_column and date_column not in df.columns:
        raise ValueError(f"Date column not found: {date_column}")

    working = df.copy()
    selected_columns = list(measures)
    for measure in measures:
        working[measure] = pd.to_numeric(working[measure], errors="coerce")

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

    rows_after_date_filter = len(working)
    working = working[working[measures].notna().any(axis=1)].copy()
    rows_used = len(working)
    if working.empty:
        raise ValueError("No rows remain after parsing the selected numeric/date columns.")

    agg_method = AGGREGATIONS[aggregation]
    if group_columns:
        aggregated = working.groupby(group_columns, dropna=False, as_index=False).agg(
            **{measure: (measure, agg_method) for measure in measures},
            rows=(measures[0], "size"),
        )
    else:
        aggregated = pd.DataFrame(
            {
                "metric": [aggregation],
                **{measure: [getattr(working[measure], agg_method)()] for measure in measures},
                "rows": [rows_used],
            }
        )

    aggregated = aggregated.rename(columns={"_category": category_column or "category", "_period": "period"})
    for measure in measures:
        if measure in aggregated.columns:
            aggregated[measure] = aggregated[measure].round(2)
    if len(measures) == 1 and measures[0] in aggregated.columns:
        aggregated["value"] = aggregated[measures[0]]

    insights = build_generic_insights(
        source_df=df,
        aggregated=aggregated,
        measures=measures,
        aggregation=aggregation,
        selected_columns=selected_columns,
        rows_used=rows_used,
        rows_after_date_filter=rows_after_date_filter,
        category_column=category_column,
    )
    return GenericAnalyticsResult(
        aggregated=aggregated,
        insights=insights,
        rows_used=rows_used,
        measure_columns=measures,
    )


def build_generic_insights(
    source_df: pd.DataFrame,
    aggregated: pd.DataFrame,
    *,
    measures: list[str],
    aggregation: str,
    selected_columns: list[str],
    rows_used: int,
    rows_after_date_filter: int,
    category_column: str | None,
) -> list[str]:
    """Create transparent observations from the generic aggregation."""
    insights = [
        f"Rows used: {rows_used:,}.",
        f"Measures selected: {', '.join(measures)}.",
        f"Aggregation used: {aggregation}.",
    ]
    if rows_after_date_filter != len(source_df):
        insights.append(f"Rows after date parsing filter: {rows_after_date_filter:,}.")

    missing_parts = [
        f"{column}: {int(source_df[column].isna().sum()):,}"
        for column in dict.fromkeys(selected_columns)
    ]
    insights.append("Missing values in selected columns: " + "; ".join(missing_parts) + ".")

    if category_column and category_column in aggregated.columns and not aggregated.empty:
        for measure in measures:
            if measure not in aggregated.columns:
                continue
            ranked = aggregated.sort_values(measure, ascending=False)
            top = ranked.iloc[0]
            bottom = ranked.iloc[-1]
            insights.append(f"Highest {category_column} for {measure}: {top[category_column]} ({top[measure]:,.2f}).")
            insights.append(f"Lowest {category_column} for {measure}: {bottom[category_column]} ({bottom[measure]:,.2f}).")

    return insights
