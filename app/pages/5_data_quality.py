from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import (
    FINANCE_REQUIRED_FIELDS,
    LOGISTICS_REQUIRED_FIELDS,
    MANUFACTURING_REQUIRED_FIELDS,
    RETAIL_REQUIRED_FIELDS,
)
from app.services.dataset_workspace import get_active_template_mapping
from app.services.dataset_workspace import set_active_analytics_result
from app.services.export_service import dataframe_to_csv_bytes, dataframe_to_excel_bytes
from app.services.column_mapper import initialize_template_mapping
from app.services.quality_score import calculate_quality_score
from app.services.quality_rules import run_template_quality_rules, summarize_rule_severity
from app.services.schema_detector import detect_template_schema
from app.services.template_registry import implemented_domain_templates


configure_page("Data Quality")
page_title("Data Quality", "Explainable quality checks for generic datasets and mapped templates.")

df = get_working_dataframe()
if df is None:
    st.stop()

generic_report = calculate_quality_score(df)
set_active_analytics_result("generic_quality_report", generic_report)
st.subheader("Generic Quality Score")
cols = st.columns(3)
cols[0].metric("Overall score", f"{generic_report.overall_score:.1f}/100")
cols[1].metric("Rows", f"{len(df):,}")
cols[2].metric("Columns", f"{len(df.columns):,}")
st.progress(generic_report.overall_score / 100)
st.dataframe(
    [{"dimension": key.replace("_", " ").title(), "score": value} for key, value in generic_report.sub_scores.items()],
    use_container_width=True,
    hide_index=True,
)

with st.expander("Generic quality explanations and fixes"):
    st.write("Explanations")
    for explanation in generic_report.explanations:
        st.write(f"- {explanation}")
    st.write("Recommended fixes")
    for fix in generic_report.recommended_fixes:
        st.write(f"- {fix}")

st.subheader("Template Completeness Check")
templates = implemented_domain_templates()
template_ids = [template.template_id for template in templates]
template_by_id = {template.template_id: template for template in templates}
default_template_id = st.session_state.get("selected_template_id", "sales_retail")
if default_template_id not in template_ids:
    default_template_id = "sales_retail"
selected_template_id = st.selectbox(
    "Mapped template",
    template_ids,
    index=template_ids.index(default_template_id),
    format_func=lambda template_id: template_by_id[template_id].name,
)

template_mappings = st.session_state.get("template_mappings", {})
mapping = template_mappings.get(selected_template_id)
if selected_template_id == "sales_retail":
    mapping = get_active_template_mapping("sales_retail") or st.session_state.get("column_mapping") or mapping
    required_fields = RETAIL_REQUIRED_FIELDS
    date_fields = ["order_date"]
    numeric_fields = ["quantity", "unit_price"]
elif selected_template_id == "manufacturing":
    mapping = get_active_template_mapping("manufacturing") or st.session_state.get("manufacturing_mapping") or mapping
    required_fields = MANUFACTURING_REQUIRED_FIELDS
    date_fields = ["timestamp"]
    numeric_fields = ["actual_output", "scrap_count", "downtime_minutes"]
elif selected_template_id == "logistics":
    mapping = get_active_template_mapping("logistics") or st.session_state.get("logistics_mapping") or mapping
    required_fields = LOGISTICS_REQUIRED_FIELDS
    date_fields = ["order_date", "delivery_date", "planned_delivery_date"]
    numeric_fields = ["shipping_cost"]
elif selected_template_id == "finance":
    mapping = get_active_template_mapping("finance") or st.session_state.get("finance_mapping") or mapping
    required_fields = FINANCE_REQUIRED_FIELDS
    date_fields = ["date"]
    numeric_fields = ["amount", "budget", "actual"]
else:
    required_fields = []
    date_fields = []
    numeric_fields = []

if not mapping:
    detection = detect_template_schema(selected_template_id, list(df.columns))
    if not detection.requires_manual_mapping:
        mapping = initialize_template_mapping(selected_template_id, list(df.columns), detection)
        st.info("Using detected required fields for template checks. Save a manual mapping if you need to adjust these matches.")
    else:
        st.info("Save a mapping on the Column Mapping page to include template completeness and template-specific rules.")
        mapping = None

if not mapping:
    set_active_analytics_result("quality_rules_result", None)
    st.subheader("Template-specific Quality Rules")
    st.info("Template-specific rules run after the active dataset has a detected or saved mapping for the selected template.")
else:
    template_report = calculate_quality_score(
        df,
        mapping=mapping,
        required_fields=required_fields,
        date_fields=date_fields,
        numeric_fields=numeric_fields,
    )
    st.metric("Template-aware score", f"{template_report.overall_score:.1f}/100")
    st.progress(template_report.overall_score / 100)
    st.dataframe(
        [{"dimension": key.replace("_", " ").title(), "score": value} for key, value in template_report.sub_scores.items()],
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Template quality explanations and fixes"):
        st.write("Explanations")
        for explanation in template_report.explanations:
            st.write(f"- {explanation}")
        st.write("Recommended fixes")
        for fix in template_report.recommended_fixes:
            st.write(f"- {fix}")

    st.subheader("Template-specific Quality Rules")
    rule_results = run_template_quality_rules(df, selected_template_id, mapping)
    set_active_analytics_result("quality_rules_result", rule_results)
    severity_counts = summarize_rule_severity(rule_results)
    severity_cols = st.columns(3)
    severity_cols[0].metric("Critical rules", severity_counts["critical"])
    severity_cols[1].metric("Warning rules", severity_counts["warning"])
    severity_cols[2].metric("Info rules", severity_counts["info"])

    if rule_results.empty:
        st.success("No template-specific rules were available or no rule issues were found.")
    else:
        st.dataframe(rule_results, use_container_width=True, hide_index=True)
        with st.expander("Recommended fixes from rule checks"):
            for fix in rule_results["recommended_fix"].dropna().drop_duplicates().tolist():
                st.write(f"- {fix}")
        export_cols = st.columns(2)
        export_cols[0].download_button(
            "Download rule results as CSV",
            data=dataframe_to_csv_bytes(rule_results),
            file_name=f"{selected_template_id}_quality_rules.csv",
            mime="text/csv",
        )
        export_cols[1].download_button(
            "Download rule results as Excel",
            data=dataframe_to_excel_bytes(rule_results, sheet_name="Quality_Rules"),
            file_name=f"{selected_template_id}_quality_rules.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
