import pandas as pd

from app.services.profiler import profile_dataframe


def test_profile_dataframe_returns_generic_profile():
    df = pd.DataFrame(
        {
            "order_date": ["2024-01-01", "2024-01-02", None],
            "revenue": [10.0, 20.0, 30.0],
            "category": ["A", "B", "A"],
        }
    )

    profile = profile_dataframe(df)

    assert profile.row_count == 3
    assert profile.column_count == 3
    assert "revenue" in profile.detected_numeric_columns
    assert "order_date" in profile.detected_date_columns
    assert "category" in profile.detected_categorical_columns
    assert profile.missing_table.loc[profile.missing_table["column"] == "order_date", "missing_count"].iloc[0] == 1

