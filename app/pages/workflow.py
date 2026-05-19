from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.layout import configure_page, page_title
from app.services.dataset_workspace import get_active_dataset
from app.services.project_state import get_project_metadata, get_project_summary, project_summary_rows
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

summary_cols = st.columns(4)
summary_cols[0].metric("Done", status_counts["done"])
summary_cols[1].metric("Open", status_counts["open"])
summary_cols[2].metric("Optional", status_counts["optional"])
summary_cols[3].metric("Next", get_recommended_next_action(steps))

st.subheader("Project Summary")
st.dataframe(project_summary_rows(get_project_summary(active_dataset=active)), use_container_width=True, hide_index=True)

st.subheader("Recommended Workflow")
workflow_df = pd.DataFrame(
    [
        {
            "step": step["step"],
            "status": step["status"],
            "why it matters": step["explanation"],
            "recommended next action": step["recommended_next_action"],
        }
        for step in steps
    ]
)
st.dataframe(workflow_df, use_container_width=True, hide_index=True)

st.subheader("Open The Next Page")
for step in steps:
    with st.expander(f"{step['status']} - {step['step']}", expanded=step["status"] == "Open"):
        st.write(step["explanation"])
        st.caption(step["recommended_next_action"])
        try:
            st.page_link(step["page"], label=f"Open {step['step']}", icon=":material/arrow_forward:")
        except Exception:
            st.caption("Use the sidebar navigation to open this page.")
