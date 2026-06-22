-- schema.sql
-- SQLite schema for the SQL Foundations project
-- Defines the orders table used to answer business questions.

DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_value REAL    NOT NULL
);
