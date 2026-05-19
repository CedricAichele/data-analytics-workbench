# Data Analytics Workbench

Profiling, Preparation, Data Quality & KPI Analytics.

Data Analytics Workbench is a Streamlit portfolio project that demonstrates a practical project-based analytics workflow: define an analysis project, load raw data, inspect quality, prepare a controlled working copy, explore arbitrary tabular datasets, map business fields, generate transparent KPI analytics, and save a Project Backup.

GitHub repository: `https://github.com/CedricAichele/data-analytics-workbench`  
Live Demo: not deployed yet  
License: MIT

## Business Problem

Analysts rarely receive clean, perfectly modeled datasets. A useful analytics workflow needs to separate generic data understanding from domain-specific KPI logic, preserve source data, and document preparation decisions before reporting business metrics.

This app is built around that separation:

- Generic workflow pages work with any supported tabular dataset.
- Domain KPI templates require schema detection or manual column mapping.
- Extra columns are preserved for profiling, preparation, generic analytics, and export.
- Project Setup and Workflow pages help business users understand what to do next.

## Feature Overview

- Upload CSV, Excel `.xlsx`, and tabular JSON `.json`
- Load bundled Sales / Retail, Manufacturing, Logistics, and Finance sample datasets
- Create lightweight analytics project metadata before or after loading data
- Follow a guided workflow checklist without being locked into a wizard
- Manage several datasets in one Streamlit session, prevent duplicate loads, and choose the active dataset
- Profile any active working dataframe for types, missingness, duplicates, unique values, and summaries
- Prepare data through logged transformations on `working_df`
- Generate a Data Dictionary from the active `working_df`
- Score data quality with transparent sub-scores, explanations, and recommended fixes
- Run template-specific quality rules that report issues without mutating data
- Run robust Generic Analytics with one or multiple numeric measures
- Map source columns to implemented domain templates
- Run Sales / Retail, Manufacturing, Logistics, and Finance KPI analytics with chart controls
- Export the active working dataset, documentation, KPI summaries, chart/result data, and a BI-ready Excel package
- Download or load a business-friendly Project Backup for continuing work later
- Generate deterministic template-aware management summaries without API keys

## Architecture

```text
app/
  main.py                 Streamlit entry point
  pages/                  Workflow pages
  components/             Shared layout, KPI cards, and chart helpers
  services/               Testable loading, profiling, quality, mapping, export, and analytics logic
assets/                   Workbench logo and navigation icons
data/sample/              Synthetic sample datasets
sql/                      DuckDB SQL files for Sales / Retail analytics
tests/                    pytest coverage for core services
```

Streamlit pages handle user interaction. Analytical logic lives in `app/services/` so it can be validated outside the UI.

## Guided Project Workflow

The app is organized around a simple project flow:

1. Create a project
2. Load data
3. Review profile and quality
4. Prepare data
5. Generate a data dictionary
6. Map columns if a domain KPI template is needed
7. Analyze generic trends or domain KPIs
8. Export a BI-ready package or download a Project Backup

The Workflow page shows each step as Done, Open, or Optional with a recommended next action. It is guidance, not a rigid wizard; users can still open any page directly.

## Project Setup

Project Setup lets users document lightweight business context:

- project name
- project description
- analysis goal
- company or department
- data owner or responsible person
- reporting period
- notes
- selected workflow
- suggested domain template
- desired outputs

Users can create a project before loading data, or load data first and document the project later.

## Usage Modes

The Workbench supports three common small-business workflows:

- Quick Data Check: upload data, inspect structure and quality, and export documentation.
- BI-ready Data Preparation: clean data, create a data dictionary, validate quality, and export a BI-ready package.
- Domain KPI Analysis: map fields to Sales, Manufacturing, Logistics, or Finance templates and review KPI outputs.

## Two-Layer Analytics Model

### Layer 1: Generic Workflow

Works with any supported tabular dataset:

- upload
- active dataset selection
- profile
- prepare
- quality score
- generic analytics
- export

No predefined business schema is required.

### Layer 2: Domain KPI Templates

Business KPI analytics requires schema detection or manual mapping because the app must know which columns carry domain meaning.

Implemented templates:

- Sales / Retail Analytics
- Manufacturing Analytics
- Logistics Analytics
- Finance Analytics

Templates use mapped fields for KPI calculations. They do not remove unmapped or extra dataset columns.

## Dataset Workspace

The app supports a lightweight in-session dataset workspace.

- Uploads and bundled samples are added as separate datasets.
- Loading the same sample or identical upload content again activates the existing dataset instead of creating a duplicate.
- One dataset is active at a time.
- Profiling, preparation, quality, mapping, analytics, and export operate on the active dataset.
- Switching datasets switches the active `raw_df`, `working_df`, transformation log, mappings, and analytics results.
- The workspace does not implement joins, relationships, or cross-dataset modeling.

## Supported Input Formats

Uploaded files are converted internally into pandas DataFrames.

- CSV `.csv`
- Excel workbooks `.xlsx`
- Tabular JSON `.json`

Excel note: modern `.xlsx` workbooks are supported, including sheet selection. Legacy `.xls` workbooks are not supported; save them as `.xlsx` before upload.

JSON note: JSON support is best effort for arrays of records, records-style objects, JSON Lines, and simple nested records that can be normalized. Deeply nested API JSON may require manual preprocessing.

Parquet, XML, databases, and API connections are intentionally out of scope.

## Data Preparation Model

The app never silently modifies the original uploaded dataset.

- `raw_df` stores the original upload or sample dataset.
- `working_df` stores the transformed dataset used by profiling, mapping, quality scoring, generic analytics, domain analytics, and export.
- `transformation_log` records user-triggered transformations in order.
- `template_mappings` stores mappings per implemented template and active dataset.

Data Preparation supports renaming columns, dropping columns, type conversion, date parsing, duplicate removal, missing-value handling, row filtering, calculated revenue columns, reset to raw data, and CSV download.

Analytics pages may create temporary derived analytical fields internally, but they do not overwrite `raw_df` or `working_df`.

## Data Dictionary

The Data Dictionary is generated from the active `working_df` by default, so controlled preparation changes such as column renaming are reflected across documentation, mapping, analytics, and exports.

For each column it documents:

- detected data type
- missing value count and percentage
- unique value count
- example values
- numeric min, max, and average where applicable
- first and last date where applicable
- mapped business field and template relevance where mappings exist
- quality notes such as missingness, identifier-like columns, mapped required fields, and numeric zero or negative values

The dictionary can be filtered in the app and exported as CSV, Excel `.xlsx`, or JSON `.json`.

## Data Quality

The generic data quality score works for any active dataset. It evaluates visible dimensions such as missing values, duplicate rows, invalid numeric values, schema completeness when a template mapping exists, and date parsing quality.

Template-specific quality rules add explainable checks for mapped Sales / Retail, Manufacturing, Logistics, and Finance datasets. These rules report affected row counts, severity, explanations, and recommended fixes. They do not remove rows or mutate the dataset.

## Generic Analytics

Generic Analytics works with any active `working_df` and does not assign business meaning.

Users can select:

- one or multiple numeric measures
- optional categorical grouping
- optional date grouping
- aggregation: sum, average, count, min, max
- chart type: bar, line, area, scatter, histogram, box plot
- validation that prevents stale column selections or incompatible chart settings from crashing the app

The page returns an aggregated table, Plotly chart, insight bullets, missing values for selected measures, rows used, and CSV export of the aggregated result. Multi-measure results show one result column per selected measure.

If a dataset switch, column rename, or column drop makes a previous selection invalid, the page resets or warns instead of showing a traceback.

## Domain Templates

All implemented domain pages include chart controls for date range, relevant categorical filters, top-N rankings, and chart type selection where meaningful. The defaults show a useful dashboard immediately, while the controls let users explore the same KPI layer more like a workbench.

### Sales / Retail Analytics

Required fields: `order_id`, `order_date`, `customer_id`, `product_name`, `quantity`, `unit_price`.

Outputs include gross revenue, net revenue, valid orders, valid customers, average order value, quantity sold, return rate, cancelled order rate, revenue concentration, monthly revenue, top products, customer revenue, country performance, RFM segmentation, and issue tables.

Retail analytical aggregations use DuckDB SQL files from `sql/`.

### Manufacturing Analytics

Required fields: `timestamp`, `machine_id`, `actual_output`, `scrap_count`, `downtime_minutes`.

Outputs include total output, total scrap, scrap rate, downtime minutes, average downtime per machine, production attainment when planned output exists, availability approximation, quality rate approximation, simplified OEE approximation when defensible, machine performance, line/shift views, and issue tables.

The simplified OEE metric is labeled as an approximation, not a certified OEE standard.

### Logistics Analytics

Required fields: `shipment_id`, `order_date`, `delivery_date`, `planned_delivery_date`.

Outputs include shipment count, average lead time, on-time delivery rate, delayed shipments, average delay days, shipping cost KPIs when available, shipments over time, lead-time trends, carrier performance, destination performance, and delayed shipment tables.

### Finance Analytics

Required fields: `transaction_id`, `date`, `amount`, `type`.

Outputs include total revenue, total cost, net result, margin, transaction count, average transaction amount, budget variance when available, monthly revenue/cost, category summaries, cost center summaries, and largest transaction tables.

Finance analytics requires interpretable transaction type values such as `revenue` and `cost`. It does not guess revenue/cost meaning from ambiguous data.

## Export Center

The Export Center makes output easy to find and keeps the standard export target on the active `working_df`.

Project Export:

- Download Project Backup
- Load Project Backup
- Review the current project summary

Available exports:

- active working dataset as CSV, Excel `.xlsx`, or JSON `.json`
- optional raw dataset export when explicitly selected
- Data Dictionary as CSV, Excel `.xlsx`, or JSON `.json`
- transformation log as CSV or JSON
- Data Quality Report as CSV or Excel `.xlsx`
- template quality rules as CSV or Excel `.xlsx`
- KPI summaries as CSV, Excel `.xlsx`, or JSON `.json`
- Generic Analytics aggregated result as CSV, Excel `.xlsx`, or JSON `.json`
- chart/control result tables as CSV, Excel `.xlsx`, or JSON `.json`
- calculated domain result tables as CSV, Excel `.xlsx`, or JSON `.json`
- BI-ready Excel package with sheets for cleaned data, data dictionary, quality report, transformation log, quality rules, KPI summary, Generic Analytics result, result tables, and available domain result tables

Exports use Streamlit download buttons and do not write files to disk.

Chart image and dashboard PDF exports are intentionally deferred. The current priority is reliable export of the underlying data tables that support the charts and KPIs.

## Project Backup vs BI-ready Export Package

Project Backup is for continuing a Workbench project later. It stores project details, workflow choices, mappings, transformation log, available quality context, documentation, and the cleaned working dataset when available.

BI-ready Export Package is for sharing analysis outputs. It is an Excel workbook designed for business review, documentation, and handoff.

The backup may contain internal files, but users interact with it as a Project Backup ZIP. No backend database, user account, cloud storage, or authentication is required.

## Using SQL Server Data

The public Streamlit demo does not connect directly to SQL Server. For security and deployment simplicity, SQL Server data should be exported as CSV or Excel and uploaded to the app.

Supported workflow:

```text
SQL Server query result -> CSV/XLSX export -> upload to Data Analytics Workbench
```

This avoids exposing database credentials in a public portfolio app.

Practical export options include:

- SQL Server Management Studio: run a query and save results as CSV
- SSMS Import/Export Wizard
- `bcp` command-line export
- `sqlcmd` export
- Excel or Power BI export where appropriate

Example `bcp` command:

```powershell
bcp "SELECT * FROM dbo.YourTable" queryout "C:\Temp\export.csv" -c -t, -T -S YOUR_SERVER -d YOUR_DATABASE
```

Replace the server, database, table, and output path for your environment. Use trusted authentication or a SQL login depending on your setup. Avoid uploading sensitive company data to the public demo.

## Sample Datasets

Included synthetic samples:

- `data/sample/sample_retail_orders.csv`
- `data/sample/sample_manufacturing_operations.csv`
- `data/sample/sample_logistics_shipments.csv`
- `data/sample/sample_finance_transactions.csv`

The samples intentionally include realistic data quality issues such as duplicates, missing identifiers, invalid values, delayed shipments, budget variance, and outliers.

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

Optional local helpers are included: `start_app.bat`, `start_app.ps1`, and `setup_windows.ps1`. They are not required for Streamlit Community Cloud deployment.

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

No Streamlit secrets are required for this MVP.

## Development Approach

This project was implemented using an AI-assisted coding workflow. The analytical concept, data quality rules, KPI definitions, validation logic, testing, and documentation were specified, reviewed, and refined manually.

## Limitations

- Uploaded data is held in Streamlit session state and is not persisted to a database.
- Dataset workspace supports active dataset switching, not joins or semantic relationships.
- JSON support is limited to tabular or normalizable records.
- Legacy `.xls` Excel files are not supported.
- Schema detection is rule-based and may require manual mapping correction.
- Domain KPIs require valid mapped fields.
- Finance analytics requires interpretable revenue/cost type values.
- The management summary is deterministic and does not call an external LLM.
- The app does not include authentication, user accounts, or a backend API.
- The app does not connect directly to SQL Server or other production databases.
- PDF dashboard export is not implemented.
- Project Backups are local files, not cloud-synced saved projects.
- The app is a portfolio-grade analytics prototype, not an enterprise governance or data catalog platform.

## Next Steps

- Deploy the Streamlit app and add real screenshots.
- Add saved mapping profiles for recurring datasets.
- Add richer date parsing controls for regional formats.
- Add deeper compatibility diagnostics for user-uploaded domain datasets.
- Add optional governance-style metadata fields to the Data Dictionary.
- Add optional project progress tracking for completed manual review steps.
- Add a lightweight PDF summary report if it can be done without heavy rendering dependencies.

## Portfolio Positioning

This project is designed to show Junior Data Analyst / BI Analyst readiness:

- working with messy raw data
- separating generic exploration from business KPI logic
- documenting data preparation decisions
- building explainable quality checks
- using SQL-backed analytics with DuckDB
- defining KPI logic transparently
- supporting multiple domains without restricting arbitrary datasets
- structuring and validating testable analytics logic behind a Streamlit app
