# Feature Report

This report lists implemented features in the current Data Analytics Workbench codebase.

## Implemented Pages

- Overview
- Data Upload
- Data Profile
- Data Preparation
- Data Quality
- Generic Analytics
- Template Selection
- Column Mapping
- Sales / Retail Analytics
- Manufacturing Analytics
- Logistics Analytics planned page
- Finance Analytics planned page
- Management Summary

## Supported File Formats

- CSV `.csv`
- Excel `.xlsx`
- JSON `.json`

Excel sheet selection is implemented. JSON support is limited to tabular or normalizable records.

## Upload Behavior

Uploaded files are converted to pandas DataFrames, validated as non-empty tabular data, stored as `raw_df`, and copied to `working_df`.

The app clears stale transformation logs, mappings, and analytics outputs when loading a new dataset.

## Sample Dataset Behavior

Implemented samples:

- `sample_retail_orders.csv`
- `sample_manufacturing_operations.csv`

Both are synthetic and include intentional data quality issues.

## Data Profiling

The profiler works with any `working_df` and reports row counts, column counts, data types, missing values, duplicates, unique values, numeric summaries, categorical summaries, detected date-like columns, detected numeric columns, detected categorical columns, and visual profile charts.

## Data Preparation

Implemented transformations:

- rename column
- drop columns
- change type
- parse datetime
- remove duplicates
- fill missing values
- drop missing rows
- filter rows
- create revenue column
- reset working data
- export working data as CSV

Transformations modify `working_df` only and append human-readable log entries.

## Data Quality

The quality score is deterministic and explainable. It evaluates missing values, duplicate rows, invalid numeric values, schema completeness when mapping exists, and mapped date parsing when date fields are provided.

## Generic Analytics

Generic Analytics works with any tabular `working_df`. It supports numeric measure selection, optional category grouping, optional date grouping, sum/average/count/min/max aggregation, bar/line/scatter/histogram charts, insight text, aggregated table, and CSV export.

## Template Registry

Implemented in `app/services/template_registry.py`.

Registered templates:

- generic: always available
- sales_retail: implemented
- manufacturing: implemented
- logistics: planned
- finance: planned

## Schema Detection and Mapping

Rule-based schema detection supports Sales / Retail and Manufacturing using synonyms and fuzzy matching.

Column Mapping supports implemented domain templates:

- Sales / Retail
- Manufacturing

Mappings validate required fields, duplicate source columns, and unknown source columns.

## Sales / Retail Analytics

Implemented outputs:

- gross revenue
- net revenue
- valid order count
- valid customer count
- average order value
- total quantity sold
- return rate
- cancelled order rate
- top 10 customer revenue share
- revenue by month
- returns by month
- order count by month
- revenue by product/category/country where available
- RFM segmentation
- quality issue table

Retail aggregations use DuckDB SQL files from `sql/`.

## Manufacturing Analytics

Implemented outputs:

- total output
- total scrap
- scrap rate
- total downtime minutes
- average downtime per machine
- production attainment when planned output exists
- availability approximation when runtime and downtime exist
- quality rate approximation
- simplified OEE approximation when inputs support it
- output and downtime trends
- machine performance
- output by line and shift when available
- issue summary

## Logistics and Finance

Logistics and Finance are planned templates. They appear in navigation, template selection, and dedicated planned pages, but their KPI logic is not implemented yet.

## Management Summary

Management Summary is deterministic and currently uses calculated Sales / Retail analytics. It does not call external LLM APIs.

## Export Features

Implemented export:

- `working_df` as CSV from Data Preparation
- aggregated Generic Analytics result as CSV

## Known Limitations

- Uploaded data is stored in Streamlit session state, not a database.
- JSON support is not a full JSON schema explorer.
- `.xls`, Parquet, XML, and database connections are not implemented.
- Logistics and Finance KPI pages are planned only.
- Management Summary is retail-oriented.
- Screenshots are not committed yet.

## Not-Yet-Implemented Ideas

- Full Logistics KPI implementation.
- Full Finance KPI implementation with explicit type/sign controls.
- Deployed screenshots.
- Saved mapping profiles.
- Optional Excel export.
- More configurable date parsing.
