import pandas as pd

from app.services.generic_analytics import build_generic_analytics, get_date_columns, get_numeric_columns


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
