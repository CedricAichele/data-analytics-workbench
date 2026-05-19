import pandas as pd

from app.services.project_state import (
    add_or_activate_project,
    associate_dataset_with_active_project,
    get_active_project,
    get_project_metadata,
    get_project_summary,
    has_project,
    initialize_project_state,
    list_projects,
    set_active_project,
    start_new_project_draft,
    update_project_metadata,
)


def test_project_metadata_creation_and_update():
    state = {}
    initialize_project_state(state)

    assert has_project(state) is False

    metadata = update_project_metadata(
        state=state,
        project_name="Monthly Sales Review",
        analysis_goal="Understand margin and product performance",
        selected_workflow="Domain KPI Analysis",
        suggested_template="Sales / Retail",
        desired_outputs=["KPI Analysis", "BI-ready Export Package"],
    )

    assert metadata["project_name"] == "Monthly Sales Review"
    assert metadata["suggested_template"] == "Sales / Retail"
    assert has_project(state) is True
    assert get_project_metadata(state)["analysis_goal"] == "Understand margin and product performance"


def test_project_summary_uses_active_dataset_and_results():
    state = {}
    update_project_metadata(state=state, project_name="Ops Review", analysis_goal="Check downtime")
    active_dataset = {
        "name": "Manufacturing sample",
        "working_df": pd.DataFrame({"machine": ["M1", "M2"], "output": [10, 20]}),
        "transformation_log": ["Rename column: old -> new"],
        "template_mappings": {"manufacturing": {"machine_id": "machine"}},
        "analytics_results": {
            "data_dictionary_result": pd.DataFrame({"column_name": ["machine"]}),
            "manufacturing_analytics_result": object(),
        },
    }

    summary = get_project_summary(active_dataset=active_dataset, state=state)

    assert summary["Project name"] == "Ops Review"
    assert summary["Active dataset"] == "Manufacturing sample"
    assert summary["Active dataset rows"] == 2
    assert summary["Transformations"] == 1
    assert summary["Data Dictionary"] == "Available"
    assert summary["Analytics results"] == "Manufacturing"


def test_project_workspace_supports_multiple_projects_and_active_switching():
    state = {}

    first_id, first_created = add_or_activate_project(
        {
            "project_name": "Sales Review",
            "project_description": "Review sales",
            "analysis_goal": "Find revenue drivers",
            "selected_workflow": "Domain KPI Analysis",
            "suggested_template": "Sales / Retail",
        },
        state=state,
    )
    second_id, second_created = add_or_activate_project(
        {
            "project_name": "Operations Review",
            "project_description": "Review production",
            "analysis_goal": "Find downtime drivers",
            "selected_workflow": "BI-ready Data Preparation",
            "suggested_template": "Manufacturing",
        },
        state=state,
    )

    assert first_created is True
    assert second_created is True
    assert len(list_projects(state)) == 2
    assert get_active_project(state)["project_id"] == second_id

    set_active_project(first_id, state)

    assert get_project_metadata(state)["project_name"] == "Sales Review"


def test_duplicate_project_metadata_activates_existing_project():
    state = {}
    metadata = {
        "project_name": "Sales Review",
        "project_description": "Review sales",
        "analysis_goal": "Find revenue drivers",
    }

    first_id, first_created = add_or_activate_project(metadata, state=state)
    second_id, second_created = add_or_activate_project(metadata, state=state)

    assert first_created is True
    assert second_created is False
    assert first_id == second_id
    assert len(list_projects(state)) == 1


def test_same_project_name_with_different_metadata_creates_separate_project():
    state = {}
    first_id, _ = add_or_activate_project(
        {
            "project_name": "Monthly Review",
            "project_description": "Sales",
            "analysis_goal": "Review revenue",
        },
        state=state,
    )
    second_id, created = add_or_activate_project(
        {
            "project_name": "Monthly Review",
            "project_description": "Operations",
            "analysis_goal": "Review downtime",
        },
        state=state,
    )

    assert created is True
    assert first_id != second_id
    assert len(list_projects(state)) == 2


def test_project_can_remember_available_dataset():
    state = {
        "datasets": {
            "dataset-1": {
                "dataset_id": "dataset-1",
                "name": "Dataset",
                "raw_df": pd.DataFrame({"a": [1]}),
                "working_df": pd.DataFrame({"a": [1]}),
                "metadata": {},
                "transformation_log": [],
                "template_mappings": {},
                "analytics_results": {},
            }
        },
        "active_dataset_id": None,
    }
    project_id, _ = add_or_activate_project({"project_name": "Linked Project"}, state=state)
    associate_dataset_with_active_project("dataset-1", state)
    state["active_dataset_id"] = None

    set_active_project(project_id, state)

    assert state["active_dataset_id"] == "dataset-1"


def test_start_new_project_draft_keeps_existing_projects():
    state = {}
    add_or_activate_project({"project_name": "Existing"}, state=state)

    start_new_project_draft(state)

    assert len(list_projects(state)) == 1
    assert get_active_project(state) is None
    assert get_project_metadata(state)["project_name"] == ""
