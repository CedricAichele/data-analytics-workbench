# Data Analytics Workbench

Profiling, Preparation, Data Quality & KPI Analytics.

Data Analytics Workbench is a professional Streamlit portfolio project that demonstrates a realistic analyst workflow: upload raw datasets, inspect data quality, apply controlled transformations, map business fields and generate transparent KPI analytics.

GitHub repository: `https://github.com/CedricAichele/data-analytics-workbench`

The project is intentionally split into two layers:

- Generic data profiling works with any supported tabular upload.
- Business KPI analytics requires a valid domain schema or manual column mapping.

The first implemented domain template is Retail / Sales Analytics. The codebase also leaves a clear extension point for future Operations / Manufacturing Analytics.

## Business Problem

Analysts rarely receive perfect datasets. A practical analytics workflow needs to separate raw-data inspection from business metric calculation, document data preparation decisions, and avoid changing source data without traceability.

This app demonstrates that workflow by keeping the original upload as `raw_df`, creating a separate `working_df` for transformations, and recording every preparation step in a transformation log.

## Feature Overview

- CSV, Excel `.xlsx`, and JSON `.json` upload for arbitrary tabular datasets
- Bundled synthetic retail sample dataset with realistic data quality issues
- Generic profiling for rows, columns, data types, missing values, duplicate rows, unique counts, numeric summaries, categorical summaries, and detected date-like columns
- Controlled Data Preparation page for renaming columns, dropping columns, type conversion, datetime parsing, missing-value handling, duplicate removal, row filtering, and calculated revenue creation
- Transparent transformation log
- Export of transformed `working_df` as CSV
- Explainable 0-100 data quality score
- Rule-based retail schema detection with synonym and fuzzy matching
- Manual retail column mapping with validation
- Retail cleaning pipeline that flags returns, invalid prices, missing customers, cancelled orders, duplicate rows, and date issues
- DuckDB SQL layer for analytical aggregations
- Retail KPIs, monthly trends, product/customer/country performance, and RFM customer segmentation
- Deterministic management summary with no API key or external LLM dependency

## Architecture Overview

```text
app/
  main.py                 Streamlit entrypoint
  pages/                  Multipage workflow
  components/             Reusable UI components and Plotly charts
  services/               Testable profiling, preparation, quality, mapping, SQL, retail, and summary logic
assets/                   SVG logo and portfolio branding assets
sql/                      DuckDB SQL files used by the analytics layer
data/sample/              Synthetic sample dataset
tests/                    pytest coverage for core services
```

The Streamlit pages orchestrate the workflow. Business logic lives in `app/services/` so it can be tested without the UI.

## Data Preparation Model

The app never silently modifies the original uploaded dataset.

- `raw_df` stores the original upload or bundled sample.
- `working_df` stores the transformed dataset used by profiling, mapping, quality scoring, and analytics.
- `transformation_log` stores human-readable descriptions of every applied transformation.
- `column_mapping` stores the saved mapping for domain-specific analytics.

Users can reset `working_df` back to the original upload at any time and can export the transformed working dataset as CSV.

## Supported Input Formats

The app converts every uploaded file into a pandas DataFrame before profiling, preparation, mapping, and analytics.

- CSV is the primary format for simple tabular datasets.
- Excel `.xlsx` is supported through `openpyxl`; workbooks with multiple sheets can be loaded by selecting the desired sheet.
- JSON `.json` is supported as a best-effort tabular import for arrays of records, records-oriented files, JSON Lines, and simple nested records that can be normalized.

Deeply nested API JSON may require manual preprocessing before upload. JSON files must represent tabular records or normalizable nested records; the app shows a clear error instead of crashing when the structure is not suitable.

## Generic Profiling vs KPI Analytics

Generic profiling answers questions such as:

- How many rows and columns are present?
- Which columns have missing values?
- Are there duplicate rows?
- Which columns appear numeric, categorical, or date-like?
- What are the distributions of selected fields?

Business KPI analytics answers domain-specific questions such as:

- What is net sales revenue?
- Which products and customers drive revenue?
- How concentrated is revenue among top customers?
- Which customers are Champions, Loyal Customers, At Risk, or Low Value?

Those KPI questions require the app to know which columns represent order ID, order date, customer ID, product, quantity, unit price, and optional business fields. The schema detector can suggest mappings, but users can also map fields manually.

## Tech Stack

- Python
- Streamlit
- pandas
- DuckDB
- Plotly
- openpyxl
- pytest

No external database, paid API, cloud service, or notebook runtime is required.

## How To Run Locally

```bash
git clone https://github.com/CedricAichele/data-analytics-workbench.git
cd data-analytics-workbench
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/main.py
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

## Running on Windows

Open the repository folder in Windows Explorer after cloning or downloading the project. The folder name should be:

```text
data-analytics-workbench
```

If you are already in PowerShell, make sure you change into the repository root before running project commands:

```powershell
cd path\to\data-analytics-workbench
```

The easiest startup option is to double-click:

```text
start_app.bat
```

The batch file changes into the repository folder, creates `.venv` if needed, installs `requirements.txt`, and starts Streamlit at:

```text
http://127.0.0.1:8501
```

To run from PowerShell, open PowerShell in the repository root, not `C:\WINDOWS\system32`, and run:

```powershell
.\start_app.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start_app.ps1
```

For first-time setup and validation:

```powershell
.\setup_windows.ps1
```

Troubleshooting:

- If `python` is not recognized, try `py`.
- If neither `python` nor `py` works, install Python 3.12 or newer from `https://www.python.org/downloads/`.
- If Windows opens Microsoft Store, disable App Execution Aliases for `python.exe` and `python3.exe`.
- App Execution Aliases are under Settings > Apps > Advanced app settings > App execution aliases.
- Always run commands from the repository root, not `C:\WINDOWS\system32`.

## Run Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Upload to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/CedricAichele/data-analytics-workbench.git
git push -u origin main
```

## Deployment

This app is ready for Streamlit Community Cloud deployment.

1. Push this repository to GitHub.
2. Go to Streamlit Community Cloud.
3. Create a new app.
4. Select repository `CedricAichele/data-analytics-workbench`.
5. Select branch `main`.
6. Set the main file path to `app/main.py`.
7. Deploy.
8. Open the generated `streamlit.app` URL.

Deployment notes:

- `requirements.txt` contains the runtime dependencies Streamlit Community Cloud installs.
- `.streamlit/config.toml` contains the Streamlit theme and startup config.
- No secrets are required for the MVP.
- No external database, paid API, local file outside the repository, or local environment variable is required.

Streamlit Community Cloud settings:

| Setting | Value |
| --- | --- |
| Repository | `CedricAichele/data-analytics-workbench` |
| Branch | `main` |
| Main file path | `app/main.py` |

## Expected Retail Dataset Schema

Required fields:

| Field | Meaning |
| --- | --- |
| `order_id` | Unique order or invoice identifier |
| `order_date` | Date or timestamp of the transaction |
| `customer_id` | Customer identifier |
| `product_name` | Product or item description |
| `quantity` | Units purchased; negative values are treated as returns |
| `unit_price` | Price per unit; values `<= 0` are treated as invalid for revenue |

Optional fields:

| Field | Meaning |
| --- | --- |
| `country` | Customer or order market |
| `product_category` | Product category or department |
| `invoice_status` | Order status used to identify cancellations |

Supported synonym examples include `invoice_no`, `invoice_date`, `client_id`, `description`, `qty`, `sales_price`, `market`, and `order_status`.

## Data Quality Score

The score is transparent. In generic profiling mode it evaluates dataset-level issues. When a domain template is selected, it also evaluates schema completeness and mapped date parsing.

- missing values
- duplicate rows
- invalid numeric values
- schema completeness for the selected template
- date parsing issues

The UI shows sub-scores, plain-language explanations, and recommended fixes.

## Retail Cleaning Rules

The retail pipeline:

- standardizes mapped columns to internal names
- parses `order_date`
- calculates `gross_revenue` and `net_revenue`
- flags returns where `quantity < 0`
- flags invalid prices where `unit_price <= 0`
- flags missing customers
- flags cancelled orders from `invoice_status`
- flags exact duplicate rows after standardization
- retains a data quality issue summary for auditability

Flagged rows remain visible in the cleaned data preview. KPI calculations exclude rows that would distort net revenue.

## KPI Definitions

| KPI | Definition |
| --- | --- |
| Gross sales revenue | Positive `quantity * unit_price` for rows with valid dates and non-duplicate records, before return and cancellation exclusions |
| Net revenue | Positive valid sales excluding returns, cancelled orders, invalid prices, invalid dates, and duplicate rows |
| Valid orders | Distinct order IDs included in net revenue |
| Valid customers | Distinct customers included in net revenue |
| Average order value | Net revenue divided by valid orders |
| Total quantity sold | Sum of positive quantities included in net revenue |
| Return rate | Non-duplicate return rows divided by non-duplicate rows |
| Cancelled order rate | Distinct cancelled orders divided by distinct non-duplicate orders |
| Top 10 customer share | Net revenue from the 10 highest-revenue customers divided by total net revenue |

## RFM Segmentation

RFM is calculated from valid net revenue rows:

- Recency: days since last purchase, using the dataset's latest valid order date as the reference point
- Frequency: number of distinct valid orders
- Monetary: total valid net revenue

Each metric receives a 1-5 score using percentile ranks. Segments use simple, explainable rules:

- Champions: recent buyers with high frequency and high monetary value
- Loyal Customers: high frequency and solid monetary value
- Potential Loyalists: recent customers with moderate repeat behavior
- New Customers: recent customers with low frequency
- At Risk: historically active customers with poor recent activity
- Low Value: fallback for low monetary/frequency profiles

## Screenshots

Add screenshots after running the app locally:

- `screenshots/data_upload.png`
- `screenshots/data_profile.png`
- `screenshots/data_preparation.png`
- `screenshots/column_mapping.png`
- `screenshots/retail_analytics.png`
- `screenshots/management_summary.png`

## Example Insights

With the bundled sample dataset, the app can surface insights such as:

- net revenue trend by month
- products and categories contributing the most revenue
- countries with stronger order volume
- customer revenue concentration in the top 10 customers
- customer segment distribution across Champions, Loyal Customers, At Risk, and Low Value
- data quality risks such as returns, cancellations, invalid prices, duplicates, and missing customer IDs

## Development Approach

This project was implemented using an AI-assisted coding workflow. The analytical concept, data quality rules, KPI definitions, validation logic and documentation are specified, reviewed and refined manually.

## Limitations

- The MVP runs locally and does not include authentication or user accounts.
- Uploaded data is held in Streamlit session state, not persisted to a database.
- Schema detection is rule-based and intentionally simple.
- JSON loading is designed for tabular or normalizable records, not deeply nested API payload exploration.
- The management summary is deterministic and does not call an external LLM.
- The Operations / Manufacturing template is only an architecture placeholder.

## Next Steps

- Add screenshot assets for the README.
- Add an Operations / Manufacturing template with downtime, throughput, and defect KPIs.
- Add saved mapping profiles for repeated datasets.
- Add richer date parsing controls for regional formats.
- Add screenshots from the deployed Streamlit app.

## Portfolio Positioning

This project is designed to show recruiter-relevant analytics skills for Junior Data Analyst and BI Analyst roles:

- ability to reason about messy raw data
- controlled data preparation with an auditable transformation log
- separation of exploratory profiling from business metric logic
- transparent data quality scoring
- practical KPI definitions
- SQL-based aggregation with DuckDB
- customer segmentation using RFM
- readable Streamlit product workflow
- testable Python service design
