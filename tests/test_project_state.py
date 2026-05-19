import pandas as pd

from app.services.project_state import (
    get_project_metadata,
    get_project_summary,
    has_project,
    initialize_project_state,
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

