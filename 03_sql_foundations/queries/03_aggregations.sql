-- 03_aggregations.sql
-- Business question: What is our overall revenue picture?

-- Total number of orders
SELECT COUNT(*) AS total_orders
FROM orders;

-- Total, average, minimum and maximum order value
SELECT
    SUM(order_value)   AS total_revenue,
    AVG(order_value)   AS average_order_value,
    MIN(order_value)   AS smallest_order,
    MAX(order_value)   AS largest_order
FROM orders;

-- How many distinct customers placed an order?
SELECT COUNT(DISTINCT customer_id) AS unique_customers
FROM orders;
