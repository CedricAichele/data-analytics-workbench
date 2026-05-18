"""Export helpers for datasets, logs, and analytics result tables."""

from __future__ import annotations

from io import BytesIO
import re

import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Return a dataframe as UTF-8 CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    """Return a dataframe as XLSX bytes using openpyxl."""
    output = BytesIO()
    safe_sheet_name = _safe_sheet_name(sheet_name)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=safe_sheet_name)
    return output.getvalue()


def dataframe_to_json_bytes(df: pd.DataFrame) -> bytes:
    """Return a dataframe as records-oriented JSON bytes."""
    return df.to_json(orient="records", date_format="iso", indent=2).encode("utf-8")


def transformation_log_to_dataframe(log: list[str] | tuple[str, ...] | None) -> pd.DataFrame:
    """Convert a transformation log to a tabular export format."""
    entries = list(log or [])
    return pd.DataFrame(
        [{"step": index + 1, "transformation": entry} for index, entry in enumerate(entries)],
        columns=["step", "transformation"],
    )


def build_export_filename(dataset_name: str, suffix: str, extension: str) -> str:
    """Build a safe export filename without relying on local paths."""
    dataset_slug = _slugify(dataset_name or "dataset")
    suffix_slug = _slugify(suffix or "export")
    extension = extension.lstrip(".").lower()
    return f"{dataset_slug}_{suffix_slug}.{extension}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "export"


def _safe_sheet_name(value: str) -> str:
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", " ", value).strip()
    return (cleaned or "Data")[:31]
