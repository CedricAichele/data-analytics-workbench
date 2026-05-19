import pandas as pd

from app.services.generic_analytics import (
    build_generic_analytics,
    create_long_chart_data,
    get_date_columns,
    get_numeric_columns,
    is_chart_config_supported,
    validate_generic_selection,
)


def test_generic_analytics_groups_and_summarizes():
    df = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-15", "2025-02-01"],
            "category": ["A", "A", "B"],
            "value": [10, 20, 5],
        }
    )

    result = build_generic_analytics(
        df,
        numeric_column="value",
        aggregation="sum",
        category_column="category",
        date_column="date",
    )

    assert result.rows_used == 3
    assert set(result.aggregated["category"]) == {"A", "B"}
    assert result.aggregated["value"].sum() == 35
    assert any("Highest category" in insight for insight in result.insights)


def test_generic_analytics_supports_multiple_measures():
    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "value": [10, 20, 5],
            "cost": [2, 3, 7],
        }
    )

    result = build_generic_analytics(
        df,
        numeric_columns=["value", "cost"],
        aggregation="sum",
        category_column="category",
    )

    row_a = result.aggregated[result.aggregated["category"] == "A"].iloc[0]
    assert row_a["value"] == 30
    assert row_a["cost"] == 5
    assert result.measure_columns == ["value", "cost"]
    assert any("Measures selected: value, cost" in insight for insight in result.insights)


def test_generic_column_detection():
    df = pd.DataFrame({"date": ["2025-01-01"], "value": ["10"], "label": ["x"]})

    assert "value" in get_numeric_columns(df)
    assert "date" in get_date_columns(df)


def test_create_long_chart_data_supports_multiple_measures():
    chart_data = pd.DataFrame({"category": ["A", "B"], "sales": [10, 20], "cost": [4, 8]})

    long_result = create_long_chart_data(chart_data, ["category"], ["sales", "cost"])

    assert long_result.value_column == "metric_value"
    assert set(long_result.data["measure"]) == {"sales", "cost"}
    assert long_result.data["metric_value"].sum() == 42


def test_create_long_chart_data_handles_missing_and_overlapping_columns_without_raising():
    chart_data = pd.DataFrame({"metric": ["sum"], "rows": [2], "value": [30], "cost": [12]})

    long_result = create_long_chart_data(
        chart_data,
        ["metric", "missing_id", "value"],
        ["value", "cost", "missing_measure", "metric"],
    )

    assert long_result.measure_columns == ["cost"]
    assert "metric_value" in long_result.data.columns
    assert any("Missing chart grouping" in message for message in long_result.messages)
    assert any("Missing chart measure" in message for message in long_result.messages)
    assert any("Skipped overlapping" in message for message in long_result.messages)


def test_create_long_chart_data_handles_existing_value_column_name_without_raising():
    chart_data = pd.DataFrame({"category": ["A"], "value": [10], "metric_value": [99]})

    long_result = create_long_chart_data(chart_data, ["category"], ["value"])

    assert long_result.value_column == "metric_value_2"
    assert long_result.data.loc[0, "metric_value_2"] == 10


def test_validate_generic_selection_handles_stale_columns_after_preparation_changes():
    df = pd.DataFrame({"sales": [1, 2], "current_group": ["A", "B"]})

    validation = validate_generic_selection(df, ["old_sales", "sales"], "old_group", "old_date")

    assert validation.valid is True
    assert validation.measures == ["sales"]
    assert validation.category_column is None
    assert validation.date_column is None
    assert any("Missing measure" in message for message in validation.messages)
    assert any("Missing grouping" in message for message in validation.messages)


def test_incompatible_generic_chart_config_returns_message_not_exception():
    supported, messages = is_chart_config_supported("scatter plot", ["sales"])

    assert supported is False
    assert messages == ["Scatter plot requires at least two numeric measures."]
