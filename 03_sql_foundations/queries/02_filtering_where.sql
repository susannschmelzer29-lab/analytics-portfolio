-- 02_filtering_where.sql
-- Business question: Which orders are "normal" and which are unusually large?

-- Orders below 50 (the typical range for this shop)
SELECT order_id, order_value
FROM orders
WHERE order_value < 50;

-- Unusually large orders (potential outliers) worth investigating
SELECT order_id, customer_id, order_value
FROM orders
WHERE order_value >= 50;

-- Orders within a specific value band
SELECT order_id, order_value
FROM orders
WHERE order_value BETWEEN 20 AND 25;
