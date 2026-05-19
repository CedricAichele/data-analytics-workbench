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


@dataclass(frozen=True)
class GenericSelectionValidation:
    valid: bool
    measures: list[str]
    category_column: str | None
    date_column: str | None
    messages: list[str]


@dataclass(frozen=True)
class LongChartData:
    data: pd.DataFrame
    id_vars: list[str]
    measure_columns: list[str]
    value_column: str
    messages: list[str]


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


def validate_generic_selection(
    df: pd.DataFrame,
    selected_measures: list[str] | str | None,
    group_col: str | None = None,
    date_col: str | None = None,
) -> GenericSelectionValidation:
    """Validate user selections against the current working dataframe."""
    messages: list[str] = []
    requested_measures = _normalize_measures(selected_measures or [])
    missing_measures = [measure for measure in requested_measures if measure not in df.columns]
    if missing_measures:
        messages.append(f"Missing measure column(s): {', '.join(missing_measures)}.")
    valid_measures = [measure for measure in requested_measures if measure in df.columns]

    numeric_measures = []
    for measure in valid_measures:
        parsed = pd.to_numeric(df[measure], errors="coerce")
        if parsed.notna().any():
            numeric_measures.append(measure)
        else:
            messages.append(f"Measure has no numeric values: {measure}.")

    valid_group = group_col if group_col in df.columns else None
    if group_col and valid_group is None:
        messages.append(f"Missing grouping column: {group_col}.")

    valid_date = date_col if date_col in df.columns else None
    if date_col and valid_date is None:
        messages.append(f"Missing date column: {date_col}.")

    if not numeric_measures:
        messages.append("Select at least one numeric measure available in the current dataset.")

    return GenericSelectionValidation(
        valid=bool(numeric_measures),
        measures=numeric_measures,
        category_column=valid_group,
        date_column=valid_date,
        messages=messages,
    )


def aggregate_generic_data(
    df: pd.DataFrame,
    measures: list[str],
    group_col: str | None,
    date_col: str | None,
    aggregation: str,
) -> GenericAnalyticsResult:
    """Compatibility wrapper for generic aggregation."""
    return build_generic_analytics(
        df,
        numeric_columns=measures,
        category_column=group_col,
        date_column=date_col,
        aggregation=aggregation,
    )


def create_long_chart_data(
    chart_data: pd.DataFrame,
    id_vars: list[str] | tuple[str, ...] | str | None,
    measure_cols: list[str] | tuple[str, ...] | str | None,
) -> LongChartData:
    """Safely reshape aggregated chart data without surfacing pandas melt errors."""
    messages: list[str] = []
    if chart_data is None or chart_data.empty:
        return LongChartData(pd.DataFrame(), [], [], "metric_value", ["No chart data is available."])

    id_var_list = _as_list(id_vars)
    measure_list = _as_list(measure_cols)
    valid_id_vars = [column for column in dict.fromkeys(id_var_list) if column in chart_data.columns]
    missing_id_vars = [column for column in id_var_list if column not in chart_data.columns]
    if missing_id_vars:
        messages.append(f"Missing chart grouping column(s): {', '.join(dict.fromkeys(missing_id_vars))}.")

    id_var_set = set(valid_id_vars)
    valid_measures = [
        column
        for column in dict.fromkeys(measure_list)
        if column in chart_data.columns and column not in id_var_set
    ]
    missing_measures = [column for column in measure_list if column not in chart_data.columns]
    overlap = [column for column in measure_list if column in id_var_set]
    if missing_measures:
        messages.append(f"Missing chart measure column(s): {', '.join(dict.fromkeys(missing_measures))}.")
    if overlap:
        messages.append(f"Skipped overlapping grouping/measure column(s): {', '.join(dict.fromkeys(overlap))}.")
    if not valid_measures:
        messages.append("No valid measure columns are available for charting.")
        return LongChartData(pd.DataFrame(), valid_id_vars, [], "metric_value", messages)

    value_name = _unique_column_name(chart_data.columns, "metric_value")
    try:
        long_data = chart_data.melt(
            id_vars=valid_id_vars,
            value_vars=valid_measures,
            var_name="measure",
            value_name=value_name,
        )
    except ValueError as exc:
        messages.append(f"The selected chart configuration is not valid for the current dataset: {exc}")
        return LongChartData(pd.DataFrame(), valid_id_vars, valid_measures, value_name, messages)

    return LongChartData(long_data, valid_id_vars, valid_measures, value_name, messages)


def is_chart_config_supported(
    chart_type: str,
    measures: list[str],
    group_col: str | None = None,
    date_col: str | None = None,
) -> tuple[bool, list[str]]:
    """Return whether a generic chart configuration is supported."""
    messages: list[str] = []
    if not measures:
        return False, ["Select at least one numeric measure."]
    if chart_type == "scatter plot" and len(measures) < 2:
        messages.append("Scatter plot requires at least two numeric measures.")
    if chart_type in {"line chart", "area chart"} and not (group_col or date_col):
        messages.append("Line and area charts are most useful with a date or category grouping.")
    return not messages, messages


def _as_list(value: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _unique_column_name(existing_columns: pd.Index, preferred: str) -> str:
    if preferred not in existing_columns:
        return preferred
    suffix = 2
    while f"{preferred}_{suffix}" in existing_columns:
        suffix += 1
    return f"{preferred}_{suffix}"


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
