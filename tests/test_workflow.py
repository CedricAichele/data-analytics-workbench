import pandas as pd

from app.services.workflow import build_workflow_steps, calculate_workflow_status, get_recommended_next_action


def test_workflow_with_no_project_starts_with_project_creation():
    steps = build_workflow_steps({}, None, {})

    assert steps[0]["step"] == "Project Setup"
    assert steps[0]["status"] == "Open"
    assert get_recommended_next_action(steps) == "Open Project Setup and save the project details."


def test_workflow_with_project_but_no_dataset_marks_dataset_open():
    steps = build_workflow_steps({"project_name": "Sales Review"}, None, {})

    assert steps[0]["status"] == "Done"
    assert steps[1]["status"] == "Open"
    assert calculate_workflow_status({"project_name": "Sales Review"}, None, {})["open"] >= 1


def test_workflow_with_dataset_and_outputs_marks_available_steps_done():
    active_dataset = {
        "working_df": pd.DataFrame({"a": [1]}),
        "transformation_log": ["Rename column"],
        "template_mappings": {"sales_retail": {"order_id": "a"}},
        "analytics_results": {
            "generic_quality_report": object(),
            "data_dictionary_result": pd.DataFrame({"column_name": ["a"]}),
            "retail_analytics_result": object(),
        },
    }
    metadata = {"project_name": "Sales Review", "suggested_template": "Sales / Retail"}

    steps = build_workflow_steps(metadata, active_dataset)
    statuses = {step["step"]: step["status"] for step in steps}

    assert statuses["Project Setup"] == "Done"
    assert statuses["Upload Data"] == "Done"
    assert statuses["Check Quality"] == "Done"
    assert statuses["Prepare Data"] == "Done"
    assert statuses["Generate Data Dictionary"] == "Done"
    assert statuses["Column Mapping"] == "Done"
    assert statuses["Run Analytics"] == "Done"
