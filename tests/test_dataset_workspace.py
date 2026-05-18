import pandas as pd

from app.services.dataset_workspace import (
    add_dataset,
    append_active_transformation_log,
    get_active_analytics_result,
    get_active_working_df,
    get_active_template_mapping,
    list_datasets,
    reset_active_working_df,
    set_active_dataset,
    set_active_analytics_result,
    set_active_template_mapping,
    update_active_working_df,
)


def test_workspace_adds_and_switches_active_datasets():
    state = {}
    first_id = add_dataset("First", pd.DataFrame({"a": [1, 2]}), {"source": "sample"}, state=state)
    second_id = add_dataset("Second", pd.DataFrame({"b": [3]}), {"source": "upload"}, state=state)

    assert state["active_dataset_id"] == second_id
    assert len(list_datasets(state)) == 2

    set_active_dataset(first_id, state)

    assert get_active_working_df(state).columns.tolist() == ["a"]
    assert state["dataset_name"] == "First"


def test_workspace_updates_working_data_log_and_mapping():
    state = {}
    add_dataset("Dataset", pd.DataFrame({"a": [1, 2, 3]}), {}, state=state)

    update_active_working_df(pd.DataFrame({"a": [1]}), state)
    append_active_transformation_log("Filtered rows", state)
    set_active_template_mapping("finance", {"amount": "a"}, state)

    assert len(get_active_working_df(state)) == 1
    assert state["transformation_log"] == ["Filtered rows"]
    assert get_active_template_mapping("finance", state) == {"amount": "a"}

    reset_active_working_df(state)

    assert len(get_active_working_df(state)) == 3
    assert state["transformation_log"] == []
    assert get_active_template_mapping("finance", state) is None


def test_workspace_keeps_analytics_results_per_active_dataset():
    state = {}
    first_id = add_dataset("First", pd.DataFrame({"a": [1]}), {}, state=state)
    set_active_analytics_result("generic_analytics_result", "first-result", state)
    second_id = add_dataset("Second", pd.DataFrame({"b": [2]}), {}, state=state)
    set_active_analytics_result("generic_analytics_result", "second-result", state)

    set_active_dataset(first_id, state)
    assert get_active_analytics_result("generic_analytics_result", state) == "first-result"
    assert state["generic_analytics_result"] == "first-result"

    set_active_dataset(second_id, state)
    assert get_active_analytics_result("generic_analytics_result", state) == "second-result"
    assert state["generic_analytics_result"] == "second-result"
