INSERT INTO customers (customer_id, customer_name, city, signup_date) VALUES
(1, 'Anna Krause',   'Berlin',   '2024-01-10'),
(2, 'Bernd Mueller', 'Hamburg',  '2024-02-05'),
(3, 'Carla Schmidt', 'Berlin',   '2024-02-20'),
(4, 'David Wolf',    'Muenchen', '2024-03-15'),
(5, 'Eva Lange',     'Hamburg',  '2024-04-01');

INSERT INTO products (product_id, product_name, category, unit_price) VALUES
(1, 'Notebook', 'Hardware', 899.00),
(2, 'Maus',     'Zubehoer',  25.00),
(3, 'Tastatur', 'Zubehoer',  60.00),
(4, 'Monitor',  'Hardware', 320.00);

INSERT INTO orders (order_id, customer_id, product_id, quantity, order_date) VALUES
(1,  1, 1, 1, '2024-05-01'),
(2,  1, 2, 2, '2024-05-03'),
(3,  2, 4, 1, '2024-05-05'),
(4,  2, 3, 1, '2024-05-09'),
(5,  3, 1, 1, '2024-05-10'),
(6,  3, 4, 2, '2024-05-12'),
(7,  3, 2, 3, '2024-05-15'),
(8,  4, 2, 1, '2024-05-18'),
(9,  1, 3, 1, '2024-05-20'),
(10, 2, 1, 1, '2024-05-22'),
(11, 3, 3, 2, '2024-05-25'),
(12, 4, 4, 1, '2024-05-28'),
(13, 1, 4, 1, '2024-06-02'),
(14, 3, 1, 1, '2024-06-05');