from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
import streamlit as st

from app.components.layout import configure_page, page_title
from app.services.dataset_workspace import (
    get_active_analytics_result,
    get_active_dataset,
    get_active_transformation_log,
    initialize_workspace,
)
from app.services.export_service import (
    build_export_filename,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    dataframe_to_json_bytes,
    transformation_log_to_dataframe,
)


configure_page("Export Center")
page_title("Export Center", "Download the active working dataset, transformation log, and calculated result tables.")

initialize_workspace()
active = get_active_dataset()
if active is None:
    st.warning("Load a CSV, XLSX, JSON, or sample dataset before exporting.")
    st.stop()

dataset_name = active.get("name", "dataset")
metadata = active.get("metadata", {})
working_df = active["working_df"]
raw_df = active["raw_df"]

st.subheader("Active Dataset")
status_cols = st.columns(4)
status_cols[0].metric("Dataset", dataset_name)
status_cols[1].metric("Source", str(metadata.get("source", "dataset")))
status_cols[2].metric("File type", str(metadata.get("file_type", "data")))
status_cols[3].metric("Working shape", f"{len(working_df):,} x {len(working_df.columns):,}")

st.caption("Exports use the active working dataset by default. Select raw data only when you explicitly need the unchanged source copy.")
export_raw = st.checkbox("Export raw dataset instead of working dataset", value=False)
dataset_to_export = raw_df if export_raw else working_df
dataset_suffix = "raw_dataset" if export_raw else "working_dataset"

st.subheader("Dataset Export")
st.dataframe(dataset_to_export.head(20), use_container_width=True, hide_index=True)


def _download_buttons(df: pd.DataFrame, suffix: str, label_prefix: str, key_prefix: str) -> None:
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


_download_buttons(dataset_to_export, dataset_suffix, "Download dataset as", "dataset-export")

st.subheader("Transformation Log")
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


result_sources = [
    (
        "Generic Analytics",
        get_active_analytics_result("generic_analytics_result"),
        ["aggregated"],
    ),
    (
        "Sales / Retail Analytics",
        get_active_analytics_result("retail_analytics_result"),
        ["monthly_revenue", "product_performance", "country_performance", "customer_rfm", "segment_summary", "issue_summary"],
    ),
    (
        "Manufacturing Analytics",
        get_active_analytics_result("manufacturing_analytics_result"),
        ["machine_performance", "output_over_time", "downtime_over_time", "output_by_line", "output_by_shift", "issue_summary"],
    ),
    (
        "Logistics Analytics",
        get_active_analytics_result("logistics_analytics_result"),
        ["shipments_over_time", "lead_time_over_time", "status_summary", "carrier_performance", "destination_performance", "delayed_shipments", "issue_summary"],
    ),
    (
        "Finance Analytics",
        get_active_analytics_result("finance_analytics_result"),
        ["monthly_summary", "category_summary", "cost_center_summary", "largest_transactions", "issue_summary"],
    ),
]

st.subheader("Analytics Result Tables")
available_results = False
for result_label, result, table_names in result_sources:
    if result is None:
        continue
    if result_label == "Generic Analytics":
        tables = [("aggregated_result", result.aggregated)] if not result.aggregated.empty else []
    else:
        tables = _result_tables(result, table_names)
    if not tables:
        continue
    available_results = True
    with st.expander(result_label, expanded=False):
        for table_name, table_df in tables:
            st.markdown(f"**{table_name.replace('_', ' ').title()}**")
            st.dataframe(table_df, use_container_width=True, hide_index=True)
            _download_buttons(
                table_df,
                f"{result_label}_{table_name}",
                "Download table as",
                f"{result_label}-{table_name}".lower().replace(" ", "-").replace("/", "-"),
            )

if not available_results:
    st.info("No analytics result tables are available yet. Run Generic Analytics or a compatible domain analytics page first.")
