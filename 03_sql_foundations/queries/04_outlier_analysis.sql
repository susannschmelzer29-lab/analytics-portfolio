-- 04_outlier_analysis.sql
-- Business question: Does a single large order distort our average?
-- This ties the SQL project back to the Statistics Foundations insight
-- (mean vs. median, sensitivity to outliers).

-- Average WITH the outlier (order 8 = 500)
SELECT AVG(order_value) AS avg_with_outlier
FROM orders;

-- Average WITHOUT the outlier
SELECT AVG(order_value) AS avg_without_outlier
FROM orders
WHERE order_value < 50;

-- Side-by-side comparison in a single result
SELECT
    (SELECT AVG(order_value) FROM orders)                        AS avg_with_outlier,
    (SELECT AVG(order_value) FROM orders WHERE order_value < 50) AS avg_without_outlier;
