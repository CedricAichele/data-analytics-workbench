# Data

This folder contains small synthetic sample datasets used by Data Analytics Workbench.

## Sample Retail Orders

`sample/sample_retail_orders.csv` is a synthetic retail order dataset with more than 500 rows. It is designed to be realistic enough for portfolio demonstrations while remaining small enough for GitHub.

The sample includes intentional data quality issues:

- missing customer IDs
- duplicated rows
- negative quantities for returns
- zero or invalid unit prices
- mixed date formats
- cancelled orders

The data is synthetic and does not represent real customers or transactions.

## Sample Manufacturing Operations

`sample/sample_manufacturing_operations.csv` is a synthetic production operations dataset with more than 500 rows.

The sample includes:

- production timestamps
- machine IDs
- production lines
- shifts
- products
- planned output
- actual output
- scrap count
- downtime minutes
- runtime minutes
- quality status

It includes intentional data quality issues:

- missing machine IDs
- duplicated rows
- zero planned output
- missing shift values
- occasional high scrap counts
- occasional high downtime

The data is synthetic and does not represent a real factory, production line, customer, or product.

## Sample Logistics Shipments

`sample/sample_logistics_shipments.csv` is a synthetic shipment dataset with more than 500 rows.

The sample includes shipment IDs, order dates, delivery dates, planned delivery dates, carriers, origins, destinations, shipping costs, and delivery status.

It includes intentional data quality issues:

- missing carrier values
- duplicated rows
- missing delivery dates
- delayed shipments
- shipping cost outliers

The data is synthetic and does not represent real shipments, carriers, or customers.

## Sample Finance Transactions

`sample/sample_finance_transactions.csv` is a synthetic finance transaction dataset with more than 500 rows.

The sample includes transaction IDs, dates, amounts, revenue/cost type values, categories, accounts, cost centers, budget, and actual values.

It includes intentional data quality issues:

- missing category values
- duplicated rows
- zero amount rows
- budget and actual variance
- occasional cost outliers

The data is synthetic and does not represent real accounts, budgets, or transactions.
