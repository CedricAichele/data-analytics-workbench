from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, page_title
from app.services.template_registry import get_template


configure_page("Finance Analytics")
template = get_template("finance")
page_title("Finance Analytics", "Planned revenue, cost, margin, and budget variance analytics template.")

st.info("This template is visible in the workbench architecture but is not implemented yet.")
st.write(template.purpose)
st.write(template.when_to_use)
st.subheader("Required Fields")
st.dataframe([{"field": field} for field in template.required_fields], use_container_width=True, hide_index=True)
st.subheader("Optional Fields")
st.dataframe([{"field": field} for field in template.optional_fields], use_container_width=True, hide_index=True)
st.warning("Finance rows are not interpreted unless a type, category, or explicit sign convention is available.")
st.caption(template.notes)
st.page_link("pages/6_generic_analytics.py", label="Use Generic Analytics for finance datasets today")
