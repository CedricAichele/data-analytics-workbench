"""Column mapping helpers for domain-specific analytics templates."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import RETAIL_OPTIONAL_FIELDS, RETAIL_REQUIRED_FIELDS
from app.services.schema_detector import SchemaDetectionResult
from app.services.template_registry import get_template


@dataclass(frozen=True)
class MappingValidation:
    is_valid: bool
    missing_required_fields: list[str]
    duplicate_source_columns: list[str]
    unknown_source_columns: list[str]
    messages: list[str]


def initialize_retail_mapping(
    columns: list[str],
    detection: SchemaDetectionResult | None = None,
) -> dict[str, str | None]:
    """Create a retail mapping, pre-filled with detected matches when available."""
    mapping: dict[str, str | None] = {
        field: None
        for field in RETAIL_REQUIRED_FIELDS + RETAIL_OPTIONAL_FIELDS
    }
    if detection is None:
        return mapping

    available = set(columns)
    for field, column in detection.matched_fields.items():
        if field in mapping and column in available:
            mapping[field] = column
    return mapping


def initialize_template_mapping(
    template_id: str,
    columns: list[str],
    detection: SchemaDetectionResult | None = None,
) -> dict[str, str | None]:
    """Create a mapping for any registered template."""
    template = get_template(template_id)
    mapping: dict[str, str | None] = {
        field: None
        for field in template.required_fields + template.optional_fields
    }
    if detection is None:
        return mapping

    available = set(columns)
    for field, column in detection.matched_fields.items():
        if field in mapping and column in available:
            mapping[field] = column
    return mapping


def validate_template_mapping(
    template_id: str,
    mapping: dict[str, str | None],
    columns: list[str],
) -> MappingValidation:
    """Validate that required template fields map to unique existing columns."""
    template = get_template(template_id)
    available = set(columns)
    missing_required = [
        field
        for field in template.required_fields
        if not mapping.get(field)
    ]
    selected_columns = [
        column
        for column in mapping.values()
        if column
    ]
    duplicate_sources = sorted(
        {
            column
            for column in selected_columns
            if selected_columns.count(column) > 1
        }
    )
    unknown_sources = sorted(
        {
            column
            for column in selected_columns
            if column not in available
        }
    )

    messages: list[str] = []
    if missing_required:
        messages.append(f"Missing required mappings: {', '.join(missing_required)}.")
    if duplicate_sources:
        messages.append(f"Each source column can only be mapped once. Duplicates: {', '.join(duplicate_sources)}.")
    if unknown_sources:
        messages.append(f"Mapped columns not found in dataset: {', '.join(unknown_sources)}.")
    if not messages:
        messages.append(f"Mapping is valid for {template.name}.")

    return MappingValidation(
        is_valid=not missing_required and not duplicate_sources and not unknown_sources,
        missing_required_fields=missing_required,
        duplicate_source_columns=duplicate_sources,
        unknown_source_columns=unknown_sources,
        messages=messages,
    )


def validate_retail_mapping(
    mapping: dict[str, str | None],
    columns: list[str],
) -> MappingValidation:
    """Validate that required retail fields have unique, existing source columns."""
    return validate_template_mapping("sales_retail", mapping, columns)
