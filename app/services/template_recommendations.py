"""Template recommendation helpers for Analytics Hub."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence

from app.services.schema_detector import detect_template_schema
from app.services.template_registry import AnalyticsTemplate, list_templates


@dataclass(frozen=True)
class TemplateRecommendation:
    template_id: str
    template_name: str
    status: str
    confidence_score: float
    required_detected: dict[str, str]
    required_missing: list[str]
    optional_detected: dict[str, str]
    mapping_required: bool
    recommended_next_action: str
    reason: str


def build_template_recommendations(
    columns: Sequence[str] | None,
    *,
    mappings: Mapping[str, Mapping[str, str | None]] | None = None,
) -> list[TemplateRecommendation]:
    """Build template compatibility rows for the current dataset columns."""
    if columns is None:
        return []

    mapping_lookup = mappings or {}
    recommendations: list[TemplateRecommendation] = []
    for template in list_templates(include_generic=True):
        if template.template_id == "generic":
            recommendations.append(_generic_recommendation())
            continue
        recommendations.append(_domain_recommendation(template, list(columns), mapping_lookup.get(template.template_id, {})))

    best_domain = recommend_best_template(recommendations)
    if best_domain is None:
        return recommendations

    return [
        recommendation
        if recommendation.template_id != best_domain.template_id
        else TemplateRecommendation(
            **{
                **recommendation.__dict__,
                "status": "Recommended",
                "recommended_next_action": f"Open {recommendation.template_name}",
                "reason": f"Matched {len(recommendation.required_detected)}/{len(recommendation.required_detected) + len(recommendation.required_missing)} required fields.",
            }
        )
        for recommendation in recommendations
    ]


def recommend_best_template(recommendations: Sequence[TemplateRecommendation]) -> TemplateRecommendation | None:
    """Return the best domain recommendation when a template clearly fits."""
    domain_recommendations = [item for item in recommendations if item.template_id != "generic"]
    clear_matches = [
        item
        for item in domain_recommendations
        if not item.required_missing and item.confidence_score >= 80
    ]
    if not clear_matches:
        return None
    return max(clear_matches, key=lambda item: item.confidence_score)


def no_dataset_guidance() -> str:
    """Return safe Analytics Hub guidance before a dataset is loaded."""
    return "Load a dataset to receive template recommendations."


def _generic_recommendation() -> TemplateRecommendation:
    return TemplateRecommendation(
        template_id="generic",
        template_name="Generic Analytics",
        status="Available",
        confidence_score=100.0,
        required_detected={},
        required_missing=[],
        optional_detected={},
        mapping_required=False,
        recommended_next_action="Open Generic Analytics",
        reason="Generic Analytics works with any supported tabular dataset.",
    )


def _domain_recommendation(
    template: AnalyticsTemplate,
    columns: list[str],
    mapping: Mapping[str, str | None],
) -> TemplateRecommendation:
    detection = detect_template_schema(template.template_id, columns)
    mapped_required = {
        field: column
        for field, column in mapping.items()
        if field in template.required_fields and column in columns
    }
    mapped_optional = {
        field: column
        for field, column in mapping.items()
        if field in template.optional_fields and column in columns
    }
    required_detected = _deduplicated_detected_fields(template.required_fields, detection.field_matches)
    required_detected.update(mapped_required)
    used_columns = set(required_detected.values())
    optional_detected = _deduplicated_detected_fields(template.optional_fields, detection.field_matches, used_columns=used_columns)
    optional_detected.update(mapped_optional)
    required_missing = [field for field in template.required_fields if field not in required_detected]
    confidence = round(len(required_detected) / len(template.required_fields) * 100, 1) if template.required_fields else 100.0

    if not required_missing:
        status = "Available"
        action = f"Open {template.name}"
    elif required_detected:
        status = "Partial match"
        action = "Go to Column Mapping"
    else:
        status = "Not compatible"
        action = "Use Generic Analytics first"

    return TemplateRecommendation(
        template_id=template.template_id,
        template_name=template.name,
        status=status,
        confidence_score=confidence,
        required_detected=required_detected,
        required_missing=required_missing,
        optional_detected=optional_detected,
        mapping_required=bool(required_missing),
        recommended_next_action=action,
        reason=f"Matched {len(required_detected)}/{len(template.required_fields)} required fields.",
    )


def _deduplicated_detected_fields(
    fields: list[str],
    field_matches: Mapping[str, object],
    *,
    used_columns: set[str] | None = None,
) -> dict[str, str]:
    """Keep one best field match per dataset column for clearer diagnostics."""
    detected: dict[str, str] = {}
    used = set(used_columns or set())
    ranked = sorted(
        (
            match
            for field, match in field_matches.items()
            if field in fields and getattr(match, "column", None) is not None
        ),
        key=lambda match: getattr(match, "score", 0.0),
        reverse=True,
    )
    for match in ranked:
        column = getattr(match, "column", None)
        field = getattr(match, "field", "")
        if not column or column in used:
            continue
        detected[field] = column
        used.add(column)
    return detected
