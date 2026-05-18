# Feature Report

This report lists features implemented in the current Data Analytics Workbench codebase.

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

## Data Quality

The quality score is deterministic and explainable. It evaluates missing values, duplicate rows, invalid numeric values, schema completeness when mapping exists, and mapped date parsing when date fields are provided.

## Generic Analytics

Generic Analytics works with any active tabular `working_df`. It supports one or multiple numeric measures, optional category grouping, optional date grouping, sum/average/count/min/max aggregation, bar/line/scatter/histogram/box charts, insight text, aggregated table, and CSV export of the aggregated result.

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

- active working dataset as CSV, Excel `.xlsx`, and JSON `.json`
- optional raw dataset export when explicitly selected
- transformation log as CSV and JSON
- Generic Analytics aggregated result as CSV, Excel `.xlsx`, and JSON `.json`
- domain analytics result tables as CSV, Excel `.xlsx`, and JSON `.json`

## Known Limitations

- Data is stored in Streamlit session state, not a database.
- Dataset Workspace does not implement joins or semantic relationships.
- JSON support is not a full JSON schema explorer.
- Legacy `.xls`, Parquet, XML, and database connections are not implemented.
- Rule-based schema detection may need manual mapping correction.
- Domain KPIs require valid field mappings.
- Finance interpretation requires meaningful type values such as `revenue` and `cost`.
- Screenshots are not committed yet.

## Not-Yet-Implemented Ideas

- Deployed screenshots.
- Saved mapping profiles.
- Richer locale-aware date parsing controls.
- Multi-table exports bundled into one workbook.
- Deeper compatibility diagnostics for uploaded domain datasets.
