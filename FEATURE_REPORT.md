# Feature Report

This report lists features implemented in the current Data Analytics Workbench codebase.

## Implemented Pages

- Overview
- Project Setup
- Workflow
- Data Upload
- Data Profile
- Data Dictionary
- Data Preparation
- Data Quality
- Analytics Hub
- Generic Analytics
- Template Selection
- Column Mapping
- Sales / Retail Analytics
- Manufacturing Analytics
- Logistics Analytics
- Finance Analytics
- Management Summary
- Export Center

## Supported File Formats

- CSV `.csv`
- Excel workbooks `.xlsx`
- JSON `.json`

Excel sheet selection is implemented for `.xlsx`. Legacy `.xls` workbooks are not supported and produce a clear conversion message. JSON support is limited to tabular or normalizable records.

## Dataset Workspace

The app supports multiple datasets in the current Streamlit session. Each dataset stores:

- `raw_df`
- `working_df`
- metadata
- transformation log
- template mappings
- analytics results

One dataset is active at a time. All workflow pages operate on the active dataset. No joins, relationships, or cross-dataset analytics are implemented.

Duplicate sample loads and identical upload content activate the existing dataset instead of creating duplicates. Users can reset the active working dataset, remove the active dataset, or clear all loaded datasets from visible controls. Dataset removal, reset, switching, and clearing remove stale analytics/export results for the affected dataset.

Large dataset guardrails record row count, column count, estimated memory use, and warning state. Large datasets are allowed, but the UI warns that profiling, charting, and exports may take longer.

## Project Setup and Guided Workflow

Project Setup stores lightweight business context such as project name, analysis goal, owner, reporting period, selected workflow, suggested template, and desired outputs.

The Project Workspace supports multiple projects in one Streamlit session with one active project at a time. Duplicate project metadata or repeated Project Backup loads activate the existing project instead of creating duplicates. Projects can remember associated dataset IDs during the session.

Workflow shows a readable process layout with Done, Open, and Optional statuses. It recommends the next action but does not block users from opening pages freely.

Implemented usage modes:

- Quick Data Check
- BI-ready Data Preparation
- Domain KPI Analysis

## Upload and Sample Behavior

Uploads and sample datasets are validated as non-empty tabular DataFrames, added to the Dataset Workspace, and made active.

Implemented samples:

- `sample_retail_orders.csv`
- `sample_manufacturing_operations.csv`
- `sample_logistics_shipments.csv`
- `sample_finance_transactions.csv`

The samples are synthetic and include intentional data quality issues.

## Data Profiling

The profiler works with any active `working_df` and reports row counts, column counts, data types, missing values, duplicates, unique values, numeric summaries, categorical summaries, detected date-like columns, detected numeric columns, detected categorical columns, and profile charts.

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

## Data Dictionary

The Data Dictionary works with any active `working_df`. It documents column names, detected types, missingness, unique counts, example values, numeric summaries, date ranges, saved template mappings, template relevance, and quality notes.

The page supports filtering by data type, mapped/unmapped status, and missing values. It can export the dictionary as CSV, Excel `.xlsx`, or JSON `.json`.

## Data Quality

The quality score is deterministic and explainable. It evaluates missing values, duplicate rows, invalid numeric values, schema completeness when mapping exists, and mapped date parsing when date fields are provided.

Template-specific quality rules are implemented for Sales / Retail, Manufacturing, Logistics, and Finance mappings. Rules report severity, affected rows, explanations, and recommended fixes without mutating the source dataframe.

## Generic Analytics

Analytics Hub is the primary sidebar entry for analytics. It lets users choose Generic, Sales / Retail, Manufacturing, Logistics or Finance analytics, shows whether mapping is required, and displays compatibility guidance for the active dataset.

Generic Analytics works with any active tabular `working_df`. It supports one or multiple numeric measures, optional category grouping, optional date grouping, sum/average/count/min/max aggregation, bar/line/area/scatter/histogram/box charts, insight text, aggregated table, and CSV export of the aggregated result.

Generic Analytics validates stale selections after dataset switches or preparation changes. Invalid chart configurations show guidance instead of user-facing tracebacks.

## Template Registry

Registered templates:

- generic: always available
- sales_retail: implemented
- manufacturing: implemented
- logistics: implemented
- finance: implemented

Each template defines purpose, status, required fields, optional fields, synonyms, sample dataset, implemented page, and limitations.

## Schema Detection and Mapping

Rule-based schema detection uses synonyms and fuzzy matching. Column Mapping supports all implemented domain templates:

- Sales / Retail
- Manufacturing
- Logistics
- Finance

Mappings validate required fields, duplicate source columns, and unknown source columns. Mappings are stored per active dataset and template.

## Sales / Retail Analytics

Implemented outputs include gross revenue, net revenue, valid order count, valid customer count, average order value, quantity sold, return rate, cancelled order rate, top 10 customer revenue share, revenue by month, returns by month, order count by month, revenue by product/category/country where available, RFM segmentation, and quality issue tables.

Retail aggregations use DuckDB SQL files from `sql/`.

## Manufacturing Analytics

Implemented outputs include total output, total scrap, scrap rate, total downtime minutes, average downtime per machine, production attainment, availability approximation, quality rate approximation, simplified OEE approximation when inputs support it, output and downtime trends, machine performance, output by line and shift, and issue summary.

## Logistics Analytics

Implemented outputs include shipment count, average lead time, on-time delivery rate, delayed shipment count, average delay days, shipping cost KPIs when available, shipments over time, lead time trends, on-time versus delayed summary, carrier performance, destination performance, delayed shipments table, and issue summary.

## Finance Analytics

Implemented outputs include total revenue, total cost, net result, margin, transaction count, average transaction amount, budget variance when available, monthly revenue/cost, net result trend, category summaries, cost center summaries, largest transactions, and issue summary.

Finance rows with uninterpretable transaction types are flagged and excluded from KPI calculations.

## Management Summary

Management Summary is deterministic and template-aware. It summarizes Sales, Manufacturing, Logistics, or Finance analytics when compatible mappings exist. If no domain mapping exists, it returns a generic data summary with quality context and next actions. It does not call external LLM APIs.

## Export Features

Export Center supports:

- Project Backup download and load
- active working dataset as CSV, Excel `.xlsx`, and JSON `.json`
- optional raw dataset export when explicitly selected
- Data Dictionary as CSV, Excel `.xlsx`, and JSON `.json`
- transformation log as CSV and JSON
- Data Quality Report as CSV and Excel `.xlsx`
- template quality rules as CSV and Excel `.xlsx`
- KPI summaries as CSV, Excel `.xlsx`, and JSON `.json`
- Generic Analytics aggregated result as CSV, Excel `.xlsx`, and JSON `.json`
- domain analytics result tables as CSV, Excel `.xlsx`, and JSON `.json`
- chart/control result tables as CSV, Excel `.xlsx`, and JSON `.json`
- BI-ready Excel package with cleaned data, data dictionary, quality report, transformation log, quality rules, KPI summary, Generic Analytics result when available, result tables, and domain result sheets when available

Project Backup is distinct from the BI-ready Export Package. The backup is for continuing a Workbench project later; the BI-ready package is for sharing analysis outputs.

Loading the same Project Backup more than once activates the existing project.

## Known Limitations

- Data is stored in Streamlit session state, not a database.
- Project Workspace is session-based and supports one active project at a time, not project sharing or cloud persistence.
- Dataset Workspace does not implement joins or semantic relationships.
- Large datasets may be slower in browser-based Streamlit workflows; the app warns but does not add a big-data backend.
- JSON support is not a full JSON schema explorer.
- Legacy `.xls`, Parquet, XML, and database connections are not implemented.
- Rule-based schema detection may need manual mapping correction.
- Domain KPIs require valid field mappings.
- Finance interpretation requires meaningful type values such as `revenue` and `cost`.
- The Data Dictionary is useful documentation, not a full enterprise data catalog.
- Direct SQL Server connectivity and dashboard PDF export are not implemented.
- Project Backups are local ZIP files, not cloud-synced saved projects.

## Not-Yet-Implemented Ideas

- Improve guided onboarding based on tester feedback.
- Add stronger validation and sampling strategies for large uploaded datasets.
- Add an optional PDF summary report if it can be implemented without heavy rendering dependencies.
- Explore private deployment options for real company data.
- Improve reusable mapping profiles for recurring source files when Project Backup is not enough.
