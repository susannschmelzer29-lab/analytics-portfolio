# 04 – SQL Advanced Cases

Advanced SQL analyses on a small e-commerce data model:
revenue analysis, customer segmentation, and churn detection with SQLite.

## Data model

Three tables with referential integrity:

| Table       | Content                              | Records |
|-------------|--------------------------------------|---------|
| `customers` | Customer master data (name, city)    | 5       |
| `products`  | Product catalog (name, price)        | 4       |
| `orders`    | Orders (customer, product, quantity) | 14      |

Note: One customer (Eva Lange) deliberately has **no** order – as a test case for the churn analysis.

## Queries

| Query                  | Question                              |
|------------------------|---------------------------------------|
| `revenue_total`        | Total revenue across all orders       |
| `revenue_by_customer`  | Revenue per customer, descending      |
| `revenue_by_city`      | Revenue per city incl. customer count |
| `high_value_customers` | Customers with revenue > 500 €        |
| `product_analysis`     | Products by revenue, with rank        |
| `churn_analysis`       | Customers without orders (LEFT JOIN)  |

## Key results

- **Total revenue:** 5,586 €
- **Top customer:** Carla (2,633 €), followed by Anna (1,329 €) and Bernd (1,279 €)
- **Highest-revenue city:** Berlin (3,962 € / 2 customers), ahead of Hamburg (1,279 €) and Munich (345 €)
- **Top product:** Notebook (3,596 €), ahead of Monitor, Tastatur and Maus
- **Churn:** Eva Lange (Hamburg) – 0 orders

## Stack

SQLite · VS Code with SQLTools · pure SQL (no external dependencies)
