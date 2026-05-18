from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, page_title
from app.config import APP_DESCRIPTION
from app.services.data_loader import (
    LoadedDataset,
    get_excel_sheet_names,
    get_supported_file_types,
    load_sample_retail_orders,
    load_uploaded_file,
)
from app.services.schema_detector import detect_retail_schema


configure_page("Data Upload")
page_title("Data Upload", APP_DESCRIPTION)
st.caption("Accepted formats: CSV, Excel .xlsx, JSON .json")


def _store_dataset(loaded: LoadedDataset) -> None:
    df = loaded.dataframe
    st.session_state["raw_df"] = df
    st.session_state["working_df"] = df.copy()
    st.session_state["dataset_name"] = loaded.metadata.get("file_name", "Dataset")
    st.session_state["dataset_metadata"] = loaded.metadata
    detection = detect_retail_schema(list(df.columns))
    st.session_state["retail_schema_detection"] = detection
    st.session_state["transformation_log"] = []
    st.session_state.pop("column_mapping", None)
    st.session_state.pop("retail_analytics_result", None)
    st.session_state.pop("retail_clean_result", None)


left, right = st.columns([1, 1])
with left:
    uploaded = st.file_uploader("Upload dataset", type=get_supported_file_types())
    if uploaded is not None:
        suffix = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
        sheet_name = None
        if suffix == "xlsx":
            try:
                sheet_names = get_excel_sheet_names(uploaded)
                if len(sheet_names) > 1:
                    sheet_name = st.selectbox("Excel sheet", sheet_names)
                elif sheet_names:
                    sheet_name = sheet_names[0]
                    st.caption(f"Excel sheet: {sheet_name}")
            except Exception as exc:
                st.error(f"Could not read Excel workbook sheets: {exc}")

        should_load = st.button("Load uploaded dataset", type="primary")
        if should_load:
            try:
                loaded = load_uploaded_file(uploaded, sheet_name=sheet_name)
                _store_dataset(loaded)
                st.success(
                    f"Loaded {loaded.metadata['file_name']} "
                    f"({loaded.metadata['file_type'].upper()}) with "
                    f"{loaded.metadata['rows']:,} rows and {loaded.metadata['columns']:,} columns."
                )
            except Exception as exc:
                st.error(f"Could not load uploaded file: {exc}")
    else:
        st.info("Upload a CSV, XLSX, or JSON file to begin.")

with right:
    st.write("Bundled sample")
    if st.button("Load sample retail dataset", type="primary"):
        try:
            loaded = load_sample_retail_orders()
            _store_dataset(loaded)
            st.success(
                f"Loaded sample dataset with {loaded.metadata['rows']:,} rows "
                f"and {loaded.metadata['columns']:,} columns."
            )
        except Exception as exc:
            st.error(f"Could not load sample dataset: {exc}")

if "raw_df" in st.session_state:
    df = st.session_state["working_df"]
    st.divider()
    metadata = st.session_state.get("dataset_metadata", {})
    if metadata:
        st.subheader("Loaded Dataset Metadata")
        st.dataframe(
            [{"field": key, "value": value} for key, value in metadata.items()],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Working Data Preview")
    st.caption(
        f"{st.session_state.get('dataset_name', 'Dataset')} | "
        f"raw rows: {len(st.session_state['raw_df']):,} | "
        f"working rows: {len(df):,} | working columns: {len(df.columns):,}"
    )
    st.dataframe(df.head(30), use_container_width=True)

    detection = st.session_state.get("retail_schema_detection")
    if detection:
        st.subheader("Initial Schema Detection")
        st.metric("Retail template confidence", f"{detection.confidence_score:.1f}%")
        if detection.detected_template:
            st.success(f"Detected template: {detection.detected_template}")
        else:
            st.warning("No domain template was detected with enough confidence. Manual mapping can still be used.")
        cols = st.columns(2)
        with cols[0]:
            st.write("Matched fields")
            st.dataframe(
                [{"field": field, "column": column} for field, column in detection.matched_fields.items()],
                use_container_width=True,
                hide_index=True,
            )
        with cols[1]:
            st.write("Missing required fields")
            if detection.missing_fields:
                st.dataframe(
                    [{"field": field} for field in detection.missing_fields],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("All required retail fields were matched.")
