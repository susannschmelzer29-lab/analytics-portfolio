-- 01_select_basics.sql
-- Business question: What orders do we have, and what is each order worth?

-- Show all orders
SELECT *
FROM orders;

-- Show only the columns relevant for revenue reporting
SELECT order_id, order_value
FROM orders;

-- Order the results from the most valuable order to the least valuable
SELECT order_id, customer_id, order_value
FROM orders
ORDER BY order_value DESC;
