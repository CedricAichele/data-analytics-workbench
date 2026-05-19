from __future__ import annotations

import streamlit as st

from app.components.layout import configure_page, page_title, render_process_steps
from app.services.dataset_workspace import get_active_dataset
from app.services.project_state import compact_project_summary_rows, get_project_metadata, get_project_summary
from app.services.workflow import build_workflow_steps, calculate_workflow_status, get_recommended_next_action


configure_page("Workflow")
page_title("Workflow", "A guided checklist for turning raw data into useful exports.")

metadata = get_project_metadata()
active = get_active_dataset()
analytics_results = (active or {}).get("analytics_results", {})
steps = build_workflow_steps(metadata, active, analytics_results)
status_counts = calculate_workflow_status(metadata, active, analytics_results)

st.info(
    "This checklist is guidance, not a rigid wizard. You can still open any page directly from the sidebar."
)

summary_cols = st.columns(3)
summary_cols[0].metric("Done", status_counts["done"])
summary_cols[1].metric("Open", status_counts["open"])
summary_cols[2].metric("Optional", status_counts["optional"])
st.info(f"Recommended next action: {get_recommended_next_action(steps)}")

st.subheader("Project Summary")
st.dataframe(compact_project_summary_rows(get_project_summary(active_dataset=active)), use_container_width=True, hide_index=True)

st.subheader("Recommended Workflow")
render_process_steps(steps)
