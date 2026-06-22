-- seed_data.sql
-- Sample data for the orders table.
-- Mirrors datasets/ecommerce_orders.csv (note the deliberate outlier: order 8 = 500).

INSERT INTO orders (order_id, customer_id, order_value) VALUES
    (1, 101, 20),
    (2, 102, 22),
    (3, 103, 19),
    (4, 104, 23),
    (5, 105, 21),
    (6, 106, 20),
    (7, 107, 24),
    (8, 108, 500),
    (9, 109, 18),
    (10, 110, 25),
    (11, 111, 21),
    (12, 112, 22);
