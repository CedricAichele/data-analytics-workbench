from io import BytesIO
import json

import pandas as pd
import pytest

from app.services.data_loader import (
    get_supported_file_types,
    load_csv,
    load_excel,
    load_json,
    load_sample_manufacturing_operations,
    load_uploaded_file,
    normalize_json_to_dataframe,
    validate_loaded_dataframe,
)


def _named_bytes(data: bytes, name: str) -> BytesIO:
    file = BytesIO(data)
    file.name = name
    return file


def test_supported_file_types():
    assert get_supported_file_types() == ["csv", "xlsx", "json"]


def test_load_csv_from_bytesio():
    file = _named_bytes(b"name,value\nA,1\nB,2\n", "sample.csv")

    df = load_csv(file)

    assert df.to_dict("records") == [{"name": "A", "value": 1}, {"name": "B", "value": 2}]


def test_load_excel_from_bytesio():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame({"name": ["A", "B"], "value": [1, 2]}).to_excel(writer, sheet_name="Data", index=False)
    file = _named_bytes(output.getvalue(), "sample.xlsx")

    df = load_excel(file, sheet_name="Data")

    assert df["name"].tolist() == ["A", "B"]
    assert df["value"].tolist() == [1, 2]


def test_load_excel_selected_sheet_from_bytesio():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame({"ignore": [1]}).to_excel(writer, sheet_name="Summary", index=False)
        pd.DataFrame({"order_id": [10, 11]}).to_excel(writer, sheet_name="Orders", index=False)
    file = _named_bytes(output.getvalue(), "sample.xlsx")

    df = load_excel(file, sheet_name="Orders")

    assert df["order_id"].tolist() == [10, 11]


def test_load_json_array_of_records():
    file = _named_bytes(json.dumps([{"a": 1, "b": 2}, {"a": 3, "b": 4}]).encode("utf-8"), "sample.json")

    df = load_json(file)

    assert df.to_dict("records") == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]


def test_load_json_lines():
    file = _named_bytes(b'{"a": 1, "b": "x"}\n{"a": 2, "b": "y"}\n', "sample.json")

    df = load_json(file)

    assert df.to_dict("records") == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]


def test_normalize_nested_json_records():
    data = {"records": [{"id": 1, "customer": {"country": "DE"}}, {"id": 2, "customer": {"country": "US"}}]}

    df = normalize_json_to_dataframe(data)

    assert df.columns.tolist() == ["id", "customer.country"]
    assert df["customer.country"].tolist() == ["DE", "US"]


def test_invalid_json_error_message():
    file = _named_bytes(b"{not valid json", "sample.json")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_json(file)


def test_load_uploaded_file_returns_metadata():
    file = _named_bytes(b"name,value\nA,1\n", "sample.csv")

    loaded = load_uploaded_file(file)

    assert loaded.metadata["file_name"] == "sample.csv"
    assert loaded.metadata["file_type"] == "csv"
    assert loaded.metadata["rows"] == 1
    assert loaded.metadata["columns"] == 2


def test_unsupported_extension_error():
    file = _named_bytes(b"not supported", "sample.txt")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_uploaded_file(file)


def test_empty_dataframe_validation_error():
    with pytest.raises(ValueError, match="tabular data"):
        validate_loaded_dataframe(pd.DataFrame())


def test_load_sample_manufacturing_operations():
    loaded = load_sample_manufacturing_operations()

    assert loaded.metadata["suggested_template"] == "manufacturing"
    assert loaded.metadata["rows"] >= 500
    assert {"timestamp", "machine_id", "actual_output", "scrap_count", "downtime_minutes"} <= set(loaded.dataframe.columns)
