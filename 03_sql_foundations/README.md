# SQL Foundations - Business Analytics

## Business Problem
Business data is stored in databases and must be transformed into actionable insights.
This project focuses on answering business questions using SQL on e-commerce order data.

---

## Dataset
E-commerce order data (`datasets/ecommerce_orders.csv`), loaded into a SQLite table.

Fields:
- `order_id`
- `customer_id`
- `order_value`

The data contains a deliberate outlier (order 8 = 500) to demonstrate how a single
extreme value affects business reporting.

---

## Setup (SQLite)
Run the following from this folder to build the database:

    sqlite3 orders.db < schema.sql
    sqlite3 orders.db < seed_data.sql

Then run any query file, for example:

    sqlite3 orders.db < queries/03_aggregations.sql

In VS Code you can also open `orders.db` with the SQLTools / SQLite extension and
run the queries interactively.

---

## Files
- `schema.sql` - table definition for `orders`
- `seed_data.sql` - sample data matching the CSV
- `queries/01_select_basics.sql` - SELECT, column selection, ORDER BY
- `queries/02_filtering_where.sql` - WHERE, comparison operators, BETWEEN
- `queries/03_aggregations.sql` - COUNT, SUM, AVG, MIN, MAX, DISTINCT
- `queries/04_outlier_analysis.sql` - average with vs. without the outlier

---

## Key Insights
- Average order value WITH the outlier: 61.25
- Average order value WITHOUT the outlier: 21.36
- A single large order inflates the reported average by almost 3x
- Filtering (WHERE) is essential before drawing conclusions from aggregates
- COUNT(DISTINCT ...) shows every customer placed exactly one order

---

## Business Impact
- Aggregated SQL metrics must be checked for outliers before reporting
- WHERE filters let analysts separate normal activity from exceptional cases
- Connects directly to the Statistics Foundations project (mean vs. median)

---

## Tools
- SQL (SQLite)
- VS Code + SQLTools
