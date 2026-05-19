"""Project Backup ZIP creation and loading helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import re
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from app.services.data_dictionary import generate_data_dictionary
from app.services.export_package import build_quality_report_sheet
from app.services.export_service import dataframe_to_excel_bytes


@dataclass(frozen=True)
class ProjectBackupLoadResult:
    project_metadata: dict[str, Any]
    dataset_metadata: dict[str, Any]
    transformation_log: list[str]
    column_mappings: dict[str, Any]
    quality_summary: dict[str, Any]
    cleaned_dataset: pd.DataFrame | None
    messages: list[str]
    backup_hash: str = ""


def safe_project_filename(project_name: str, suffix: str = "project_backup", extension: str = "zip") -> str:
    """Build a business-friendly backup filename."""
    slug = re.sub(r"[^a-z0-9]+", "_", (project_name or "analytics_project").lower()).strip("_")
    return f"{slug or 'analytics_project'}_{suffix}.{extension.lstrip('.')}"


def build_project_readme(project_metadata: dict[str, Any], *, includes_dataset: bool) -> str:
    """Explain Project Backup contents in plain language."""
    project_name = project_metadata.get("project_name") or "Analytics Project"
    dataset_line = (
        "A cleaned working dataset is included and can be restored as a dataset in the Workbench."
        if includes_dataset
        else "The original source dataset is not included. Upload it again to continue analysis."
    )
    return "\n".join(
        [
            f"Project Backup: {project_name}",
            "",
            "This file stores project documentation, workflow choices, mappings and available analysis context.",
            dataset_line,
            "",
            "Typical use:",
            "1. Load this Project Backup in Data Analytics Workbench.",
            "2. Review the restored project details.",
            "3. Upload or restore the dataset if needed.",
            "4. Continue profiling, preparation, mapping, analytics or exports.",
            "",
            "This backup is intended for continuing work in the Workbench. The BI-ready Export Package is the better file for sharing analysis outputs with business users.",
        ]
    )


def serialize_project_state(
    project_metadata: dict[str, Any],
    active_dataset: dict[str, Any] | None = None,
    quality_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a compact serializable project state dictionary."""
    return {
        "project_metadata": dict(project_metadata or {}),
        "dataset_metadata": dict((active_dataset or {}).get("metadata", {})),
        "dataset_name": (active_dataset or {}).get("name"),
        "transformation_log": list((active_dataset or {}).get("transformation_log", [])),
        "column_mappings": dict((active_dataset or {}).get("template_mappings", {})),
        "quality_summary": dict(quality_summary or {}),
    }


def build_project_backup_zip(
    *,
    project_metadata: dict[str, Any],
    active_dataset: dict[str, Any] | None = None,
    data_dictionary: pd.DataFrame | None = None,
    quality_report: Any | None = None,
    quality_rules: pd.DataFrame | None = None,
    include_cleaned_dataset: bool = True,
) -> bytes:
    """Build a Project Backup ZIP in memory."""
    output = BytesIO()
    working_df = (active_dataset or {}).get("working_df")
    quality_summary = _quality_report_to_dict(quality_report)
    project_state = serialize_project_state(project_metadata, active_dataset, quality_summary)
    dataset_included = include_cleaned_dataset and isinstance(working_df, pd.DataFrame) and not working_df.empty
    dictionary_df = data_dictionary
    if dictionary_df is None and isinstance(working_df, pd.DataFrame):
        dictionary_df = generate_data_dictionary(
            working_df,
            template_mappings=(active_dataset or {}).get("template_mappings", {}),
        )

    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as backup:
        backup.writestr("project_state.json", _to_json(project_state))
        backup.writestr("project_metadata.json", _to_json(project_metadata or {}))
        backup.writestr("dataset_metadata.json", _to_json(project_state["dataset_metadata"]))
        backup.writestr("transformation_log.json", _to_json(project_state["transformation_log"]))
        backup.writestr("column_mappings.json", _to_json(project_state["column_mappings"]))
        backup.writestr("quality_summary.json", _to_json(quality_summary))
        backup.writestr("README_Project_Backup.txt", build_project_readme(project_metadata, includes_dataset=dataset_included))
        if isinstance(dictionary_df, pd.DataFrame) and not dictionary_df.empty:
            backup.writestr("data_dictionary.xlsx", dataframe_to_excel_bytes(dictionary_df, sheet_name="Data_Dictionary"))
        if isinstance(quality_rules, pd.DataFrame) and not quality_rules.empty:
            backup.writestr("quality_rules.xlsx", dataframe_to_excel_bytes(quality_rules, sheet_name="Quality_Rules"))
        if quality_report is not None:
            backup.writestr("data_quality_report.xlsx", dataframe_to_excel_bytes(build_quality_report_sheet(quality_report, quality_rules), sheet_name="Data_Quality"))
        if dataset_included:
            backup.writestr("cleaned_dataset.csv", working_df.to_csv(index=False).encode("utf-8"))
    return output.getvalue()


def load_project_backup_zip(file_or_bytes: Any) -> ProjectBackupLoadResult:
    """Load a Project Backup ZIP and return restorable parts."""
    raw_bytes = file_or_bytes.getvalue() if hasattr(file_or_bytes, "getvalue") else bytes(file_or_bytes)
    backup_hash = hashlib.sha256(raw_bytes).hexdigest()
    messages: list[str] = []
    with ZipFile(BytesIO(raw_bytes), mode="r") as backup:
        names = set(backup.namelist())
        project_metadata = _read_json(backup, "project_metadata.json") if "project_metadata.json" in names else {}
        if not project_metadata and "project_state.json" in names:
            project_metadata = _read_json(backup, "project_state.json").get("project_metadata", {})
        dataset_metadata = _read_json(backup, "dataset_metadata.json") if "dataset_metadata.json" in names else {}
        transformation_log = _read_json(backup, "transformation_log.json") if "transformation_log.json" in names else []
        column_mappings = _read_json(backup, "column_mappings.json") if "column_mappings.json" in names else {}
        quality_summary = _read_json(backup, "quality_summary.json") if "quality_summary.json" in names else {}
        cleaned_dataset = None
        if "cleaned_dataset.csv" in names:
            cleaned_dataset = pd.read_csv(BytesIO(backup.read("cleaned_dataset.csv")))
            messages.append("Restored the cleaned working dataset from the Project Backup.")
        else:
            messages.append("This project backup restored metadata, mappings and workflow state. Please upload the source dataset again to continue analysis.")

    return ProjectBackupLoadResult(
        project_metadata=project_metadata,
        dataset_metadata=dataset_metadata,
        transformation_log=list(transformation_log or []),
        column_mappings=dict(column_mappings or {}),
        quality_summary=dict(quality_summary or {}),
        cleaned_dataset=cleaned_dataset,
        messages=messages,
        backup_hash=backup_hash,
    )


def deserialize_project_state(backup_result: ProjectBackupLoadResult) -> dict[str, Any]:
    """Return a simple state payload from a loaded backup."""
    return {
        "project_metadata": backup_result.project_metadata,
        "dataset_metadata": backup_result.dataset_metadata,
        "transformation_log": backup_result.transformation_log,
        "column_mappings": backup_result.column_mappings,
        "quality_summary": backup_result.quality_summary,
        "has_cleaned_dataset": backup_result.cleaned_dataset is not None,
    }


def _quality_report_to_dict(report: Any | None) -> dict[str, Any]:
    if report is None:
        return {}
    return {
        "overall_score": getattr(report, "overall_score", None),
        "sub_scores": getattr(report, "sub_scores", {}),
        "metrics": getattr(report, "metrics", {}),
        "explanations": getattr(report, "explanations", []),
        "recommended_fixes": getattr(report, "recommended_fixes", []),
    }


def _read_json(backup: ZipFile, name: str) -> Any:
    return json.loads(backup.read(name).decode("utf-8"))


def _to_json(value: Any) -> str:
    return json.dumps(value, indent=2, default=_json_default)


def _json_default(value: Any) -> str | float | int | None:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
