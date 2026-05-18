from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, page_title, require_dataframe
from app.services.column_mapper import validate_retail_mapping
from app.services.management_summary import generate_llm_summary_placeholder, generate_retail_management_summary
from app.services.retail_analytics import build_retail_analytics, clean_retail_orders


configure_page("Management Summary")
page_title("Management Summary", "Deterministic narrative generated from calculated retail metrics.")

if not require_dataframe():
    st.stop()

analytics = st.session_state.get("retail_analytics_result")
if analytics is None:
    df = st.session_state["working_df"]
    mapping = st.session_state.get("column_mapping")
    if mapping and validate_retail_mapping(mapping, list(df.columns)).is_valid:
        try:
            clean_result = clean_retail_orders(df, mapping)
            analytics = build_retail_analytics(clean_result)
            st.session_state["retail_clean_result"] = clean_result
            st.session_state["retail_analytics_result"] = analytics
        except Exception as exc:
            st.error(f"Summary could not be generated: {exc}")
            st.stop()
    else:
        st.warning("Run Retail Analytics first or save a valid retail mapping.")
        st.stop()

summary = generate_retail_management_summary(analytics)
st.text_area("Summary", value=summary, height=260)

with st.expander("LLM summary extension placeholder"):
    st.write(generate_llm_summary_placeholder(enabled=False))
    st.caption("The MVP does not call external LLM APIs or require API keys.")

st.subheader("Supporting Metrics")
st.dataframe(
    [{"metric": key, "value": value} for key, value in analytics.metrics.items()],
    use_container_width=True,
    hide_index=True,
)
