import pandas as pd

from app.services.transformations import (
    change_column_type,
    create_revenue_column,
    create_transformation_log_entry,
    drop_columns,
    drop_missing_rows,
    fill_missing_values,
    filter_rows,
    parse_datetime_column,
    remove_duplicate_rows,
    rename_column,
)


def test_rename_column_does_not_mutate_original():
    df = pd.DataFrame({"old": [1]})

    renamed = rename_column(df, "old", "new")

    assert "new" in renamed.columns
    assert "old" in df.columns


def test_drop_columns():
    df = pd.DataFrame({"a": [1], "b": [2]})

    result = drop_columns(df, ["b"])

    assert list(result.columns) == ["a"]


def test_change_column_type():
    df = pd.DataFrame({"value": ["1", "2", "bad"], "flag": ["yes", "no", "unknown"]})

    numeric = change_column_type(df, "value", "integer")
    boolean = change_column_type(df, "flag", "boolean")

    assert str(numeric["value"].dtype) == "Int64"
    assert numeric["value"].isna().sum() == 1
    assert str(boolean["flag"].dtype) == "boolean"
    assert boolean["flag"].isna().sum() == 1


def test_parse_datetime_column():
    df = pd.DataFrame({"date": ["2024-01-01", "not a date"]})

    result = parse_datetime_column(df, "date")

    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    assert result["date"].isna().sum() == 1


def test_remove_duplicate_rows():
    df = pd.DataFrame({"a": [1, 1, 2]})

    result = remove_duplicate_rows(df)

    assert len(result) == 2


def test_fill_missing_values():
    df = pd.DataFrame({"amount": [10.0, None, 30.0], "name": ["A", None, "B"]})

    median_result = fill_missing_values(df, "amount", "fill_numeric_median")
    text_result = fill_missing_values(df, "name", "fill_text_unknown")

    assert median_result["amount"].tolist() == [10.0, 20.0, 30.0]
    assert text_result["name"].tolist() == ["A", "Unknown", "B"]


def test_drop_missing_rows():
    df = pd.DataFrame({"a": [1, None, 2]})

    result = drop_missing_rows(df, "a")

    assert len(result) == 2
    assert result["a"].isna().sum() == 0


def test_filter_rows():
    df = pd.DataFrame({"amount": [10, 20, 30], "country": ["France", "Germany", "Finland"]})

    numeric = filter_rows(df, "amount", "greater_or_equal", "20")
    text = filter_rows(df, "country", "contains", "fin")

    assert numeric["amount"].tolist() == [20, 30]
    assert text["country"].tolist() == ["Finland"]


def test_create_revenue_column():
    df = pd.DataFrame({"quantity": [2, "bad"], "unit_price": [5.0, 10.0]})

    result = create_revenue_column(df, "quantity", "unit_price")

    assert result["revenue"].iloc[0] == 10.0
    assert pd.isna(result["revenue"].iloc[1])


def test_create_transformation_log_entry():
    entry = create_transformation_log_entry("Rename column", "old -> new")

    assert entry == "Rename column: old -> new"

