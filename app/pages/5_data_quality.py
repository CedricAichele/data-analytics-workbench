from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, get_working_dataframe, page_title
from app.config import MANUFACTURING_REQUIRED_FIELDS, RETAIL_REQUIRED_FIELDS
from app.services.quality_score import calculate_quality_score
from app.services.template_registry import implemented_domain_templates


configure_page("Data Quality")
page_title("Data Quality", "Explainable quality checks for generic datasets and mapped templates.")

df = get_working_dataframe()
if df is None:
    st.stop()

generic_report = calculate_quality_score(df)
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
    mapping = st.session_state.get("column_mapping") or mapping
    required_fields = RETAIL_REQUIRED_FIELDS
    date_fields = ["order_date"]
    numeric_fields = ["quantity", "unit_price"]
elif selected_template_id == "manufacturing":
    mapping = st.session_state.get("manufacturing_mapping") or mapping
    required_fields = MANUFACTURING_REQUIRED_FIELDS
    date_fields = ["timestamp"]
    numeric_fields = ["actual_output", "scrap_count", "downtime_minutes"]
else:
    required_fields = []
    date_fields = []
    numeric_fields = []

if not mapping:
    st.info("Save a mapping on the Column Mapping page to include template completeness in the quality score.")
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
