"""Rule-based schema detection for analytics templates."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from app.config import RETAIL_REQUIRED_FIELDS, RETAIL_TEMPLATE_NAME
from app.services.template_registry import SALES_RETAIL_SYNONYMS, get_template


RETAIL_FIELD_SYNONYMS: dict[str, list[str]] = SALES_RETAIL_SYNONYMS


@dataclass(frozen=True)
class FieldMatch:
    field: str
    column: str | None
    score: float
    matched_synonym: str | None


@dataclass(frozen=True)
class SchemaDetectionResult:
    detected_template: str | None
    confidence_score: float
    matched_fields: dict[str, str]
    missing_fields: list[str]
    requires_manual_mapping: bool
    field_matches: dict[str, FieldMatch]


def normalize_name(value: str) -> str:
    """Normalize a column or synonym for matching."""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.92
    return SequenceMatcher(None, left, right).ratio()


def match_field_to_column(
    field: str,
    columns: list[str],
    *,
    threshold: float = 0.76,
    synonyms: dict[str, list[str]] | None = None,
) -> FieldMatch:
    """Find the best fuzzy synonym match for a target field."""
    synonym_lookup = synonyms or RETAIL_FIELD_SYNONYMS
    field_synonyms = synonym_lookup.get(field, [field])
    normalized_columns = {column: normalize_name(column) for column in columns}
    best_column: str | None = None
    best_synonym: str | None = None
    best_score = 0.0

    for synonym in field_synonyms:
        normalized_synonym = normalize_name(synonym)
        for column, normalized_column in normalized_columns.items():
            score = _similarity(normalized_synonym, normalized_column)
            if score > best_score:
                best_column = column
                best_synonym = synonym
                best_score = score

    if best_score < threshold:
        return FieldMatch(field=field, column=None, score=round(best_score, 3), matched_synonym=None)
    return FieldMatch(field=field, column=best_column, score=round(best_score, 3), matched_synonym=best_synonym)


def detect_template_schema(template_id: str, columns: list[str]) -> SchemaDetectionResult:
    """Suggest a registered template when enough required fields can be matched."""
    template = get_template(template_id)
    fields = template.required_fields + template.optional_fields
    field_matches = {
        field: match_field_to_column(field, columns, synonyms=template.synonyms)
        for field in fields
    }
    matched_fields = {
        field: match.column
        for field, match in field_matches.items()
        if match.column is not None
    }
    missing_required = [
        field
        for field in template.required_fields
        if field not in matched_fields
    ]

    if template.required_fields:
        required_match_count = len(template.required_fields) - len(missing_required)
        confidence_score = round(required_match_count / len(template.required_fields) * 100, 1)
    else:
        confidence_score = 100.0

    detected_template = template.name if confidence_score >= 67 else None
    return SchemaDetectionResult(
        detected_template=detected_template,
        confidence_score=confidence_score,
        matched_fields=matched_fields,
        missing_fields=missing_required,
        requires_manual_mapping=bool(missing_required),
        field_matches=field_matches,
    )


def detect_retail_schema(columns: list[str]) -> SchemaDetectionResult:
    """Suggest the retail template when enough required fields can be matched."""
    result = detect_template_schema("sales_retail", columns)
    missing_required = [field for field in RETAIL_REQUIRED_FIELDS if field in result.missing_fields]
    return SchemaDetectionResult(
        detected_template=RETAIL_TEMPLATE_NAME if result.detected_template else None,
        confidence_score=result.confidence_score,
        matched_fields=result.matched_fields,
        missing_fields=missing_required,
        requires_manual_mapping=bool(missing_required),
        field_matches=result.field_matches,
    )
