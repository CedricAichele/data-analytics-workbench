"""Guided workflow status helpers for the analytics project."""

from __future__ import annotations

from typing import Any


def build_workflow_steps(
    project_metadata: dict[str, Any],
    active_dataset: dict[str, Any] | None,
    analytics_results: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Return guided workflow steps with business-friendly status labels."""
    results = analytics_results or (active_dataset or {}).get("analytics_results", {})
    selected_template = project_metadata.get("suggested_template", "Generic")
    template_key = {
        "Sales / Retail": "sales_retail",
        "Manufacturing": "manufacturing",
        "Logistics": "logistics",
        "Finance": "finance",
    }.get(selected_template)
    mappings = (active_dataset or {}).get("template_mappings", {})
    has_domain_mapping = bool(template_key and template_key in mappings)
    has_any_analytics = any(
        results.get(key) is not None
        for key in [
            "generic_analytics_result",
            "retail_analytics_result",
            "manufacturing_analytics_result",
            "logistics_analytics_result",
            "finance_analytics_result",
        ]
    )
    transformations = (active_dataset or {}).get("transformation_log", [])

    return [
        _step(
            "Project created",
            bool(project_metadata.get("project_name")),
            "Document the purpose, owner and intended output.",
            "Open Project Setup and save the project details.",
            "pages/project_setup.py",
        ),
        _step(
            "Dataset loaded",
            active_dataset is not None,
            "Load an uploaded file or sample dataset into the workspace.",
            "Open Data Upload and load a CSV, XLSX, JSON, or sample dataset.",
            "pages/1_data_upload.py",
        ),
        _step(
            "Data Profile reviewed",
            active_dataset is not None,
            "Inspect structure, column types, missingness and duplicates.",
            "Open Data Profile to review the active working dataset.",
            "pages/2_data_profile.py",
        ),
        _step(
            "Data Quality checked",
            results.get("generic_quality_report") is not None,
            "Calculate the explainable quality score and template-specific rules.",
            "Open Data Quality to generate the quality report.",
            "pages/5_data_quality.py",
        ),
        _step(
            "Data Preparation completed",
            bool(transformations),
            "Apply controlled transformations only if the data needs preparation.",
            "Use Data Preparation for column renames, type fixes, missing values, filters or reset.",
            "pages/3_data_preparation.py",
            optional=True,
        ),
        _step(
            "Data Dictionary generated",
            results.get("data_dictionary_result") is not None,
            "Create column-level documentation from the active working dataset.",
            "Open Data Dictionary to generate documentation.",
            "pages/data_dictionary.py",
        ),
        _step(
            "Column Mapping completed",
            selected_template == "Generic" or has_domain_mapping,
            "Map business fields when using a domain KPI template.",
            "Open Column Mapping if you selected Sales, Manufacturing, Logistics or Finance.",
            "pages/4_column_mapping.py",
            optional=selected_template == "Generic",
        ),
        _step(
            "Analytics reviewed",
            has_any_analytics,
            "Run Generic Analytics or the selected domain KPI page.",
            "Open Generic Analytics or the matching domain analytics page.",
            "pages/6_generic_analytics.py",
        ),
        _step(
            "Export Package generated",
            False,
            "Download a BI-ready workbook for business users.",
            "Open Export Center and download the BI-ready Export Package.",
            "pages/export_center.py",
            optional=True,
        ),
        _step(
            "Project Backup downloaded",
            False,
            "Save project metadata, mappings and working context for later.",
            "Open Export Center and download the Project Backup.",
            "pages/export_center.py",
            optional=True,
        ),
    ]


def get_recommended_next_action(steps: list[dict[str, str]]) -> str:
    """Return the first open required action."""
    for step in steps:
        if step["status"] == "Open":
            return step["recommended_next_action"]
    return "Review exports or download a Project Backup."


def calculate_workflow_status(
    project_metadata: dict[str, Any],
    active_dataset: dict[str, Any] | None,
    analytics_results: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Count workflow step statuses for summary metrics."""
    steps = build_workflow_steps(project_metadata, active_dataset, analytics_results)
    return {
        "done": sum(step["status"] == "Done" for step in steps),
        "open": sum(step["status"] == "Open" for step in steps),
        "optional": sum(step["status"] == "Optional" for step in steps),
    }


def _step(
    name: str,
    done: bool,
    explanation: str,
    recommended_next_action: str,
    page: str,
    *,
    optional: bool = False,
) -> dict[str, str]:
    if done:
        status = "Done"
    elif optional:
        status = "Optional"
    else:
        status = "Open"
    return {
        "step": name,
        "status": status,
        "explanation": explanation,
        "recommended_next_action": recommended_next_action,
        "page": page,
    }
