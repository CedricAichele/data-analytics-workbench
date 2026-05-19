"""Business-friendly in-session project metadata helpers."""

from __future__ import annotations

from collections.abc import MutableMapping
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

import streamlit as st


PROJECT_METADATA_KEY = "project_metadata"
PROJECTS_KEY = "projects"
ACTIVE_PROJECT_ID_KEY = "active_project_id"
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
        "project_id": "",
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
    """Initialize project workspace keys without requiring a dataset."""
    current = _state(state)
    current.setdefault(PROJECT_METADATA_KEY, default_project_metadata())
    current.setdefault(PROJECTS_KEY, {})
    current.setdefault(ACTIVE_PROJECT_ID_KEY, None)
    current.setdefault("project_draft_active", False)

    active_id = current.get(ACTIVE_PROJECT_ID_KEY)
    if current.get("project_draft_active"):
        current[PROJECT_METADATA_KEY] = current.get(PROJECT_METADATA_KEY, default_project_metadata())
        return
    if active_id and active_id in current[PROJECTS_KEY]:
        current[PROJECT_METADATA_KEY] = dict(current[PROJECTS_KEY][active_id]["metadata"])
        return

    legacy_metadata = dict(current.get(PROJECT_METADATA_KEY, {}))
    if legacy_metadata.get("project_name") and not current[PROJECTS_KEY]:
        project_id, _ = add_or_activate_project(legacy_metadata, state=current)
        current[ACTIVE_PROJECT_ID_KEY] = project_id
        sync_active_project_metadata(current)
    elif current[PROJECTS_KEY] and not active_id:
        current[ACTIVE_PROJECT_ID_KEY] = next(iter(current[PROJECTS_KEY]))
        sync_active_project_metadata(current)


def compute_project_signature(metadata: dict[str, Any], backup_hash: str | None = None) -> str:
    """Return a stable signature for duplicate project detection."""
    comparable = _normalized_project_payload(metadata)
    if backup_hash:
        comparable["backup_hash"] = backup_hash
    payload = json.dumps(comparable, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def add_or_activate_project(
    metadata: dict[str, Any],
    *,
    state: MutableMapping[str, Any] | None = None,
    backup_hash: str | None = None,
    associated_dataset_ids: list[str] | None = None,
) -> tuple[str, bool]:
    """Compatibility helper that creates or activates an existing duplicate project."""
    return create_project(
        metadata,
        state=state,
        backup_hash=backup_hash,
        associated_dataset_ids=associated_dataset_ids,
    )


def create_project(
    metadata: dict[str, Any],
    *,
    state: MutableMapping[str, Any] | None = None,
    backup_hash: str | None = None,
    associated_dataset_ids: list[str] | None = None,
) -> tuple[str, bool]:
    """Create and activate a project while preserving the existing workspace.

    Returns `(project_id, created)`. If the same project metadata or backup is
    already loaded, the existing project is activated and `created` is False.
    """
    current = _state(state)
    current.setdefault(PROJECT_METADATA_KEY, default_project_metadata())
    current.setdefault(PROJECTS_KEY, {})
    current.setdefault(ACTIVE_PROJECT_ID_KEY, None)
    current.setdefault("project_draft_active", False)

    merged = default_project_metadata()
    merged.update({key: value for key, value in dict(metadata or {}).items() if key in merged})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not merged.get("created_at"):
        merged["created_at"] = now
    merged["updated_at"] = now

    signature = compute_project_signature(merged)
    for project_id, project in current[PROJECTS_KEY].items():
        if backup_hash and project.get("backup_hash") == backup_hash:
            current[ACTIVE_PROJECT_ID_KEY] = project_id
            current["project_draft_active"] = False
            sync_active_project_metadata(current)
            _activate_project_dataset_if_available(project, current)
            return project_id, False
        if project.get("project_signature") == signature:
            current[ACTIVE_PROJECT_ID_KEY] = project_id
            current["project_draft_active"] = False
            sync_active_project_metadata(current)
            _activate_project_dataset_if_available(project, current)
            return project_id, False

    merged["project_name"] = _safe_unique_project_name(merged.get("project_name") or "Analytics Project", current[PROJECTS_KEY])
    requested_id = str(merged.get("project_id") or "").strip()
    project_id = requested_id if requested_id and requested_id not in current[PROJECTS_KEY] else _new_project_id(merged.get("project_name", "Analytics Project"), current[PROJECTS_KEY])
    merged["project_id"] = project_id
    current[PROJECTS_KEY][project_id] = {
        "project_id": project_id,
        "metadata": dict(merged),
        "project_signature": signature,
        "backup_hash": backup_hash,
        "associated_dataset_ids": list(associated_dataset_ids or []),
        "created_at": merged["created_at"],
        "updated_at": merged["updated_at"],
    }
    current[ACTIVE_PROJECT_ID_KEY] = project_id
    current["project_draft_active"] = False
    sync_active_project_metadata(current)
    return project_id, True


def update_active_project(
    metadata: dict[str, Any] | None = None,
    *,
    state: MutableMapping[str, Any] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Update only the active project and preserve every other project."""
    current = _state(state)
    initialize_project_state(current)
    active_id = current.get(ACTIVE_PROJECT_ID_KEY)
    if not active_id or active_id not in current[PROJECTS_KEY]:
        raise ValueError("No active project is available to update.")

    project = current[PROJECTS_KEY][active_id]
    existing = dict(project["metadata"])
    updates = dict(metadata or {})
    updates.update(fields)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    existing.update({key: value for key, value in updates.items() if key in existing})
    existing["project_id"] = active_id
    existing["updated_at"] = now
    if not existing.get("created_at"):
        existing["created_at"] = project.get("created_at") or now

    project["metadata"] = dict(existing)
    project["project_signature"] = compute_project_signature(existing)
    project["updated_at"] = now
    current[PROJECT_METADATA_KEY] = dict(existing)
    current["project_draft_active"] = False
    return dict(existing)


def list_projects(state: MutableMapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return project workspace records for display."""
    current = _state(state)
    initialize_project_state(current)
    return [
        {
            "project_id": project_id,
            "project_name": project["metadata"].get("project_name") or "Untitled project",
            "selected_workflow": project["metadata"].get("selected_workflow", "Quick Data Check"),
            "suggested_template": project["metadata"].get("suggested_template", "Generic"),
            "updated_at": project.get("updated_at", ""),
            "associated_dataset_ids": list(project.get("associated_dataset_ids", [])),
        }
        for project_id, project in current[PROJECTS_KEY].items()
    ]


def get_active_project(state: MutableMapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Return the active project workspace record."""
    current = _state(state)
    initialize_project_state(current)
    active_id = current.get(ACTIVE_PROJECT_ID_KEY)
    if not active_id:
        return None
    return current[PROJECTS_KEY].get(active_id)


def set_active_project(project_id: str, state: MutableMapping[str, Any] | None = None) -> None:
    """Activate a project and synchronize the displayed metadata."""
    current = _state(state)
    initialize_project_state(current)
    if project_id not in current[PROJECTS_KEY]:
        raise ValueError(f"Unknown project id: {project_id}")
    current[ACTIVE_PROJECT_ID_KEY] = project_id
    current["project_draft_active"] = False
    sync_active_project_metadata(current)
    _activate_project_dataset_if_available(current[PROJECTS_KEY][project_id], current)


def start_new_project_draft(state: MutableMapping[str, Any] | None = None) -> None:
    """Clear the active project selection and show an empty project form."""
    current = _state(state)
    current.setdefault(PROJECTS_KEY, {})
    current[ACTIVE_PROJECT_ID_KEY] = None
    current["project_draft_active"] = True
    current[PROJECT_METADATA_KEY] = default_project_metadata()


def associate_dataset_with_active_project(dataset_id: str, state: MutableMapping[str, Any] | None = None) -> None:
    """Remember that the active project has used a dataset in this session."""
    current = _state(state)
    initialize_project_state(current)
    active = get_active_project(current)
    if active is None or not dataset_id:
        return
    associated = active.setdefault("associated_dataset_ids", [])
    if dataset_id not in associated:
        associated.append(dataset_id)
    active["metadata"]["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    active["updated_at"] = active["metadata"]["updated_at"]
    sync_active_project_metadata(current)


def sync_active_project_metadata(state: MutableMapping[str, Any] | None = None) -> None:
    """Keep the legacy project metadata key aligned with the active project."""
    current = _state(state)
    active_id = current.get(ACTIVE_PROJECT_ID_KEY)
    project = current.get(PROJECTS_KEY, {}).get(active_id) if active_id else None
    if project is None:
        current[PROJECT_METADATA_KEY] = default_project_metadata()
        return
    current[PROJECT_METADATA_KEY] = dict(project["metadata"])


def update_project_metadata(
    metadata: dict[str, Any] | None = None,
    state: MutableMapping[str, Any] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Compatibility wrapper for legacy callers.

    New UI code should use `create_project` or `update_active_project` so create
    and update intent remains explicit.
    """
    current = _state(state)
    initialize_project_state(current)
    updates = dict(metadata or {})
    updates.update(fields)
    active_id = current.get(ACTIVE_PROJECT_ID_KEY)
    if active_id and active_id in current[PROJECTS_KEY]:
        return update_active_project(updates, state=current)
    project_id, _ = create_project(updates, state=current)
    return dict(current[PROJECTS_KEY][project_id]["metadata"])


def get_project_metadata(state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the current project metadata."""
    current = _state(state)
    initialize_project_state(current)
    return dict(current[PROJECT_METADATA_KEY])


def set_project_metadata(metadata: dict[str, Any], state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    """Replace project metadata, merging with defaults for missing keys."""
    current = _state(state)
    project_id, _ = add_or_activate_project(metadata, state=current)
    return dict(current[PROJECTS_KEY][project_id]["metadata"])


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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def _new_project_id(project_name: str, projects: dict[str, Any]) -> str:
    base = _slugify(project_name)
    candidate = base
    suffix = 2
    while candidate in projects:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _safe_unique_project_name(project_name: str, projects: dict[str, Any]) -> str:
    existing_names = {
        str(project.get("metadata", {}).get("project_name", "")).strip()
        for project in projects.values()
    }
    base = project_name.strip() or "Analytics Project"
    if base not in existing_names:
        return base
    suffix = 2
    candidate = f"{base} ({suffix})"
    while candidate in existing_names:
        suffix += 1
        candidate = f"{base} ({suffix})"
    return candidate


def _normalized_project_payload(metadata: dict[str, Any]) -> dict[str, Any]:
    excluded = {"project_id", "created_at", "updated_at"}
    payload = {
        key: value
        for key, value in dict(metadata or {}).items()
        if key not in excluded and key in default_project_metadata()
    }
    if isinstance(payload.get("desired_outputs"), list):
        payload["desired_outputs"] = sorted(str(value) for value in payload["desired_outputs"])
    return payload


def _activate_project_dataset_if_available(project: dict[str, Any], state: MutableMapping[str, Any]) -> None:
    datasets = state.get("datasets", {})
    for dataset_id in project.get("associated_dataset_ids", []):
        if dataset_id in datasets:
            state["active_dataset_id"] = dataset_id
            try:
                from app.services.dataset_workspace import sync_legacy_state

                sync_legacy_state(state)
            except Exception:
                pass
            return
