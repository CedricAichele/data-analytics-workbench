from app.services.dataset_workspace import list_datasets
from app.services.demo_flows import start_guided_demo
from app.services.project_state import get_project_metadata, list_projects


def test_sales_demo_creates_project_and_sample_dataset():
    state = {}

    result = start_guided_demo("sales_retail", state)

    assert result.project_created is True
    assert result.dataset_created is True
    assert state["selected_template_id"] == "sales_retail"
    assert get_project_metadata(state)["suggested_template"] == "Sales / Retail"
    assert len(list_projects(state)) == 1
    assert len(list_datasets(state)) == 1


def test_starting_same_demo_activates_existing_dataset_and_project():
    state = {}

    first = start_guided_demo("sales_retail", state)
    second = start_guided_demo("sales_retail", state)

    assert first.project_id == second.project_id
    assert first.dataset_id == second.dataset_id
    assert second.project_created is False
    assert second.dataset_created is False
    assert len(list_projects(state)) == 1
    assert len(list_datasets(state)) == 1
