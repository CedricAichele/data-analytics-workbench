"""Explainable data quality score calculation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DataQualityReport:
    overall_score: float
    sub_scores: dict[str, float]
    explanations: list[str]
    recommended_fixes: list[str]
    metrics: dict[str, float]


def _score_from_rate(problem_rate: float) -> float:
    return round(max(0.0, min(100.0, (1 - problem_rate) * 100)), 1)


def _parse_dates(series: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def _resolve_columns(mapping: dict[str, str | None] | None, fields: Iterable[str]) -> list[str]:
    if not mapping:
        return []
    return [
        column
        for field in fields
        if (column := mapping.get(field))
    ]


def calculate_quality_score(
    df: pd.DataFrame,
    *,
    mapping: dict[str, str | None] | None = None,
    required_fields: list[str] | None = None,
    date_fields: list[str] | None = None,
    numeric_fields: list[str] | None = None,
) -> DataQualityReport:
    """Calculate an explainable 0-100 quality score.

    The score is a weighted blend of visible dimensions, not a black box:
    missing values, duplicate rows, invalid numeric values, schema completeness,
    and date parsing quality.
    """
    total_cells = max(df.shape[0] * df.shape[1], 1)
    missing_cells = int(df.isna().sum().sum())
    missing_rate = missing_cells / total_cells
    missing_score = _score_from_rate(missing_rate)

    row_count = max(len(df), 1)
    duplicate_rows = int(df.duplicated().sum())
    duplicate_rate = duplicate_rows / row_count
    duplicate_score = _score_from_rate(duplicate_rate)

    numeric_columns = _resolve_columns(mapping, numeric_fields or [])
    invalid_numeric_count = 0
    numeric_values_checked = 0
    for field, column in (mapping or {}).items():
        if numeric_fields and field not in numeric_fields:
            continue
        if not column or column not in df.columns:
            continue
        numeric = pd.to_numeric(df[column], errors="coerce")
        numeric_values_checked += int(df[column].notna().sum())
        invalid_numeric_count += int(numeric.isna().sum() - df[column].isna().sum())
        if field == "unit_price":
            invalid_numeric_count += int((numeric <= 0).sum())
        elif field == "quantity":
            invalid_numeric_count += int((numeric == 0).sum())

    if not numeric_columns:
        numeric_columns = [
            column
            for column in df.select_dtypes(include=[np.number]).columns
        ]
        for column in numeric_columns:
            numeric = pd.to_numeric(df[column], errors="coerce")
            numeric_values_checked += int(numeric.notna().sum())
            invalid_numeric_count += int(np.isinf(numeric).sum())

    invalid_numeric_rate = invalid_numeric_count / max(numeric_values_checked, 1)
    invalid_numeric_score = _score_from_rate(invalid_numeric_rate)

    schema_assessed = bool(required_fields and mapping is not None)
    if schema_assessed:
        mapped_required = [
            field
            for field in required_fields
            if mapping.get(field) in df.columns
        ]
        schema_completeness = len(mapped_required) / len(required_fields)
    else:
        schema_completeness = 1.0
    schema_score = round(schema_completeness * 100, 1)

    date_columns = _resolve_columns(mapping, date_fields or [])
    date_values_checked = 0
    date_parse_failures = 0
    for column in date_columns:
        if column not in df.columns:
            continue
        non_null = df[column].dropna()
        parsed = _parse_dates(non_null)
        date_values_checked += len(non_null)
        date_parse_failures += int(parsed.isna().sum())
    date_parse_rate = date_parse_failures / max(date_values_checked, 1)
    date_score = _score_from_rate(date_parse_rate)

    sub_scores = {
        "missing_values": missing_score,
        "duplicate_rows": duplicate_score,
        "invalid_numeric_values": invalid_numeric_score,
    }
    if schema_assessed:
        sub_scores["schema_completeness"] = schema_score
    if date_columns:
        sub_scores["date_parsing"] = date_score

    weights = {
        "missing_values": 0.25,
        "duplicate_rows": 0.15,
        "invalid_numeric_values": 0.2,
        "schema_completeness": 0.25,
        "date_parsing": 0.15,
    }
    active_weight_total = sum(weights[name] for name in sub_scores)
    overall_score = round(
        sum(sub_scores[name] * weights[name] for name in sub_scores) / active_weight_total,
        1,
    )

    explanations = [
        f"Missing values: {missing_cells} missing cells across {total_cells} total cells ({missing_rate:.1%}).",
        f"Duplicate rows: {duplicate_rows} duplicate rows out of {len(df)} rows ({duplicate_rate:.1%}).",
        f"Invalid numeric values: {invalid_numeric_count} issues across {max(numeric_values_checked, 1)} checked values.",
    ]
    if schema_assessed:
        explanations.append(f"Schema completeness: {schema_score:.1f}% of required template fields are mapped.")
    else:
        explanations.append("Schema completeness: not assessed until a domain template is selected.")
    if date_columns:
        explanations.append(f"Date parsing: {date_parse_failures} failures across {max(date_values_checked, 1)} checked date values.")
    else:
        explanations.append("Date parsing: not assessed because no template date field was provided.")

    recommended_fixes: list[str] = []
    if missing_score < 95:
        recommended_fixes.append("Review high-missing columns and decide whether to impute, backfill, or exclude them.")
    if duplicate_rows:
        recommended_fixes.append("Investigate duplicate rows before KPI reporting; keep an audit trail if removing them.")
    if invalid_numeric_count:
        recommended_fixes.append("Correct or exclude invalid numeric values such as non-numeric quantities or unit prices <= 0.")
    if schema_assessed and schema_score < 100:
        recommended_fixes.append("Complete required field mapping before using domain-specific analytics.")
    if date_columns and date_parse_failures:
        recommended_fixes.append("Standardize date formats or provide explicit parsing rules.")
    if not recommended_fixes:
        recommended_fixes.append("No major data quality issues were detected by the current rules.")

    return DataQualityReport(
        overall_score=overall_score,
        sub_scores=sub_scores,
        explanations=explanations,
        recommended_fixes=recommended_fixes,
        metrics={
            "missing_cells": missing_cells,
            "duplicate_rows": duplicate_rows,
            "invalid_numeric_count": invalid_numeric_count,
            "date_parse_failures": date_parse_failures,
            "schema_completeness": schema_score if schema_assessed else np.nan,
        },
    )
