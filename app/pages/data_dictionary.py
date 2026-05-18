from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.services.data_dictionary import generate_data_dictionary
from app.services.dataset_workspace import get_active_dataset, set_active_analytics_result
from app.services.export_service import (
    build_export_filename,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    dataframe_to_json_bytes,
)


configure_page("Data Dictionary")
page_title("Data Dictionary", "Column-level documentation generated from the active working dataframe.")

df = get_working_dataframe()
if df is None:
    st.stop()

active = get_active_dataset()
dataset_name = active.get("name", "dataset") if active else "dataset"
template_mappings = active.get("template_mappings", {}) if active else {}
dictionary_df = generate_data_dictionary(df, template_mappings=template_mappings)
set_active_analytics_result("data_dictionary_result", dictionary_df)

st.caption("This dictionary is generated from working_df, so user-triggered preparation changes such as column renames are reflected here.")

filters = st.columns(3)
type_options = ["All"] + sorted(dictionary_df["detected_data_type"].dropna().unique().tolist())
selected_type = filters[0].selectbox("Detected data type", type_options)
mapping_filter = filters[1].selectbox("Mapping status", ["All", "Mapped", "Unmapped"])
missing_only = filters[2].checkbox("Columns with missing values only")

filtered = dictionary_df.copy()
if selected_type != "All":
    filtered = filtered[filtered["detected_data_type"] == selected_type]
if mapping_filter == "Mapped":
    filtered = filtered[filtered["mapped_business_field"].astype(str).str.len() > 0]
elif mapping_filter == "Unmapped":
    filtered = filtered[filtered["mapped_business_field"].astype(str).str.len() == 0]
if missing_only:
    filtered = filtered[filtered["missing_value_count"] > 0]

st.subheader("Column Dictionary")
st.dataframe(filtered, use_container_width=True, hide_index=True)

download_cols = st.columns(3)
download_cols[0].download_button(
    "Download dictionary as CSV",
    data=dataframe_to_csv_bytes(filtered),
    file_name=build_export_filename(dataset_name, "data_dictionary", "csv"),
    mime="text/csv",
)
download_cols[1].download_button(
    "Download dictionary as Excel",
    data=dataframe_to_excel_bytes(filtered, sheet_name="Data_Dictionary"),
    file_name=build_export_filename(dataset_name, "data_dictionary", "xlsx"),
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
download_cols[2].download_button(
    "Download dictionary as JSON",
    data=dataframe_to_json_bytes(filtered),
    file_name=build_export_filename(dataset_name, "data_dictionary", "json"),
    mime="application/json",
)

with st.expander("How this dictionary is generated"):
    st.write(
        "The dictionary inspects the active working dataframe, not the raw upload. "
        "It includes missingness, examples, numeric/date summaries, saved template mappings, template relevance, and simple quality notes."
    )
