"""Data dictionary generation for the active working dataframe."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from app.services.template_registry import implemented_domain_templates


def build_mapping_lookup(
    template_mappings: Mapping[str, Mapping[str, str | None]] | None,
) -> dict[str, list[tuple[str, str, str]]]:
    """Return source-column lookup entries from saved template mappings."""
    lookup: dict[str, list[tuple[str, str, str]]] = {}
    template_by_id = {template.template_id: template for template in implemented_domain_templates()}
    for template_id, mapping in (template_mappings or {}).items():
        template = template_by_id.get(template_id)
        if template is None:
            continue
        for field, column in mapping.items():
            if not column:
                continue
            field_type = "required" if field in template.required_fields else "optional"
            lookup.setdefault(column, []).append((template.name, field, field_type))
    return lookup


def generate_data_dictionary(
    df: pd.DataFrame,
    *,
    template_mappings: Mapping[str, Mapping[str, str | None]] | None = None,
) -> pd.DataFrame:
    """Build a BI-friendly data dictionary from a dataframe."""
    mapping_lookup = build_mapping_lookup(template_mappings)
    rows: list[dict[str, Any]] = []
    row_count = max(len(df), 1)

    for column in df.columns:
        series = df[column]
        missing_count = int(series.isna().sum())
        missing_pct = round(missing_count / row_count * 100, 2)
        numeric = pd.to_numeric(series, errors="coerce")
        parsed_dates = _parse_dates(series.dropna())
        is_numeric = pd.api.types.is_numeric_dtype(series) or (series.notna().any() and numeric.notna().mean() >= 0.9)
        is_datetime = pd.api.types.is_datetime64_any_dtype(series) or (
            not is_numeric and series.dropna().size > 0 and parsed_dates.notna().mean() >= 0.8
        )
        detected_type = _detected_type(series, is_numeric=is_numeric, is_datetime=is_datetime)

        examples = [
            str(value)
            for value in series.dropna().astype(str).drop_duplicates().head(3).tolist()
        ]
        mapped_entries = mapping_lookup.get(column, [])
        mapped_business_field = "; ".join(
            f"{template}: {field}" for template, field, _ in mapped_entries
        )
        template_relevance = "; ".join(
            f"{template} {field_type}" for template, _, field_type in mapped_entries
        )
        notes = _quality_notes(
            column,
            series,
            missing_pct=missing_pct,
            numeric=numeric,
            parsed_dates=parsed_dates,
            is_numeric=is_numeric,
            is_datetime=is_datetime,
            mapped_entries=mapped_entries,
        )

        rows.append(
            {
                "column_name": column,
                "detected_data_type": detected_type,
                "missing_value_count": missing_count,
                "missing_value_percentage": missing_pct,
                "unique_value_count": int(series.nunique(dropna=True)),
                "example_values": ", ".join(examples),
                "numeric_min": _safe_number(numeric.min()) if is_numeric else None,
                "numeric_max": _safe_number(numeric.max()) if is_numeric else None,
                "numeric_average": _safe_number(numeric.mean()) if is_numeric else None,
                "first_date": _safe_date(parsed_dates.min()) if is_datetime else None,
                "last_date": _safe_date(parsed_dates.max()) if is_datetime else None,
                "mapped_business_field": mapped_business_field,
                "template_relevance": template_relevance,
                "quality_notes": "; ".join(notes),
            }
        )

    return pd.DataFrame(rows)


def _parse_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def _detected_type(series: pd.Series, *, is_numeric: bool, is_datetime: bool) -> str:
    if is_datetime:
        return "datetime"
    if is_numeric:
        return "numeric"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if series.nunique(dropna=True) <= max(20, len(series) * 0.05):
        return "categorical"
    return "text"


def _quality_notes(
    column: str,
    series: pd.Series,
    *,
    missing_pct: float,
    numeric: pd.Series,
    parsed_dates: pd.Series,
    is_numeric: bool,
    is_datetime: bool,
    mapped_entries: list[tuple[str, str, str]],
) -> list[str]:
    notes: list[str] = []
    if missing_pct == 0:
        notes.append("No missing values")
    else:
        notes.append("Contains missing values")
    if missing_pct >= 30:
        notes.append("High missing percentage")
    if "id" in column.lower() or series.nunique(dropna=True) == len(series.dropna()):
        notes.append("Potential identifier column")
    if any(field_type == "required" for _, _, field_type in mapped_entries):
        notes.append("Mapped to required template field")
    elif mapped_entries:
        notes.append("Mapped to optional template field")
    if is_numeric and ((numeric.dropna() <= 0).any()):
        notes.append("Numeric column with zero or negative values")
    if is_datetime and parsed_dates.isna().sum() > 0:
        notes.append("Date column with parsing issues")
    return notes


def _safe_number(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), 4)


def _safe_date(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()
