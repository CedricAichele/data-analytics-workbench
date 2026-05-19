from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
import streamlit as st

from app.components.layout import configure_page, page_title
from app.services.data_dictionary import generate_data_dictionary
from app.services.dataset_workspace import (
    get_active_analytics_result,
    get_active_dataset,
    get_active_transformation_log,
    initialize_workspace,
    set_active_analytics_result,
)
from app.services.export_package import build_export_workbook, build_quality_report_sheet
from app.services.export_service import (
    build_export_filename,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    dataframe_to_json_bytes,
    transformation_log_to_dataframe,
)
from app.services.quality_rules import run_template_quality_rules
from app.services.quality_score import calculate_quality_score


def _download_buttons(df: pd.DataFrame, suffix: str, label_prefix: str, key_prefix: str, dataset_name: str) -> None:
    button_cols = st.columns(3)
    button_cols[0].download_button(
        f"{label_prefix} CSV",
        data=dataframe_to_csv_bytes(df),
        file_name=build_export_filename(dataset_name, suffix, "csv"),
        mime="text/csv",
        key=f"{key_prefix}-csv",
    )
    button_cols[1].download_button(
        f"{label_prefix} Excel",
        data=dataframe_to_excel_bytes(df, sheet_name=suffix),
        file_name=build_export_filename(dataset_name, suffix, "xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"{key_prefix}-xlsx",
    )
    button_cols[2].download_button(
        f"{label_prefix} JSON",
        data=dataframe_to_json_bytes(df),
        file_name=build_export_filename(dataset_name, suffix, "json"),
        mime="application/json",
        key=f"{key_prefix}-json",
    )


def _result_tables(result: Any, table_names: Iterable[str]) -> list[tuple[str, pd.DataFrame]]:
    tables: list[tuple[str, pd.DataFrame]] = []
    metrics = getattr(result, "metrics", None)
    if isinstance(metrics, dict) and metrics:
        tables.append(("metrics", pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()])))
    for name in table_names:
        value = getattr(result, name, None)
        if isinstance(value, pd.DataFrame) and not value.empty:
            tables.append((name, value))
    return tables


def _build_display_sections(
    result_sources: list[tuple[str, str, Any, list[str]]],
    controlled_result_sources: list[tuple[str, Any]],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for result_label, package_sheet, result, table_names in result_sources:
        if result is None:
            continue
        sections.append(
            {
                "label": result_label,
                "package_sheet": package_sheet,
                "tables": _result_tables(result, table_names),
            }
        )
    for result_label, result in controlled_result_sources:
        if not isinstance(result, dict):
            continue
        tables = [(name, table) for name, table in result.items() if isinstance(table, pd.DataFrame) and not table.empty]
        if tables:
            sections.append({"label": result_label, "package_sheet": None, "tables": tables})
    return sections


def _pack_named_tables(tables: list[tuple[str, pd.DataFrame]]) -> pd.DataFrame:
    packed: list[pd.DataFrame] = []
    for table_name, table_df in tables:
        if not isinstance(table_df, pd.DataFrame) or table_df.empty:
            continue
        preview = table_df.head(500).copy()
        preview.insert(0, "source_table", table_name)
        packed.append(preview)
    if not packed:
        return pd.DataFrame()
    return pd.concat(packed, ignore_index=True, sort=False)


def _kpi_summary_table(generic_result: Any, result_sources: list[tuple[str, str, Any, list[str]]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if generic_result is not None:
        rows.append(
            {
                "source": "Generic Analytics",
                "metric": "rows_used",
                "value": getattr(generic_result, "rows_used", None),
            }
        )
        rows.append(
            {
                "source": "Generic Analytics",
                "metric": "measures",
                "value": ", ".join(getattr(generic_result, "measure_columns", []) or []),
            }
        )
        aggregated = getattr(generic_result, "aggregated", None)
        if isinstance(aggregated, pd.DataFrame):
            rows.append({"source": "Generic Analytics", "metric": "result_rows", "value": len(aggregated)})

    for label, _, result, _ in result_sources:
        metrics = getattr(result, "metrics", None)
        if isinstance(metrics, dict):
            rows.extend({"source": label, "metric": key, "value": value} for key, value in metrics.items())

    return pd.DataFrame(rows, columns=["source", "metric", "value"])


def _quality_rules_for_mappings(df: pd.DataFrame, template_mappings: dict[str, dict[str, str | None]]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for template_id, mapping in template_mappings.items():
        if not mapping:
            continue
        rules = run_template_quality_rules(df, template_id, mapping)
        if not rules.empty:
            frames.append(rules)
    if not frames:
        return pd.DataFrame(
            columns=[
                "template",
                "rule_name",
                "severity",
                "affected_rows_count",
                "affected_percentage",
                "explanation",
                "recommended_fix",
            ]
        )
    return pd.concat(frames, ignore_index=True)


configure_page("Export Center")
page_title("Export Center", "Download working data, documentation, quality checks, and result tables.")

initialize_workspace()
active = get_active_dataset()
if active is None:
    st.warning("Load a CSV, XLSX, JSON, or sample dataset before exporting.")
    st.stop()

dataset_name = active.get("name", "dataset")
metadata = active.get("metadata", {})
working_df = active["working_df"]
raw_df = active["raw_df"]
template_mappings = active.get("template_mappings", {})

data_dictionary_df = generate_data_dictionary(working_df, template_mappings=template_mappings)
quality_report = get_active_analytics_result("generic_quality_report") or calculate_quality_score(working_df)
quality_rules_df = _quality_rules_for_mappings(working_df, template_mappings)
quality_report_df = build_quality_report_sheet(quality_report, quality_rules_df)
set_active_analytics_result("data_dictionary_result", data_dictionary_df)
set_active_analytics_result("generic_quality_report", quality_report)
set_active_analytics_result("quality_rules_result", quality_rules_df)

st.subheader("Active Dataset")
status_cols = st.columns(4)
status_cols[0].metric("Dataset", dataset_name)
status_cols[1].metric("Source", str(metadata.get("source", "dataset")))
status_cols[2].metric("File type", str(metadata.get("file_type", "data")))
status_cols[3].metric("Working shape", f"{len(working_df):,} x {len(working_df.columns):,}")

st.caption(
    "The standard export target is the active working dataset. "
    "Use raw export only when you need the unchanged source copy."
)

st.subheader("A. Export Active Working Dataset")
export_raw = st.checkbox("Export raw dataset instead of working dataset", value=False)
dataset_to_export = raw_df if export_raw else working_df
dataset_suffix = "raw_dataset" if export_raw else "working_dataset"
st.dataframe(dataset_to_export.head(20), use_container_width=True, hide_index=True)
_download_buttons(dataset_to_export, dataset_suffix, "Download dataset as", "dataset-export", dataset_name)

st.subheader("B. Export Documentation")
doc_tabs = st.tabs(["Data Dictionary", "Transformation Log", "Data Quality Report", "Quality Rules"])

with doc_tabs[0]:
    st.caption("Generated from the active working dataset.")
    st.dataframe(data_dictionary_df, use_container_width=True, hide_index=True)
    _download_buttons(data_dictionary_df, "data_dictionary", "Download dictionary as", "dictionary-export", dataset_name)

with doc_tabs[1]:
    log_df = transformation_log_to_dataframe(get_active_transformation_log())
    if log_df.empty:
        st.info("No transformations have been logged for the active dataset.")
    else:
        st.dataframe(log_df, use_container_width=True, hide_index=True)
    log_cols = st.columns(2)
    log_cols[0].download_button(
        "Download log as CSV",
        data=dataframe_to_csv_bytes(log_df),
        file_name=build_export_filename(dataset_name, "transformation_log", "csv"),
        mime="text/csv",
        key="transformation-log-csv",
    )
    log_cols[1].download_button(
        "Download log as JSON",
        data=dataframe_to_json_bytes(log_df),
        file_name=build_export_filename(dataset_name, "transformation_log", "json"),
        mime="application/json",
        key="transformation-log-json",
    )

with doc_tabs[2]:
    st.dataframe(quality_report_df, use_container_width=True, hide_index=True)
    quality_cols = st.columns(2)
    quality_cols[0].download_button(
        "Download quality report as CSV",
        data=dataframe_to_csv_bytes(quality_report_df),
        file_name=build_export_filename(dataset_name, "data_quality_report", "csv"),
        mime="text/csv",
        key="quality-report-csv",
    )
    quality_cols[1].download_button(
        "Download quality report as Excel",
        data=dataframe_to_excel_bytes(quality_report_df, sheet_name="Data_Quality"),
        file_name=build_export_filename(dataset_name, "data_quality_report", "xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="quality-report-xlsx",
    )

with doc_tabs[3]:
    if quality_rules_df.empty:
        st.info("No template-specific quality rules are available until a compatible template mapping is saved.")
    else:
        st.dataframe(quality_rules_df, use_container_width=True, hide_index=True)
    rule_cols = st.columns(2)
    rule_cols[0].download_button(
        "Download rules as CSV",
        data=dataframe_to_csv_bytes(quality_rules_df),
        file_name=build_export_filename(dataset_name, "quality_rules", "csv"),
        mime="text/csv",
        key="quality-rules-csv",
    )
    rule_cols[1].download_button(
        "Download rules as Excel",
        data=dataframe_to_excel_bytes(quality_rules_df, sheet_name="Quality_Rules"),
        file_name=build_export_filename(dataset_name, "quality_rules", "xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="quality-rules-xlsx",
    )

generic_result = get_active_analytics_result("generic_analytics_result")
generic_table = getattr(generic_result, "aggregated", None)
result_sources = [
    (
        "Sales / Retail Analytics",
        "Sales_Results",
        get_active_analytics_result("retail_analytics_result"),
        ["monthly_revenue", "product_performance", "country_performance", "customer_rfm", "segment_summary", "issue_summary"],
    ),
    (
        "Manufacturing Analytics",
        "Manufacturing_Results",
        get_active_analytics_result("manufacturing_analytics_result"),
        ["machine_performance", "output_over_time", "downtime_over_time", "output_by_line", "output_by_shift", "issue_summary"],
    ),
    (
        "Logistics Analytics",
        "Logistics_Results",
        get_active_analytics_result("logistics_analytics_result"),
        ["shipments_over_time", "lead_time_over_time", "status_summary", "carrier_performance", "destination_performance", "delayed_shipments", "issue_summary"],
    ),
    (
        "Finance Analytics",
        "Finance_Results",
        get_active_analytics_result("finance_analytics_result"),
        ["monthly_summary", "category_summary", "cost_center_summary", "largest_transactions", "issue_summary"],
    ),
]
controlled_result_sources = [
    ("Generic Analytics Chart / Result Data", get_active_analytics_result("generic_controlled_chart_result")),
    ("Sales / Retail Controlled Charts", get_active_analytics_result("retail_controlled_chart_result")),
    ("Manufacturing Controlled Charts", get_active_analytics_result("manufacturing_controlled_chart_result")),
    ("Logistics Controlled Charts", get_active_analytics_result("logistics_controlled_chart_result")),
    ("Finance Controlled Charts", get_active_analytics_result("finance_controlled_chart_result")),
]

package_tables: dict[str, pd.DataFrame] = {}
display_sections = _build_display_sections(result_sources, controlled_result_sources)
kpi_summary_df = _kpi_summary_table(generic_result, result_sources)
for section in display_sections:
    if section["package_sheet"] and section["tables"]:
        package_tables[section["package_sheet"]] = _pack_named_tables(section["tables"])
result_table_pack = _pack_named_tables(
    [
        (f"{section['label']} - {table_name}", table_df)
        for section in display_sections
        for table_name, table_df in section["tables"]
    ]
)
if not result_table_pack.empty:
    package_tables["Result_Tables"] = result_table_pack

st.subheader("C. KPI Summary Export")
if kpi_summary_df.empty:
    st.info("No KPI summaries are available yet. Run Generic Analytics or a compatible domain analytics page first.")
else:
    st.dataframe(kpi_summary_df, use_container_width=True, hide_index=True)
    _download_buttons(kpi_summary_df, "kpi_summary", "Download KPI summary as", "kpi-summary-export", dataset_name)

st.subheader("D. BI-ready Export Package")
st.caption(
    "Creates one Excel workbook with the active working dataset, data dictionary, quality report, "
    "transformation log, and available result tables."
)
package_bytes = build_export_workbook(
    cleaned_data=working_df,
    data_dictionary=data_dictionary_df,
    quality_report=quality_report,
    quality_rules=quality_rules_df,
    transformation_log=get_active_transformation_log(),
    generic_analytics_result=generic_table if isinstance(generic_table, pd.DataFrame) else None,
    kpi_summary=kpi_summary_df,
    result_tables=package_tables,
)
st.download_button(
    "Download BI-ready Excel package",
    data=package_bytes,
    file_name=build_export_filename(dataset_name, "bi_ready_export_package", "xlsx"),
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="bi-ready-export-package",
)

st.subheader("E. Export Chart / Result Data")
available_results = False
if isinstance(generic_table, pd.DataFrame) and not generic_table.empty:
    available_results = True
    with st.expander("Generic Analytics", expanded=False):
        st.markdown("**Aggregated Result**")
        st.dataframe(generic_table, use_container_width=True, hide_index=True)
        _download_buttons(generic_table, "generic_analytics_result", "Download table as", "generic-analytics-result", dataset_name)

for section in display_sections:
    tables = section["tables"]
    if not tables:
        continue
    available_results = True
    with st.expander(section["label"], expanded=False):
        for table_name, table_df in tables:
            st.markdown(f"**{table_name.replace('_', ' ').title()}**")
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            _download_buttons(
                table_df,
                f"{section['label']}_{table_name}",
                "Download table as",
                f"{section['label']}-{table_name}".lower().replace(" ", "-").replace("/", "-"),
                dataset_name,
            )

if not available_results:
    st.info("No analytics result tables are available yet. Run Generic Analytics or a compatible domain analytics page first.")
