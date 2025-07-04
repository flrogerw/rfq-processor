-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop tables
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS supplier_products CASCADE;
DROP TABLE IF EXISTS rfq_logs CASCADE;


-- Create tables
CREATE TABLE IF NOT EXISTS rfq_logs (
                message_id TEXT PRIMARY KEY,
                subject TEXT,
                email_from TEXT,
                timestamp TIMESTAMPTZ,
                status TEXT
            );

CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supplier_products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    part_number TEXT,
    category TEXT,
    embedding vector(768),
    supplier_id INTEGER NOT NULL,
    price REAL NOT NULL,
    origin TEXT NOT NULL DEFAULT 'United States',
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

-- Optional: Insert dummy suppliers
INSERT INTO suppliers (name, email)
VALUES
('Supplier 1', 'supplier1@example.com'),
('Supplier 2', 'supplier2@example.com'),
('Supplier 3', 'supplier3@example.com'),
('Supplier 4', 'supplier4@example.com'),
('Supplier 5', 'supplier5@example.com')
ON CONFLICT DO NOTHING;
