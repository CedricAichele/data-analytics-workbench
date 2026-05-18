from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.services.transformations import (
    change_column_type,
    create_revenue_column,
    create_transformation_log_entry,
    drop_columns,
    drop_missing_rows,
    fill_missing_values,
    filter_rows,
    parse_datetime_column,
    remove_duplicate_rows,
    rename_column,
)


configure_page("Data Preparation")
page_title("Data Preparation", "Apply controlled transformations to a working copy of the uploaded dataset.")

working_df = get_working_dataframe()
if working_df is None:
    st.stop()

TYPE_LABELS = {
    "String": "string",
    "Integer": "integer",
    "Float": "float",
    "Datetime": "datetime",
    "Boolean": "boolean",
}
MISSING_STRATEGY_LABELS = {
    "Fill numeric missing values with 0": "fill_numeric_zero",
    "Fill numeric missing values with median": "fill_numeric_median",
    "Fill text missing values with Unknown": "fill_text_unknown",
    "Drop rows with missing values": "drop_rows",
}
FILTER_OPERATOR_LABELS = {
    "Equals": "equals",
    "Does not equal": "not_equals",
    "Contains text": "contains",
    "Greater than": "greater_than",
    "Greater than or equal": "greater_or_equal",
    "Less than": "less_than",
    "Less than or equal": "less_or_equal",
}


def _show_feedback() -> None:
    feedback = st.session_state.pop("prep_feedback", None)
    if not feedback:
        return
    level = feedback.get("level", "success")
    message = feedback.get("message", "")
    if level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)
    else:
        st.success(message)


def _save_working_df(
    transformed: pd.DataFrame,
    *,
    action: str,
    details: str,
    level: str = "success",
    clear_mapping: bool = False,
) -> None:
    st.session_state["working_df"] = transformed
    st.session_state.setdefault("transformation_log", []).append(create_transformation_log_entry(action, details))
    st.session_state.pop("retail_analytics_result", None)
    st.session_state.pop("retail_clean_result", None)
    st.session_state.pop("manufacturing_analytics_result", None)
    st.session_state.pop("manufacturing_clean_result", None)
    st.session_state.pop("retail_schema_detection", None)
    st.session_state.pop("sales_retail_schema_detection", None)
    st.session_state.pop("manufacturing_schema_detection", None)
    st.session_state.pop("template_schema_detections", None)
    if clear_mapping:
        st.session_state.pop("column_mapping", None)
        st.session_state.pop("manufacturing_mapping", None)
        st.session_state["template_mappings"] = {}
    st.session_state["prep_feedback"] = {"level": level, "message": details}
    st.rerun()


def _run_transformation(
    transform: Callable[[], pd.DataFrame],
    *,
    action: str,
    details: str,
    level: str = "success",
    clear_mapping: bool = False,
) -> None:
    try:
        transformed = transform()
        _save_working_df(transformed, action=action, details=details, level=level, clear_mapping=clear_mapping)
    except Exception as exc:
        st.error(f"{action} failed: {exc}")


_show_feedback()

raw_df = st.session_state["raw_df"]
working_df = st.session_state["working_df"]
log = st.session_state.setdefault("transformation_log", [])
columns = list(working_df.columns)

st.subheader("Dataset Status")
status_cols = st.columns(4)
status_cols[0].metric("Raw data loaded", "Yes" if raw_df is not None else "No")
status_cols[1].metric("Working rows", f"{len(working_df):,}")
status_cols[2].metric("Working columns", f"{len(working_df.columns):,}")
status_cols[3].metric("Transformations", f"{len(log):,}")
if log:
    st.caption(f"Last transformation: {log[-1]}")
else:
    st.caption("No transformations have been applied. The working dataset currently matches the raw upload.")

st.subheader("Preview Working Data")
st.dataframe(working_df.head(30), use_container_width=True)

if not columns:
    st.warning("The working dataset has no columns.")
    st.stop()

st.subheader("Column Operations")
rename_col, drop_col = st.columns(2)
with rename_col:
    selected_column = st.selectbox("Column to rename", columns, key="prep_rename_column")
    new_name = st.text_input("New column name", value=selected_column, key="prep_new_column_name")
    if st.button("Rename column", key="prep_rename_button"):
        _run_transformation(
            lambda: rename_column(working_df, selected_column, new_name),
            action="Rename column",
            details=f"{selected_column} -> {new_name.strip()}",
            clear_mapping=True,
        )

with drop_col:
    selected_drop_columns = st.multiselect("Columns to drop", columns, key="prep_drop_columns")
    if st.button("Drop selected columns", key="prep_drop_button"):
        _run_transformation(
            lambda: drop_columns(working_df, selected_drop_columns),
            action="Drop columns",
            details=", ".join(selected_drop_columns),
            clear_mapping=True,
        )

st.subheader("Type Conversion")
type_col, target_col = st.columns(2)
conversion_column = type_col.selectbox("Column", columns, key="prep_type_column")
target_type_label = target_col.selectbox("Target type", list(TYPE_LABELS), key="prep_target_type")
target_type = TYPE_LABELS[target_type_label]
if st.button("Apply type conversion", key="prep_type_button"):
    before_missing = int(working_df[conversion_column].isna().sum())
    try:
        converted = change_column_type(working_df, conversion_column, target_type)
        after_missing = int(converted[conversion_column].isna().sum())
        created_missing = max(after_missing - before_missing, 0)
        level = "warning" if created_missing else "success"
        details = f"Converted {conversion_column} to {target_type}; missing values changed from {before_missing} to {after_missing}."
        _save_working_df(converted, action="Change column type", details=details, level=level)
    except Exception as exc:
        st.error(f"Type conversion failed: {exc}")

st.subheader("Date Parsing")
date_column = st.selectbox("Column to parse as datetime", columns, key="prep_date_column")
if st.button("Parse datetime column", key="prep_date_button"):
    before_missing = int(working_df[date_column].isna().sum())
    try:
        parsed = parse_datetime_column(working_df, date_column)
        after_missing = int(parsed[date_column].isna().sum())
        failed_parses = max(after_missing - before_missing, 0)
        level = "warning" if failed_parses else "success"
        details = f"Parsed {date_column} as datetime; failed parses: {failed_parses}."
        _save_working_df(parsed, action="Parse datetime column", details=details, level=level)
    except Exception as exc:
        st.error(f"Date parsing failed: {exc}")

st.subheader("Missing Values")
missing_col, strategy_col = st.columns(2)
missing_column = missing_col.selectbox("Column with missing values", columns, key="prep_missing_column")
strategy_label = strategy_col.selectbox("Strategy", list(MISSING_STRATEGY_LABELS), key="prep_missing_strategy")
strategy = MISSING_STRATEGY_LABELS[strategy_label]
missing_before = int(working_df[missing_column].isna().sum())
st.caption(f"Current missing values in {missing_column}: {missing_before:,}")
if st.button("Apply missing value strategy", key="prep_missing_button"):
    try:
        if strategy == "drop_rows":
            transformed = drop_missing_rows(working_df, missing_column)
        else:
            transformed = fill_missing_values(working_df, missing_column, strategy)
        missing_after = int(transformed[missing_column].isna().sum()) if missing_column in transformed.columns else 0
        details = f"Applied {strategy} to {missing_column}; missing values changed from {missing_before} to {missing_after}."
        _save_working_df(transformed, action="Handle missing values", details=details)
    except Exception as exc:
        st.error(f"Missing value handling failed: {exc}")

st.subheader("Duplicates")
duplicate_count = int(working_df.duplicated().sum())
st.metric("Duplicate rows", f"{duplicate_count:,}")
if st.button("Remove duplicate rows", disabled=duplicate_count == 0, key="prep_duplicates_button"):
    before_rows = len(working_df)
    transformed = remove_duplicate_rows(working_df)
    after_rows = len(transformed)
    _save_working_df(
        transformed,
        action="Remove duplicate rows",
        details=f"Removed {before_rows - after_rows:,} duplicate rows; rows changed from {before_rows:,} to {after_rows:,}.",
    )

st.subheader("Row Filtering")
filter_col, op_col, value_col = st.columns([1, 1, 1])
filter_column = filter_col.selectbox("Filter column", columns, key="prep_filter_column")
operator_label = op_col.selectbox("Operator", list(FILTER_OPERATOR_LABELS), key="prep_filter_operator")
operator = FILTER_OPERATOR_LABELS[operator_label]
filter_value = value_col.text_input("Comparison value", key="prep_filter_value")
if st.button("Apply row filter", key="prep_filter_button"):
    before_rows = len(working_df)
    try:
        transformed = filter_rows(working_df, filter_column, operator, filter_value)
        after_rows = len(transformed)
        _save_working_df(
            transformed,
            action="Filter rows",
            details=f"Filtered {filter_column} {operator} {filter_value}; rows changed from {before_rows:,} to {after_rows:,}.",
        )
    except Exception as exc:
        st.error(f"Row filtering failed: {exc}")

st.subheader("Calculated Column")
calc_col1, calc_col2, calc_col3 = st.columns(3)
quantity_column = calc_col1.selectbox("Quantity column", columns, key="prep_quantity_column")
unit_price_column = calc_col2.selectbox("Unit price column", columns, key="prep_unit_price_column")
revenue_column = calc_col3.text_input("Output column name", value="revenue", key="prep_revenue_column")
if st.button("Create revenue column", key="prep_revenue_button"):
    _run_transformation(
        lambda: create_revenue_column(working_df, quantity_column, unit_price_column, revenue_column),
        action="Create revenue column",
        details=f"{revenue_column.strip() or 'revenue'} = {quantity_column} * {unit_price_column}",
    )

st.subheader("Transformation Log")
if log:
    with st.expander("View applied transformations", expanded=len(log) <= 8):
        for index, entry in enumerate(log, start=1):
            st.write(f"{index}. {entry}")
else:
    st.info("No transformations have been applied yet.")

st.subheader("Reset and Export")
reset_col, export_col = st.columns(2)
with reset_col:
    if st.button("Reset working data to original upload", key="prep_reset_button"):
        st.session_state["working_df"] = st.session_state["raw_df"].copy()
        st.session_state["transformation_log"] = []
        st.session_state.pop("retail_analytics_result", None)
        st.session_state.pop("retail_clean_result", None)
        st.session_state.pop("retail_schema_detection", None)
        st.session_state.pop("manufacturing_analytics_result", None)
        st.session_state.pop("manufacturing_clean_result", None)
        st.session_state.pop("sales_retail_schema_detection", None)
        st.session_state.pop("manufacturing_schema_detection", None)
        st.session_state.pop("template_schema_detections", None)
        st.session_state.pop("column_mapping", None)
        st.session_state.pop("manufacturing_mapping", None)
        st.session_state["template_mappings"] = {}
        st.session_state["prep_feedback"] = {"level": "success", "message": "Working data reset to the original upload."}
        st.rerun()

with export_col:
    csv_bytes = working_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download working data as CSV",
        data=csv_bytes,
        file_name="prepared_data.csv",
        mime="text/csv",
        key="prep_download_button",
    )
