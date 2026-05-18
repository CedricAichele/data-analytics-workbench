# AGENTS.md

## Project

`data-analytics-workbench` is a local Streamlit data analytics MVP for portfolio use. It demonstrates the difference between generic profiling for supported tabular uploads, controlled data preparation, and schema-aware business analytics.

## Run Commands

- App: `streamlit run app/main.py`
- Tests: `pytest`

## Engineering Notes

- Keep Streamlit UI code in `app/main.py`, `app/pages/`, and `app/components/`.
- Keep business logic in `app/services/` so it can be tested without Streamlit.
- Keep dataframe transformation logic in `app/services/transformations.py`.
- Use DuckDB SQL files in `sql/` for analytical aggregations.
- Do not add external APIs, paid services, authentication, or cloud dependencies to the MVP.
- The bundled sample dataset must remain small and synthetic.
