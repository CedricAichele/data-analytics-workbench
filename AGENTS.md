# AGENTS.md

## Project

`data-analytics-workbench` is a Streamlit data analytics portfolio app. It demonstrates the difference between generic analytics for supported tabular uploads, controlled data preparation, explainable quality checks, and schema-aware business KPI templates.

## Run Commands

- App: `streamlit run app/main.py`
- Tests: `pytest`

## Engineering Notes

- Keep Streamlit UI code in `app/main.py`, `app/pages/`, and `app/components/`.
- Keep business logic in `app/services/` so it can be tested without Streamlit.
- Keep dataframe transformation logic in `app/services/transformations.py`.
- Keep generic exploratory aggregation logic in `app/services/generic_analytics.py`.
- Keep template definitions in `app/services/template_registry.py`.
- Keep manufacturing KPI logic in `app/services/manufacturing_analytics.py`.
- Keep logistics KPI logic in `app/services/logistics_analytics.py`.
- Keep finance KPI logic in `app/services/finance_analytics.py`.
- Keep export conversion helpers in `app/services/export_service.py`.
- Keep active dataset state changes centralized in `app/services/dataset_workspace.py`.
- Use DuckDB SQL files in `sql/` for analytical aggregations.
- Do not add external APIs, paid services, authentication, or cloud dependencies to the MVP.
- Bundled sample datasets must remain small, synthetic, and safe for GitHub.
- Analytics pages may create temporary derived analytical columns, but user-triggered permanent transformations belong on the Data Preparation page and must be logged.
