"""Business-friendly in-session project metadata helpers."""

from __future__ import annotations

from collections.abc import MutableMapping
from datetime import datetime, timezone
from typing import Any

import streamlit as st


PROJECT_METADATA_KEY = "project_metadata"
WORKFLOW_OPTIONS = ["Quick Data Check", "BI-ready Data Preparation", "Domain KPI Analysis"]
TEMPLATE_OPTIONS = ["Generic", "Sales / Retail", "Manufacturing", "Logistics", "Finance"]
OUTPUT_OPTIONS = [
    "Cleaned Dataset",
    "Data Quality Report",
    "Data Dictionary",
    "KPI Analysis",
    "BI-ready Export Package",
    "Project Backup",
]


def _state(state: MutableMapping[str, Any] | None = None) -> MutableMapping[str, Any]:
    return st.session_state if state is None else state


def default_project_metadata() -> dict[str, Any]:
    """Return a fresh metadata dictionary for a new project."""
    return {
        "project_name": "",
        "project_description": "",
        "analysis_goal": "",
        "company_department": "",
        "data_owner": "",
        "reporting_period": "",
        "notes": "",
        "selected_workflow": "Quick Data Check",
        "suggested_template": "Generic",
        "desired_outputs": ["Data Quality Report", "Data Dictionary"],
        "created_at": "",
        "updated_at": "",
    }


def initialize_project_state(state: MutableMapping[str, Any] | None = None) -> None:
    """Initialize project metadata keys without requiring a dataset."""
    current = _state(state)
    current.setdefault(PROJECT_METADATA_KEY, default_project_metadata())


def update_project_metadata(
    metadata: dict[str, Any] | None = None,
    state: MutableMapping[str, Any] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Update project metadata with provided fields and return the saved state."""
    current = _state(state)
    initialize_project_state(current)
    existing = dict(current[PROJECT_METADATA_KEY])
    updates = dict(metadata or {})
    updates.update(fields)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not existing.get("created_at") and (updates.get("project_name") or existing.get("project_name")):
        existing["created_at"] = now
    existing.update({key: value for key, value in updates.items() if key in existing})
    existing["updated_at"] = now
    current[PROJECT_METADATA_KEY] = existing
    return dict(existing)


def get_project_metadata(state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the current project metadata."""
    current = _state(state)
    initialize_project_state(current)
    return dict(current[PROJECT_METADATA_KEY])


def set_project_metadata(metadata: dict[str, Any], state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    """Replace project metadata, merging with defaults for missing keys."""
    current = _state(state)
    merged = default_project_metadata()
    merged.update({key: value for key, value in dict(metadata or {}).items() if key in merged})
    current[PROJECT_METADATA_KEY] = merged
    return dict(merged)


def has_project(state: MutableMapping[str, Any] | None = None) -> bool:
    """Return whether the user has named a project."""
    metadata = get_project_metadata(state)
    return bool(str(metadata.get("project_name", "")).strip())


def get_project_summary(
    *,
    active_dataset: dict[str, Any] | None = None,
    quality_report: Any | None = None,
    analytics_results: dict[str, Any] | None = None,
    state: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact project summary for Overview, Project Setup, and Export Center."""
    metadata = get_project_metadata(state)
    results = analytics_results or (active_dataset or {}).get("analytics_results", {})
    mappings = (active_dataset or {}).get("template_mappings", {})
    working_df = (active_dataset or {}).get("working_df")
    transformation_log = (active_dataset or {}).get("transformation_log", [])
    selected_template = metadata.get("suggested_template") or "Generic"
    template_key = _template_label_to_id(selected_template)
    mapping_status = "Not required" if selected_template == "Generic" else ("Saved" if template_key in mappings else "Open")
    analytics_available = [
        label
        for key, label in [
            ("generic_analytics_result", "Generic Analytics"),
            ("retail_analytics_result", "Sales / Retail"),
            ("manufacturing_analytics_result", "Manufacturing"),
            ("logistics_analytics_result", "Logistics"),
            ("finance_analytics_result", "Finance"),
        ]
        if results.get(key) is not None
    ]
    summary = {
        "Project name": metadata.get("project_name") or "No project created",
        "Analysis goal": metadata.get("analysis_goal") or "Not documented yet",
        "Selected workflow": metadata.get("selected_workflow") or "Quick Data Check",
        "Selected template": selected_template,
        "Active dataset": (active_dataset or {}).get("name", "No dataset loaded"),
        "Active dataset rows": len(working_df) if working_df is not None else 0,
        "Active dataset columns": len(working_df.columns) if working_df is not None else 0,
        "Data quality score": getattr(quality_report, "overall_score", "Not calculated"),
        "Transformations": len(transformation_log),
        "Data Dictionary": "Available" if results.get("data_dictionary_result") is not None else "Not generated",
        "Mapping status": mapping_status,
        "Analytics results": ", ".join(analytics_available) if analytics_available else "None yet",
        "Available exports": "Working dataset, documentation, KPI summaries, chart/result data, BI-ready package, project backup",
    }
    summary["Recommended next action"] = _recommended_next_action(summary, active_dataset, results, metadata)
    return summary


def project_summary_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Return summary rows suitable for st.dataframe."""
    return [{"item": key, "status": value} for key, value in summary.items()]


def compact_project_summary_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the compact project summary rows used by user-facing pages."""
    keys = [
        "Project name",
        "Selected workflow",
        "Selected template",
        "Active dataset",
        "Active dataset rows",
        "Active dataset columns",
        "Data quality score",
        "Transformations",
        "Data Dictionary",
        "Available exports",
        "Recommended next action",
    ]
    return [{"item": key, "status": summary.get(key, "")} for key in keys]


def _template_label_to_id(label: str) -> str:
    return {
        "Sales / Retail": "sales_retail",
        "Manufacturing": "manufacturing",
        "Logistics": "logistics",
        "Finance": "finance",
    }.get(label, "generic")


def _recommended_next_action(
    summary: dict[str, Any],
    active_dataset: dict[str, Any] | None,
    analytics_results: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    if not metadata.get("project_name"):
        return "Create a project to document your analysis workflow."
    if active_dataset is None:
        return "Load a dataset to start profiling, preparation and analytics."
    if analytics_results.get("generic_quality_report") is None:
        return "Review Data Quality to calculate the quality report."
    if analytics_results.get("data_dictionary_result") is None:
        return "Open Data Dictionary to generate column-level documentation."
    if summary.get("Mapping status") == "Open":
        return "Map required fields on the Column Mapping page."
    if summary.get("Analytics results") == "None yet":
        return "Run Generic Analytics or the selected domain analytics page."
    return "Export a BI-ready package or download a Project Backup."
