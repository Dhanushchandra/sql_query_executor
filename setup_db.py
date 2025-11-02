import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


CREATE_AND_INSERT_SCRIPT = """

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(150) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);


CREATE TABLE IF NOT EXISTS Customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    age INTEGER,
    country VARCHAR(100)
);

INSERT INTO Customers (first_name, last_name, age, country)
VALUES 
('John','Doe',30,'USA'),
('Robert','Luna',22,'USA'),
('David','Robinson',25,'UK'),
('John','Reinhardt',22,'UK'),
('Betty','Doe',28,'UAE')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS Orders (
    order_id SERIAL PRIMARY KEY,
    item VARCHAR(100),
    amount INTEGER,
    customer_id INTEGER REFERENCES Customers(customer_id)
);

INSERT INTO Orders (item, amount, customer_id)
VALUES
('Keyboard',400,4),
('Mouse',300,4),
('Monitor',12000,3),
('Keyboard',400,1),
('Mousepad',250,2)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS Shippings (
    shipping_id SERIAL PRIMARY KEY,
    status VARCHAR(100),
    customer INTEGER
);

INSERT INTO Shippings (status, customer)
VALUES
('Pending',2),
('Pending',4),
('Delivered',3),
('Pending',5),
('Delivered',1)
ON CONFLICT DO NOTHING;
"""

def ensure_pg_db():
    conn = None
    try:
        print("Connecting to:", DATABASE_URL)
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(CREATE_AND_INSERT_SCRIPT)
        conn.commit()
        print("✅ PostgreSQL database schema and sample data created/verified.")
    except Exception as e:
        print("❌ Database setup error:", e)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    ensure_pg_db()
