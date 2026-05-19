from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, page_title
from app.config import APP_DESCRIPTION
from app.services.data_loader import (
    LoadedDataset,
    get_excel_sheet_names,
    get_supported_file_types,
    load_sample_finance_transactions,
    load_sample_logistics_shipments,
    load_sample_manufacturing_operations,
    load_sample_retail_orders,
    load_uploaded_file,
)
from app.services.dataset_workspace import (
    add_or_activate_dataset,
    analyze_dataset_size,
    clear_all_datasets,
    get_active_dataset,
    get_active_dataset_summary,
    get_loaded_dataset_summary,
    initialize_workspace,
    list_datasets,
    remove_dataset,
    reset_active_working_df,
    set_active_dataset,
    sync_legacy_state,
)
from app.services.project_state import associate_dataset_with_active_project
from app.services.schema_detector import detect_retail_schema, detect_template_schema
from app.services.template_registry import implemented_domain_templates


configure_page("Data Upload")
page_title("Data Upload", APP_DESCRIPTION)
st.caption("Accepted formats: CSV, Excel workbooks .xlsx, JSON .json. Legacy .xls files are not supported.")
initialize_workspace()
feedback = st.session_state.pop("dataset_load_feedback", None)
if feedback:
    feedback_type, feedback_message = feedback
    if feedback_type == "success":
        st.success(feedback_message)
    else:
        st.info(feedback_message)


def _store_dataset(loaded: LoadedDataset) -> bool:
    df = loaded.dataframe
    dataset_name = loaded.metadata.get("file_name", "Dataset")
    dataset_id, created = add_or_activate_dataset(
        dataset_name,
        df,
        loaded.metadata,
        dataset_id=loaded.metadata.get("dataset_id"),
    )
    detections = {
        template.template_id: detect_template_schema(template.template_id, list(df.columns))
        for template in implemented_domain_templates()
    }
    st.session_state["template_schema_detections"] = detections
    st.session_state["retail_schema_detection"] = detections.get("sales_retail") or detect_retail_schema(list(df.columns))
    for template_id, detection in detections.items():
        st.session_state[f"{template_id}_schema_detection"] = detection
    suggested_template = loaded.metadata.get("suggested_template")
    if suggested_template:
        st.session_state["selected_template_id"] = suggested_template
    else:
        detected_template = next(
            (template_id for template_id, detection in detections.items() if detection.detected_template),
            None,
        )
        if detected_template:
            st.session_state["selected_template_id"] = detected_template
    sync_legacy_state()
    associate_dataset_with_active_project(dataset_id)
    st.session_state["last_loaded_dataset_id"] = dataset_id
    st.session_state["last_loaded_dataset_created"] = created
    return created


def _set_load_feedback(loaded: LoadedDataset, created: bool) -> None:
    verb = "Loaded" if created else "Activated existing"
    dataset_name = loaded.metadata.get("file_name", "dataset")
    message = (
        f"{verb} {dataset_name} "
        f"({loaded.metadata.get('file_type', 'data').upper()}) with "
        f"{loaded.metadata['rows']:,} rows and {loaded.metadata['columns']:,} columns."
    )
    size_profile = analyze_dataset_size(loaded.dataframe)
    if size_profile["is_large_dataset"]:
        message += " Large dataset detected; some profiling and charting operations may take longer."
    st.session_state["dataset_load_feedback"] = ("success" if created else "info", message)


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
                created = _store_dataset(loaded)
                _set_load_feedback(loaded, created)
                st.rerun()
            except Exception as exc:
                st.error(f"Could not load uploaded file: {exc}")
    else:
        st.info("Upload a CSV, XLSX, or JSON file to begin.")

with right:
    st.write("Bundled samples")
    if st.button("Load sample retail dataset", type="primary"):
        try:
            loaded = load_sample_retail_orders()
            loaded.metadata["suggested_template"] = "sales_retail"
            created = _store_dataset(loaded)
            _set_load_feedback(loaded, created)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not load sample dataset: {exc}")
    if st.button("Load sample manufacturing dataset"):
        try:
            loaded = load_sample_manufacturing_operations()
            created = _store_dataset(loaded)
            _set_load_feedback(loaded, created)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not load manufacturing sample: {exc}")
    if st.button("Load sample logistics dataset"):
        try:
            loaded = load_sample_logistics_shipments()
            created = _store_dataset(loaded)
            _set_load_feedback(loaded, created)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not load logistics sample: {exc}")
    if st.button("Load sample finance dataset"):
        try:
            loaded = load_sample_finance_transactions()
            created = _store_dataset(loaded)
            _set_load_feedback(loaded, created)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not load finance sample: {exc}")

workspace_datasets = list_datasets()
if workspace_datasets:
    st.divider()
    st.subheader("Dataset Workspace")
    st.caption(f"{len(workspace_datasets)} dataset{'s' if len(workspace_datasets) != 1 else ''} loaded. The app analyzes one active dataset at a time.")
    active = get_active_dataset()
    active_id = active["dataset_id"] if active else workspace_datasets[0]["dataset_id"]
    selected_dataset_id = st.selectbox(
        "Active dataset",
        [dataset["dataset_id"] for dataset in workspace_datasets],
        index=[dataset["dataset_id"] for dataset in workspace_datasets].index(active_id),
        format_func=lambda dataset_id: next(dataset["name"] for dataset in workspace_datasets if dataset["dataset_id"] == dataset_id),
    )
    if selected_dataset_id != active_id:
        set_active_dataset(selected_dataset_id)
        st.rerun()
    st.dataframe(get_loaded_dataset_summary(), use_container_width=True, hide_index=True)
    action_cols = st.columns(2)
    if action_cols[0].button("Reset active working data to raw"):
        reset_active_working_df()
        st.session_state["dataset_load_feedback"] = ("success", "Active working dataset reset to the original raw data.")
        st.rerun()
    if action_cols[1].button("Remove active dataset", disabled=len(workspace_datasets) == 0):
        remove_dataset(selected_dataset_id)
        st.session_state["dataset_load_feedback"] = ("success", "Dataset removed from the workspace.")
        st.rerun()
    clear_cols = st.columns([1, 1])
    confirm_clear_all = clear_cols[0].checkbox("Confirm clear all datasets")
    if clear_cols[1].button("Clear all datasets", disabled=not confirm_clear_all):
        clear_all_datasets()
        st.session_state["dataset_load_feedback"] = ("success", "All datasets cleared. Active project was kept.")
        st.rerun()

if "raw_df" in st.session_state:
    df = st.session_state["working_df"]
    active_detections = {
        template.template_id: detect_template_schema(template.template_id, list(df.columns))
        for template in implemented_domain_templates()
    }
    st.session_state["template_schema_detections"] = active_detections
    st.session_state["retail_schema_detection"] = active_detections.get("sales_retail")
    metadata = st.session_state.get("dataset_metadata", {})
    size_summary = get_active_dataset_summary()
    if size_summary.get("is_large_dataset"):
        st.warning(size_summary.get("large_dataset_message"))
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
        detections = st.session_state.get("template_schema_detections", {"sales_retail": detection})
        st.dataframe(
            [
                {
                    "template": template_id.replace("_", " ").title(),
                    "confidence": f"{template_detection.confidence_score:.1f}%",
                    "matched_fields": len(template_detection.matched_fields),
                    "missing_required": ", ".join(template_detection.missing_fields) or "None",
                }
                for template_id, template_detection in detections.items()
            ],
            use_container_width=True,
            hide_index=True,
        )
        if any(template_detection.detected_template for template_detection in detections.values()):
            st.success(f"Suggested template: {st.session_state.get('selected_template_id', 'generic')}")
        else:
            st.warning("No domain template was detected with enough confidence. Generic analytics and manual mapping can still be used.")
