# App Walkthrough

This walkthrough documents the current Data Analytics Workbench UI and workflow. The app is designed for Streamlit wide layout and a clean sidebar with a readable logo mark, app name, subtitle, active dataset selector, and icon-based navigation.

## Global Sidebar

The sidebar shows:

- icon-only workbench/data logo mark
- Data Analytics Workbench title
- subtitle: Profiling, Preparation, Data Quality & KPI Analytics
- active dataset selector when datasets are loaded
- active dataset source, file type, and working shape
- navigation links for the full workflow

Navigation items:

- Overview
- Project Setup
- Workflow
- Data Upload
- Data Profile
- Data Dictionary
- Data Preparation
- Data Quality
- Generic Analytics
- Template Selection
- Column Mapping
- Sales Analytics
- Manufacturing Analytics
- Logistics Analytics
- Finance Analytics
- Management Summary
- Export Center

## Overview

The Overview page explains the two-layer architecture:

- generic workflow for any supported tabular dataset
- domain KPI templates that require schema detection or manual mapping

It also explains the three usage modes: Quick Data Check, BI-ready Data Preparation, and Domain KPI Analysis.

It shows a Project Summary and recommended workflow actions, and explains that `raw_df` remains unchanged, `working_df` is the transformed copy, extra columns are preserved, and analytics pages do not permanently mutate data.

Before data is loaded, the page shows that no dataset is active. After loading data, it shows raw and working row/column counts.

## Project Setup

Project Setup lets users document the business context for an analytics project before or after loading data.

It includes project name, description, analysis goal, company or department, data owner, reporting period, workflow, suggested template, desired outputs, and notes.

The page also supports:

- Save Project
- Load Project Backup
- Download Project Backup
- Project Summary

Business-facing labels avoid exposing internal JSON files as the main concept.

## Workflow

Workflow shows a guided checklist with Done, Open, and Optional statuses. Steps include project creation, dataset loading, profiling, quality check, preparation, dictionary generation, mapping, analytics, export package, and Project Backup.

The checklist is guidance only. Users can still open any page directly from the sidebar.

## Data Upload

The Data Upload page accepts:

- CSV `.csv`
- Excel workbooks `.xlsx`
- tabular JSON `.json`

Legacy `.xls` workbooks are rejected with a clear message telling the user to save the file as `.xlsx`.

The page can load bundled synthetic samples:

- Sales / Retail
- Manufacturing
- Logistics
- Finance

Every upload or sample is added to the in-session Dataset Workspace. The newly loaded dataset becomes active, `raw_df` is copied to `working_df`, mappings and logs start clean for that dataset, and schema detection runs for implemented templates.

## Data Profile

The Data Profile page works with any active `working_df`.

It shows row and column counts, duplicate count, generic quality score, column names, data types, missing values, unique values, numeric summaries, categorical summaries, detected date-like columns, detected numeric columns, detected categorical columns, and Plotly profile charts.

If no dataset is active, the page shows a warning and stops safely.

## Data Dictionary

The Data Dictionary page works with any active `working_df` and documents column-level metadata after controlled preparation changes.

It shows detected data types, missing value counts and percentages, unique counts, example values, numeric min/max/average, first and last dates where available, mapped business fields, template relevance, and quality notes. Users can filter by type, mapped/unmapped status, and columns with missing values.

The dictionary can be downloaded as CSV, Excel `.xlsx`, or JSON `.json`.

## Data Preparation

Data Preparation is the only page for user-triggered permanent transformations.

It modifies only the active dataset `working_df` and logs each successful transformation.

Available actions include rename column, drop columns, change type, parse datetime, fill missing values, drop missing rows, remove duplicates, filter rows, create a revenue column, reset to raw data, and export the prepared data as CSV.

Structural changes clear stale mappings and analytics results for the active dataset.

## Data Quality

Data Quality shows explainable 0-100 scoring for any active dataset. It reports sub-scores, explanations, and recommended fixes for missing values, duplicates, invalid numeric values, schema completeness, and date parsing issues.

When a template mapping exists, the page can calculate template-aware schema and field quality checks.

Template-specific Quality Rules report mapped-domain issues for Sales / Retail, Manufacturing, Logistics, and Finance datasets. The rules show severity, affected rows, explanations, and recommended fixes. They report issues only and do not mutate data.

## Generic Analytics

Generic Analytics works with arbitrary active datasets and does not assume sales, manufacturing, logistics, or finance meaning.

Users can choose one or multiple numeric measures, optional category grouping, optional date grouping, aggregation, and chart type. The page validates stale selections and incompatible chart configurations so column changes do not produce user-facing tracebacks.

The page shows basic insights, an aggregated table, Plotly chart, and CSV download of the aggregated result.

## Template Selection

Template Selection shows cards for:

- Generic Analytics
- Sales / Retail Analytics
- Manufacturing Analytics
- Logistics Analytics
- Finance Analytics

Cards show purpose, implementation status, required fields, optional fields, mapping requirements, sample availability, and limitations.

## Column Mapping

Column Mapping supports all implemented templates:

- Sales / Retail
- Manufacturing
- Logistics
- Finance

The user chooses a template, reviews schema detection confidence, maps required and optional fields through selectboxes, and saves a mapping for the active dataset. Unmapped extra columns remain available for profiling, preparation, generic analytics, and export.

## Domain Analytics Pages

Each domain analytics page checks compatibility before showing KPIs. If the active dataset is not mapped or detected for that template, the page shows:

- "The active dataset is not mapped to this analytics template."
- required fields
- detected and missing fields
- guidance to use Column Mapping, Generic Analytics, or a compatible sample dataset

Compatible datasets show KPI cards, charts, result tables, and issue summaries.

## Sales Analytics

Sales Analytics calculates SQL-backed revenue, order, customer, product, country, return, cancellation, and RFM metrics from mapped Sales / Retail fields.

## Manufacturing Analytics

Manufacturing Analytics calculates output, scrap, downtime, production attainment, availability approximation, quality rate approximation, simplified OEE approximation where defensible, and machine/line/shift performance tables.

## Logistics Analytics

Logistics Analytics calculates shipment count, average lead time, on-time delivery rate, delayed shipments, average delay days, shipping cost KPIs when available, carrier performance, destination performance, and delayed shipment tables.

## Finance Analytics

Finance Analytics calculates total revenue, total cost, net result, margin, transaction count, average transaction amount, budget variance when available, monthly revenue/cost, category summaries, cost center summaries, and largest transactions.

Finance requires interpretable type values such as `revenue` and `cost`; ambiguous types are flagged instead of guessed.

## Management Summary

Management Summary is deterministic and template-aware. It can summarize Sales, Manufacturing, Logistics, or Finance metrics when the active dataset is mapped. If no domain mapping is available, it shows a generic data summary with rows, columns, missingness, duplicates, quality score, and recommended next actions.

No external LLM or API key is used.

## Export Center

Export Center shows the active dataset name, source, file type, and working shape.

It can export:

- Project Backup for continuing a project later
- active working dataset as CSV, Excel `.xlsx`, or JSON `.json`
- raw dataset only when explicitly selected
- Data Dictionary as CSV, Excel `.xlsx`, or JSON `.json`
- transformation log as CSV or JSON
- Data Quality Report as CSV or Excel `.xlsx`
- template quality rules as CSV or Excel `.xlsx`
- Generic Analytics aggregated result as CSV, Excel `.xlsx`, or JSON `.json`
- KPI summaries as CSV, Excel `.xlsx`, or JSON `.json`
- available domain result tables as CSV, Excel `.xlsx`, or JSON `.json`
- chart/control result tables as CSV, Excel `.xlsx`, or JSON `.json`
- BI-ready Excel package containing cleaned data, data dictionary, quality report, transformation log, quality rules, KPI summary, and available analytics result tables

Project Backup is separate from the BI-ready Export Package. The backup is for continuing work in the Workbench; the BI-ready package is for sharing analysis outputs.

Exports use Streamlit download buttons and do not overwrite local files.
