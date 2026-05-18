# Data Analytics Workbench

Profiling, Preparation, Data Quality & KPI Analytics.

Data Analytics Workbench is a Streamlit portfolio project that demonstrates a realistic analyst workflow: load raw data, inspect quality, prepare a working copy, explore any tabular dataset, map domain fields, and generate transparent KPI analytics.

GitHub repository: `https://github.com/CedricAichele/data-analytics-workbench`

## Business Problem

Analysts rarely receive clean, perfectly modeled datasets. A practical workflow needs to separate generic data understanding from domain-specific KPI logic, preserve source data, and document preparation decisions before reporting business metrics.

This project is built around that separation:

- Generic analytics works with any supported tabular dataset.
- Domain KPI templates require schema detection or manual field mapping.
- Extra columns are preserved for profiling, preparation, generic analytics, and export.

## Feature Overview

- Upload CSV, Excel `.xlsx`, and tabular JSON `.json`
- Load bundled Sales / Retail and Manufacturing sample datasets
- Profile any working dataframe for rows, columns, types, missingness, duplicates, unique values, summaries, and detected column groups
- Score data quality with transparent sub-scores, explanations, and recommended fixes
- Prepare data through logged transformations on `working_df`
- Run Generic Analytics for arbitrary tabular datasets
- Map source columns to implemented domain templates
- Run Sales / Retail KPIs, charts, and RFM segmentation
- Run Manufacturing output, scrap, downtime, attainment, and machine performance analytics
- Show Logistics and Finance as planned template extensions
- Use DuckDB SQL for the Sales / Retail analytical layer
- Generate deterministic management summaries without API keys

## Architecture

```text
app/
  main.py                 Streamlit entrypoint
  pages/                  Workflow pages
  components/             Shared layout, KPI cards, and chart helpers
  services/               Testable data loading, profiling, quality, mapping, and analytics logic
assets/
  logo.svg                Main workbench-themed logo
  logo_mark.svg           Compact logo mark
  icons/                  Local SVG icon asset set
data/sample/              Synthetic sample datasets
sql/                      DuckDB SQL files for retail analytics
tests/                    pytest coverage for core services
```

Streamlit pages orchestrate the user workflow. Business logic lives in `app/services/` so it can be tested without the UI.

## Two-Layer Analytics Model

### Layer 1: Generic Workflow

Works with any supported tabular dataset:

- upload
- profile
- prepare
- quality score
- generic analytics
- export

No predefined schema is required.

### Layer 2: Domain KPI Templates

Business KPI analytics requires schema detection or manual mapping because the app must know which columns carry domain meaning.

Implemented templates:

- Sales / Retail Analytics
- Manufacturing Analytics

Visible planned templates:

- Logistics Analytics
- Finance Analytics

Templates use only mapped fields for KPI calculations. They do not remove or hide extra dataset columns.

## Supported Input Formats

Uploaded files are converted internally into pandas DataFrames.

- CSV `.csv`
- Excel `.xlsx`, including multi-sheet selection
- JSON `.json`, best effort for arrays of records, records-style objects, JSON Lines, and simple nested records that can be normalized

Deeply nested API JSON may require preprocessing before upload. Parquet, XML, databases, and API connections are intentionally out of scope for this MVP.

## Data Preparation Model

The app never silently modifies the original uploaded dataset.

- `raw_df` stores the original upload or sample dataset.
- `working_df` stores the transformed dataset used by profiling, mapping, quality scoring, generic analytics, domain analytics, and export.
- `transformation_log` records user-triggered transformations in order.
- `column_mapping` preserves the existing Sales / Retail mapping path.
- `template_mappings` stores mappings for implemented templates.

Data Preparation supports:

- rename column
- drop columns
- change column type
- parse datetime column
- remove duplicate rows
- fill missing values
- drop rows with missing values
- filter rows
- create revenue column
- reset working data to the original upload
- download `working_df` as CSV

Analytics pages may create temporary derived fields internally, but they do not overwrite `raw_df` or `working_df`.

## Generic Analytics

The Generic Analytics page works with any `working_df`.

Users can select:

- numeric measure
- optional categorical grouping column
- optional date column
- aggregation: sum, average, count, min, max
- chart type: bar, line, scatter, histogram

The page shows an aggregated table, Plotly chart, basic insights, missing values in selected columns, rows used, and CSV download of the aggregated result.

## Sales / Retail Analytics

Required fields:

| Field | Meaning |
| --- | --- |
| `order_id` | Order or invoice identifier |
| `order_date` | Transaction date |
| `customer_id` | Customer identifier |
| `product_name` | Product or item |
| `quantity` | Units sold; negative values are returns |
| `unit_price` | Unit price |

Optional fields:

| Field | Meaning |
| --- | --- |
| `country` | Market or country |
| `product_category` | Product group |
| `invoice_status` | Used to identify cancelled orders |

Implemented Sales / Retail outputs:

- gross sales revenue
- net revenue
- valid orders and customers
- average order value
- quantity sold
- return rate
- cancelled order rate
- revenue share from top 10 customers
- revenue by month
- order count by month
- returns by month
- top products and customers
- country performance when available
- RFM customer segmentation
- data quality issue table

Retail aggregations use SQL files in `sql/` through DuckDB.

## Manufacturing Analytics

Required fields:

| Field | Meaning |
| --- | --- |
| `timestamp` | Production record timestamp |
| `machine_id` | Machine or asset identifier |
| `actual_output` | Produced units |
| `scrap_count` | Defective or rejected units |
| `downtime_minutes` | Downtime minutes |

Optional fields:

| Field | Meaning |
| --- | --- |
| `planned_output` | Target production |
| `runtime_minutes` | Operating minutes |
| `line` | Production line |
| `shift` | Shift |
| `product` | Product or SKU |
| `quality_status` | Inspection or quality state |

Implemented Manufacturing outputs:

- total output
- total scrap
- scrap rate
- total downtime minutes
- average downtime per machine
- production attainment when planned output exists
- availability approximation when runtime and downtime exist
- quality rate approximation
- simplified OEE approximation when the required inputs exist
- output and downtime over time
- output, scrap rate, and downtime by machine
- output by line and shift when available
- issue summary, downtime table, and scrap table

The simplified OEE metric is labeled as an approximation and is not presented as a certified OEE standard.

## Logistics and Finance Status

Logistics and Finance are visible planned templates. Their schema definitions, required fields, optional fields, and limitations are documented in the app, but full KPI pages are not implemented yet.

Finance analytics does not guess whether rows are revenue or cost. A future implementation will require a reliable type, category, or sign convention.

## Sample Datasets

Included samples:

- `data/sample/sample_retail_orders.csv`
- `data/sample/sample_manufacturing_operations.csv`

Both are synthetic and intentionally include realistic quality issues for portfolio demonstration.

## Tech Stack

- Python
- Streamlit
- pandas
- DuckDB
- Plotly
- openpyxl
- pytest

No external database, paid API, cloud credential, or notebook runtime is required.

## Run Locally

```bash
git clone https://github.com/CedricAichele/data-analytics-workbench.git
cd data-analytics-workbench
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app/main.py
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The app opens at:

```text
http://127.0.0.1:8501
```

Optional local helpers are included:

- `start_app.bat`
- `start_app.ps1`
- `setup_windows.ps1`

They are not required for Streamlit Community Cloud deployment.

## Run Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Deployment

Streamlit Community Cloud settings:

| Setting | Value |
| --- | --- |
| Repository | `CedricAichele/data-analytics-workbench` |
| Branch | `main` |
| Main file path | `app/main.py` |

Deployment steps:

1. Push this repository to GitHub.
2. Go to Streamlit Community Cloud.
3. Create a new app.
4. Select repository `CedricAichele/data-analytics-workbench`.
5. Select branch `main`.
6. Set main file path to `app/main.py`.
7. Deploy.

No Streamlit secrets are required for the MVP.

## Upload to GitHub

```bash
git init
git status
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/CedricAichele/data-analytics-workbench.git
git push -u origin main
```

If `origin` already exists:

```bash
git remote set-url origin https://github.com/CedricAichele/data-analytics-workbench.git
git push -u origin main
```

## Screenshots

Screenshots will be added after the deployed Streamlit app is finalized.

## Development Approach

This project was implemented using an AI-assisted coding workflow. The analytical concept, data quality rules, KPI definitions, validation logic, testing, and documentation were specified, reviewed, and refined manually.

## Limitations

- Uploaded data is held in Streamlit session state and is not persisted to a database.
- JSON support is limited to tabular or normalizable records.
- `.xls` Excel files are not supported.
- Schema detection is rule-based and may require manual correction.
- Sales / Retail and Manufacturing KPIs require valid field mappings.
- Logistics and Finance templates are planned, not fully implemented.
- The management summary is deterministic and does not call an external LLM.
- The app does not include authentication, user accounts, or a backend API.

## Next Steps

- Add deployed app screenshots.
- Implement Logistics KPIs for shipment lead time and on-time delivery.
- Implement Finance KPIs with explicit type/sign-convention controls.
- Add saved mapping profiles for recurring datasets.
- Add richer date parsing controls for regional formats.
- Add optional Excel export for prepared data.

## Portfolio Positioning

This project is designed to show Junior Data Analyst / BI Analyst readiness:

- working with messy raw data
- separating generic profiling from business KPI logic
- documenting data preparation decisions
- building explainable quality checks
- using SQL-backed analytics with DuckDB
- implementing KPI definitions transparently
- supporting multiple domains without restricting arbitrary datasets
- writing testable Python services behind a Streamlit app
