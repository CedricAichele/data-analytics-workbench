from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, page_title
from app.services.template_registry import list_templates


configure_page("Template Selection")
page_title("Template Selection", "Choose between generic exploration and schema-aware KPI templates.")

st.write(
    "Any supported tabular dataset can use the generic workflow. Domain templates require schema detection "
    "or manual mapping because business KPIs need domain context."
)
st.info("Analytics Hub is the preferred entry point for template recommendations and compatibility diagnostics.")

for template in list_templates(include_generic=True):
    with st.container(border=True):
        cols = st.columns([2, 1])
        with cols[0]:
            st.subheader(template.name)
            st.write(template.purpose)
            st.caption(template.when_to_use)
        with cols[1]:
            st.metric("Status", template.status)
            st.write("Mapping required: " + ("Yes" if template.mapping_required else "No"))
            st.write("Sample dataset: " + ("Yes" if template.sample_dataset else "No"))
        if template.required_fields:
            st.write("Required fields")
            st.dataframe([{"field": field} for field in template.required_fields], use_container_width=True, hide_index=True)
        if template.optional_fields:
            with st.expander("Optional fields and notes"):
                st.dataframe([{"field": field} for field in template.optional_fields], use_container_width=True, hide_index=True)
                st.write(template.notes)
        else:
            st.caption(template.notes)

        if template.template_id == "generic":
            st.page_link("pages/6_generic_analytics.py", label="Open Generic Analytics", icon=":material/query_stats:")
        else:
            if st.button(f"Select {template.name}", key=f"select_{template.template_id}"):
                st.session_state["selected_template_id"] = template.template_id
                st.success(f"{template.name} selected. Continue to Column Mapping.")
            st.page_link("pages/4_column_mapping.py", label="Open Column Mapping", icon=":material/link:")
