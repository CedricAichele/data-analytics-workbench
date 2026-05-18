import pandas as pd

from app.services.data_dictionary import generate_data_dictionary
from app.services.dataset_workspace import (
    add_dataset,
    append_active_transformation_log,
    get_active_raw_df,
    get_active_transformation_log,
    get_active_working_df,
    update_active_working_df,
)
from app.services.transformations import create_transformation_log_entry, rename_column


def test_column_rename_updates_working_data_dictionary_and_log_without_mutating_raw():
    state = {}
    add_dataset("Prepared dataset", pd.DataFrame({"old_name": [1, 2], "extra": ["a", "b"]}), {}, state=state)

    renamed = rename_column(get_active_working_df(state), "old_name", "new_name")
    update_active_working_df(renamed, state)
    append_active_transformation_log(create_transformation_log_entry("Rename column", "old_name -> new_name"), state)

    assert get_active_raw_df(state).columns.tolist() == ["old_name", "extra"]
    assert get_active_working_df(state).columns.tolist() == ["new_name", "extra"]
    assert "Rename column: old_name -> new_name" in get_active_transformation_log(state)

    dictionary = generate_data_dictionary(get_active_working_df(state))
    assert "new_name" in dictionary["column_name"].tolist()
    assert "old_name" not in dictionary["column_name"].tolist()
