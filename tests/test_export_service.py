from __future__ import annotations

from io import BytesIO

import pandas as pd

from app.services.export_service import (
    build_export_filename,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    dataframe_to_json_bytes,
    transformation_log_to_dataframe,
)


def test_dataframe_export_formats_round_trip():
    df = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]), "value": [10]})

    csv_bytes = dataframe_to_csv_bytes(df)
    assert b"value" in csv_bytes

    excel_bytes = dataframe_to_excel_bytes(df, sheet_name="Working Data")
    excel_df = pd.read_excel(BytesIO(excel_bytes))
    assert excel_df["value"].iloc[0] == 10

    json_bytes = dataframe_to_json_bytes(df)
    assert b'"value":10' in json_bytes


def test_transformation_log_to_dataframe():
    log_df = transformation_log_to_dataframe(["Renamed column A to B", "Dropped duplicates"])

    assert list(log_df.columns) == ["step", "transformation"]
    assert log_df["step"].tolist() == [1, 2]


def test_build_export_filename_is_safe():
    filename = build_export_filename("Finance Data.xlsx", "Monthly Result", ".CSV")

    assert filename == "finance-data-xlsx_monthly-result.csv"
