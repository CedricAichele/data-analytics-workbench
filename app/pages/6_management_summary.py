from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import FINANCE_REQUIRED_FIELDS, LOGISTICS_REQUIRED_FIELDS, MANUFACTURING_REQUIRED_FIELDS, RETAIL_REQUIRED_FIELDS
from app.services.column_mapper import initialize_template_mapping, validate_template_mapping
from app.services.dataset_workspace import get_active_template_mapping
from app.services.finance_analytics import build_finance_analytics, clean_finance_transactions
from app.services.logistics_analytics import build_logistics_analytics, clean_logistics_shipments
from app.services.management_summary import (
    generate_finance_management_summary,
    generate_generic_data_summary,
    generate_logistics_management_summary,
    generate_manufacturing_management_summary,
    generate_retail_management_summary,
)
from app.services.manufacturing_analytics import build_manufacturing_analytics, clean_manufacturing_operations
from app.services.quality_score import calculate_quality_score
from app.services.retail_analytics import build_retail_analytics, clean_retail_orders
from app.services.schema_detector import detect_template_schema


configure_page("Management Summary")
page_title("Management Summary", "Deterministic narrative generated from the active dataset context.")

df = get_working_dataframe()
if df is None:
    st.stop()


def _mapping_for(template_id: str):
    mapping = get_active_template_mapping(template_id)
    detection = detect_template_schema(template_id, list(df.columns))
    if not mapping and not detection.requires_manual_mapping:
        mapping = initialize_template_mapping(template_id, list(df.columns), detection)
    if mapping and validate_template_mapping(template_id, mapping, list(df.columns)).is_valid:
        return mapping
    return None


summary_options: dict[str, tuple[str, object, dict[str, float] | None]] = {}

sales_mapping = _mapping_for("sales_retail")
if sales_mapping:
    try:
        clean_result = clean_retail_orders(df, sales_mapping)
        analytics = build_retail_analytics(clean_result)
        summary_options["Sales / Retail"] = (generate_retail_management_summary(analytics), analytics.issue_summary, analytics.metrics)
    except Exception:
        pass

manufacturing_mapping = _mapping_for("manufacturing")
if manufacturing_mapping:
    try:
        clean_result = clean_manufacturing_operations(df, manufacturing_mapping)
        analytics = build_manufacturing_analytics(clean_result)
        summary_options["Manufacturing"] = (generate_manufacturing_management_summary(analytics), analytics.issue_summary, analytics.metrics)
    except Exception:
        pass

logistics_mapping = _mapping_for("logistics")
if logistics_mapping:
    try:
        clean_result = clean_logistics_shipments(df, logistics_mapping)
        analytics = build_logistics_analytics(clean_result)
        summary_options["Logistics"] = (generate_logistics_management_summary(analytics), analytics.issue_summary, analytics.metrics)
    except Exception:
        pass

finance_mapping = _mapping_for("finance")
if finance_mapping:
    try:
        clean_result = clean_finance_transactions(df, finance_mapping)
        analytics = build_finance_analytics(clean_result)
        if analytics.metrics["transaction_count"] > 0:
            summary_options["Finance"] = (generate_finance_management_summary(analytics), analytics.issue_summary, analytics.metrics)
    except Exception:
        pass

if not summary_options:
    quality = calculate_quality_score(df)
    generic_result = st.session_state.get("generic_analytics_result")
    summary = generate_generic_data_summary(df, quality, generic_result)
    st.text_area("Summary", value=summary, height=330)
    st.subheader("Generic Quality Score")
    st.metric("Score", f"{quality.overall_score:.1f}/100")
    st.dataframe(
        [{"dimension": key.replace("_", " ").title(), "score": value} for key, value in quality.sub_scores.items()],
        use_container_width=True,
        hide_index=True,
    )
else:
    selected_summary = st.selectbox("Summary context", list(summary_options))
    summary, issue_summary, metrics = summary_options[selected_summary]
    st.text_area("Summary", value=summary, height=330)
    st.subheader("Supporting Metrics")
    st.dataframe(
        [{"metric": key, "value": value} for key, value in (metrics or {}).items()],
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Issue summary"):
        st.dataframe(issue_summary, use_container_width=True, hide_index=True)
