"""BI-ready multi-sheet Excel export package helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import re

import pandas as pd

from app.services.export_service import transformation_log_to_dataframe
from app.services.quality_score import DataQualityReport


def safe_excel_sheet_name(name: str) -> str:
    """Return a valid Excel sheet name with the 31-character limit."""
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", " ", name).strip()
    return (cleaned or "Sheet")[:31]


def build_quality_report_sheet(report: DataQualityReport | None, quality_rules: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build a compact quality report sheet."""
    rows: list[dict[str, object]] = []
    if report is not None:
        rows.append({"section": "overall", "metric": "overall_score", "value": report.overall_score})
        for name, score in report.sub_scores.items():
            rows.append({"section": "sub_score", "metric": name, "value": score})
        for name, value in report.metrics.items():
            rows.append({"section": "metric", "metric": name, "value": value})
        for explanation in report.explanations:
            rows.append({"section": "explanation", "metric": "note", "value": explanation})
        for fix in report.recommended_fixes:
            rows.append({"section": "recommended_fix", "metric": "fix", "value": fix})
    if quality_rules is not None and not quality_rules.empty:
        rows.append({"section": "template_rules", "metric": "rule_count", "value": len(quality_rules)})
    return pd.DataFrame(rows or [{"section": "quality", "metric": "status", "value": "No quality report available"}])


def build_transformation_log_sheet(log: list[str] | tuple[str, ...] | None) -> pd.DataFrame:
    """Build the transformation log sheet."""
    log_df = transformation_log_to_dataframe(list(log or []))
    if log_df.empty:
        return pd.DataFrame([{"step": 0, "transformation": "No transformations logged"}])
    return log_df


def build_kpi_summary_sheet(
    result_tables: dict[str, pd.DataFrame] | None = None,
    kpi_summary: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Summarize available result table row counts for workbook readers."""
    if kpi_summary is not None and not kpi_summary.empty:
        return kpi_summary
    rows = [
        {"result_table": name, "rows": len(table), "columns": len(table.columns)}
        for name, table in (result_tables or {}).items()
        if isinstance(table, pd.DataFrame)
    ]
    return pd.DataFrame(rows or [{"result_table": "No KPI result tables available", "rows": 0, "columns": 0}])


def build_readme_sheet(
    *,
    project_metadata: dict | None,
    dataset_name: str,
    cleaned_data: pd.DataFrame,
    included_sheets: list[str],
) -> pd.DataFrame:
    """Build the first sheet that explains the workbook contents."""
    metadata = project_metadata or {}
    rows = [
        {"section": "Project", "item": "Project name", "value": metadata.get("project_name") or "Not documented"},
        {"section": "Project", "item": "Selected workflow", "value": metadata.get("selected_workflow") or "Not documented"},
        {"section": "Project", "item": "Selected template", "value": metadata.get("suggested_template") or "Generic"},
        {"section": "Dataset", "item": "Active dataset", "value": dataset_name or "Active working dataset"},
        {"section": "Dataset", "item": "Rows", "value": len(cleaned_data)},
        {"section": "Dataset", "item": "Columns", "value": len(cleaned_data.columns)},
        {"section": "Export", "item": "Export timestamp", "value": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        {
            "section": "Export",
            "item": "Working data note",
            "value": "Cleaned_Data reflects user-triggered transformations applied to the working dataset.",
        },
        {
            "section": "Export",
            "item": "Included sheets",
            "value": ", ".join(included_sheets),
        },
    ]
    return pd.DataFrame(rows)


def build_export_workbook(
    *,
    cleaned_data: pd.DataFrame,
    data_dictionary: pd.DataFrame,
    project_metadata: dict | None = None,
    dataset_name: str = "",
    quality_report: DataQualityReport | None = None,
    quality_rules: pd.DataFrame | None = None,
    quality_issues: pd.DataFrame | None = None,
    transformation_log: list[str] | tuple[str, ...] | None = None,
    generic_analytics_result: pd.DataFrame | None = None,
    kpi_summary: pd.DataFrame | None = None,
    result_tables: dict[str, pd.DataFrame] | None = None,
) -> bytes:
    """Build a BI-ready multi-sheet Excel workbook as bytes."""
    output = BytesIO()
    base_sheets: dict[str, pd.DataFrame] = {
        "Cleaned_Data": cleaned_data,
        "Data_Dictionary": data_dictionary,
        "Data_Quality": build_quality_report_sheet(quality_report, quality_rules),
        "Transformation_Log": build_transformation_log_sheet(transformation_log),
        "KPI_Summary": build_kpi_summary_sheet(result_tables, kpi_summary),
    }
    if quality_rules is not None and not quality_rules.empty:
        base_sheets["Quality_Rules"] = quality_rules
    if quality_issues is not None and not quality_issues.empty:
        base_sheets["Quality_Issues"] = quality_issues
    if generic_analytics_result is not None and not generic_analytics_result.empty:
        base_sheets["Generic_Analytics_Result"] = generic_analytics_result
    for name, table in (result_tables or {}).items():
        if isinstance(table, pd.DataFrame) and not table.empty:
            base_sheets[name] = table
    base_sheets = {
        "01_Readme": build_readme_sheet(
            project_metadata=project_metadata,
            dataset_name=dataset_name,
            cleaned_data=cleaned_data,
            included_sheets=list(base_sheets),
        ),
        **base_sheets,
    }

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        used_names: set[str] = set()
        for sheet_name, sheet_df in base_sheets.items():
            safe_name = _dedupe_sheet_name(safe_excel_sheet_name(sheet_name), used_names)
            used_names.add(safe_name)
            sheet_df.to_excel(writer, index=False, sheet_name=safe_name)
    return output.getvalue()


def _dedupe_sheet_name(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        return name
    suffix = 2
    while True:
        suffix_text = f"_{suffix}"
        candidate = f"{name[:31 - len(suffix_text)]}{suffix_text}"
        if candidate not in used_names:
            return candidate
        suffix += 1
