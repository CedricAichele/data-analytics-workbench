"""Dataset loading helpers for uploads and bundled sample data."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd
from pandas.errors import EmptyDataError

from app.config import SAMPLE_MANUFACTURING_PATH, SAMPLE_RETAIL_PATH


@dataclass(frozen=True)
class LoadedDataset:
    dataframe: pd.DataFrame
    metadata: dict[str, Any]


def get_supported_file_types() -> list[str]:
    """Return upload extensions supported by the app."""
    return ["csv", "xlsx", "json"]


def _normalize_empty_strings(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    object_cols = cleaned.select_dtypes(include=["object", "string"]).columns
    for column in object_cols:
        cleaned[column] = cleaned[column].replace(r"^\s*$", pd.NA, regex=True)
    return cleaned


def _read_bytes(file: str | Path | BinaryIO) -> bytes:
    if isinstance(file, str | Path):
        return Path(file).read_bytes()
    if hasattr(file, "getvalue"):
        return file.getvalue()
    position = file.tell() if hasattr(file, "tell") else None
    data = file.read()
    if position is not None and hasattr(file, "seek"):
        file.seek(position)
    return data


def _file_name(file: str | Path | BinaryIO) -> str:
    if isinstance(file, str | Path):
        return Path(file).name
    return getattr(file, "name", "uploaded_file")


def _file_extension(file: str | Path | BinaryIO) -> str:
    return Path(_file_name(file)).suffix.lower().lstrip(".")


def _metadata(file: str | Path | BinaryIO, file_type: str, df: pd.DataFrame, **extra: Any) -> dict[str, Any]:
    metadata = {
        "file_name": _file_name(file),
        "file_type": file_type,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "source": "upload",
    }
    metadata.update(extra)
    return metadata


def validate_loaded_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate that loaded content is tabular and non-empty."""
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Loaded content did not produce a pandas DataFrame.")
    if df.empty or len(df.columns) == 0:
        raise ValueError("The uploaded file did not contain any tabular data.")
    return _normalize_empty_strings(df)


def load_csv(uploaded_file: str | Path | BinaryIO, *, max_rows: int | None = None) -> pd.DataFrame:
    """Load CSV content with UTF-8 first and latin1 fallback."""
    data = _read_bytes(uploaded_file)
    if not data:
        raise ValueError("The uploaded CSV file is empty.")

    try:
        df = pd.read_csv(BytesIO(data), nrows=max_rows, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(BytesIO(data), nrows=max_rows, encoding="latin1")
    except EmptyDataError as exc:
        raise ValueError("The uploaded CSV file did not contain any tabular data.") from exc

    return validate_loaded_dataframe(df)


def get_excel_sheet_names(uploaded_file: str | Path | BinaryIO) -> list[str]:
    """Return sheet names from an XLSX workbook."""
    data = _read_bytes(uploaded_file)
    try:
        workbook = pd.ExcelFile(BytesIO(data), engine="openpyxl")
    except Exception as exc:
        raise ValueError("The uploaded Excel file could not be opened as a valid .xlsx workbook.") from exc
    return list(workbook.sheet_names)


def load_excel(uploaded_file: str | Path | BinaryIO, sheet_name: str | int | None = None) -> pd.DataFrame:
    """Load an XLSX workbook sheet into a dataframe."""
    data = _read_bytes(uploaded_file)
    selected_sheet = 0 if sheet_name is None else sheet_name
    try:
        df = pd.read_excel(BytesIO(data), sheet_name=selected_sheet, engine="openpyxl")
    except ValueError as exc:
        raise ValueError(f"Excel sheet could not be loaded: {exc}") from exc
    except Exception as exc:
        raise ValueError("The uploaded Excel file could not be opened as a valid .xlsx workbook.") from exc
    return validate_loaded_dataframe(df)


def _contains_nested_objects(df: pd.DataFrame) -> bool:
    if df.empty:
        return False
    sample = df.head(25)
    for column in sample.columns:
        if sample[column].map(lambda value: isinstance(value, dict | list)).any():
            return True
    return False


def _first_record_list(data: dict[str, Any]) -> list[Any] | None:
    preferred_keys = ["records", "data", "items", "rows", "results"]
    for key in preferred_keys:
        value = data.get(key)
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            return value
    for value in data.values():
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            return value
    return None


def normalize_json_to_dataframe(data: Any) -> pd.DataFrame:
    """Normalize common tabular JSON shapes into a dataframe."""
    if isinstance(data, list):
        if not data:
            raise ValueError("The uploaded JSON array is empty.")
        if not all(isinstance(item, dict) for item in data):
            raise ValueError("JSON arrays must contain records/objects to be treated as tabular data.")
        df = pd.json_normalize(data)
    elif isinstance(data, dict):
        record_list = _first_record_list(data)
        if record_list is not None:
            df = pd.json_normalize(record_list)
        elif any(isinstance(value, dict) for value in data.values()):
            df = pd.json_normalize(data)
        else:
            df = pd.DataFrame([data])
    else:
        raise ValueError("JSON files must contain tabular records or normalizable nested records.")

    if _contains_nested_objects(df):
        raise ValueError("JSON appears too deeply nested. Please provide tabular records or preprocess the JSON first.")
    return validate_loaded_dataframe(df)


def load_json(uploaded_file: str | Path | BinaryIO) -> pd.DataFrame:
    """Load tabular JSON, including JSON arrays, records, simple nested objects, and JSON Lines."""
    data = _read_bytes(uploaded_file)
    if not data:
        raise ValueError("The uploaded JSON file is empty.")

    try:
        parsed = json.loads(data.decode("utf-8-sig"))
        return normalize_json_to_dataframe(parsed)
    except UnicodeDecodeError as exc:
        raise ValueError("The uploaded JSON file must be UTF-8 encoded.") from exc
    except json.JSONDecodeError:
        try:
            text = data.decode("utf-8-sig")
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
            return normalize_json_to_dataframe(records)
        except Exception as exc:
            raise ValueError("Invalid JSON. JSON files must contain tabular records or JSON Lines.") from exc


def load_uploaded_file(uploaded_file: BinaryIO, *, sheet_name: str | int | None = None) -> LoadedDataset:
    """Load an uploaded CSV, XLSX, or JSON file and return data plus metadata."""
    extension = _file_extension(uploaded_file)

    if extension == "csv":
        df = load_csv(uploaded_file)
        return LoadedDataset(df, _metadata(uploaded_file, "csv", df))
    if extension == "xlsx":
        df = load_excel(uploaded_file, sheet_name=sheet_name)
        return LoadedDataset(df, _metadata(uploaded_file, "xlsx", df, sheet_name=sheet_name or get_excel_sheet_names(uploaded_file)[0]))
    if extension == "json":
        df = load_json(uploaded_file)
        return LoadedDataset(df, _metadata(uploaded_file, "json", df))
    if extension == "xls":
        raise ValueError("Excel .xls files are not supported. Please save the workbook as .xlsx and upload again.")

    supported = ", ".join(get_supported_file_types())
    raise ValueError(f"Unsupported file format '.{extension}'. Supported formats: {supported}.")


def load_sample_retail_orders() -> LoadedDataset:
    """Load the bundled synthetic retail dataset."""
    if not SAMPLE_RETAIL_PATH.exists():
        raise FileNotFoundError(
            "Sample dataset was not found. Restore data/sample/sample_retail_orders.csv "
            "or upload your own CSV, XLSX, or JSON file."
        )
    df = load_csv(SAMPLE_RETAIL_PATH)
    metadata = {
        "file_name": SAMPLE_RETAIL_PATH.name,
        "file_type": "csv",
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "source": "sample",
        "suggested_template": "sales_retail",
    }
    return LoadedDataset(df, metadata)


def load_sample_manufacturing_operations() -> LoadedDataset:
    """Load the bundled synthetic manufacturing operations dataset."""
    if not SAMPLE_MANUFACTURING_PATH.exists():
        raise FileNotFoundError(
            "Sample manufacturing dataset was not found. Restore "
            "data/sample/sample_manufacturing_operations.csv or upload your own CSV, XLSX, or JSON file."
        )
    df = load_csv(SAMPLE_MANUFACTURING_PATH)
    metadata = {
        "file_name": SAMPLE_MANUFACTURING_PATH.name,
        "file_type": "csv",
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "source": "sample",
        "suggested_template": "manufacturing",
    }
    return LoadedDataset(df, metadata)
