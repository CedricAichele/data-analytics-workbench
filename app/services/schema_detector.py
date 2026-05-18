"""Rule-based schema detection for analytics templates."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from app.config import RETAIL_REQUIRED_FIELDS, RETAIL_TEMPLATE_NAME


RETAIL_FIELD_SYNONYMS: dict[str, list[str]] = {
    "order_id": ["order_id", "invoice_no", "invoice", "order", "transaction_id"],
    "order_date": ["order_date", "invoice_date", "date", "timestamp"],
    "customer_id": ["customer_id", "customer", "client_id", "user_id"],
    "product_name": ["product_name", "description", "item", "product"],
    "quantity": ["quantity", "qty", "units", "amount"],
    "unit_price": ["unit_price", "price", "sales_price", "item_price"],
    "country": ["country", "region", "market"],
    "product_category": ["product_category", "category", "department", "segment"],
    "invoice_status": ["invoice_status", "status", "order_status"],
}


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
) -> FieldMatch:
    """Find the best fuzzy synonym match for a target field."""
    synonyms = RETAIL_FIELD_SYNONYMS.get(field, [field])
    normalized_columns = {column: normalize_name(column) for column in columns}
    best_column: str | None = None
    best_synonym: str | None = None
    best_score = 0.0

    for synonym in synonyms:
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


def detect_retail_schema(columns: list[str]) -> SchemaDetectionResult:
    """Suggest the retail template when enough required fields can be matched."""
    field_matches = {
        field: match_field_to_column(field, columns)
        for field in RETAIL_FIELD_SYNONYMS
    }

    matched_fields = {
        field: match.column
        for field, match in field_matches.items()
        if match.column is not None
    }
    missing_required = [
        field
        for field in RETAIL_REQUIRED_FIELDS
        if field not in matched_fields
    ]

    required_match_count = len(RETAIL_REQUIRED_FIELDS) - len(missing_required)
    confidence_score = round(required_match_count / len(RETAIL_REQUIRED_FIELDS) * 100, 1)
    detected_template = RETAIL_TEMPLATE_NAME if confidence_score >= 67 else None

    return SchemaDetectionResult(
        detected_template=detected_template,
        confidence_score=confidence_score,
        matched_fields=matched_fields,
        missing_fields=missing_required,
        requires_manual_mapping=bool(missing_required),
        field_matches=field_matches,
    )

