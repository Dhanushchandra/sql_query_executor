import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.environ["DATABASE_PATH"]

CREATE_AND_INSERT_SCRIPT = """
-- USERS
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- CUSTOMERS
CREATE TABLE IF NOT EXISTS Customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    age INTEGER,
    country TEXT
);

INSERT OR IGNORE INTO Customers (first_name, last_name, age, country)
VALUES 
('John','Doe',30,'USA'),
('Robert','Luna',22,'USA'),
('David','Robinson',25,'UK'),
('John','Reinhardt',22,'UK'),
('Betty','Doe',28,'UAE');

-- ORDERS
CREATE TABLE IF NOT EXISTS Orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT,
    amount INTEGER,
    customer_id INTEGER,
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);

INSERT OR IGNORE INTO Orders (item, amount, customer_id)
VALUES
('Keyboard',400,4),
('Mouse',300,4),
('Monitor',12000,3),
('Keyboard',400,1),
('Mousepad',250,2);

-- SHIPPINGS
CREATE TABLE IF NOT EXISTS Shippings (
    shipping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT,
    customer INTEGER
);

INSERT OR IGNORE INTO Shippings (status, customer)
VALUES
('Pending',2),
('Pending',4),
('Delivered',3),
('Pending',5),
('Delivered',1);
"""

def ensure_sqlite_db():
    created = not os.path.exists(DB_PATH)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.executescript(CREATE_AND_INSERT_SCRIPT)
        conn.commit()
        print(f"✅ SQLite database created/verified at: {DB_PATH}")
        if created:
            print("📦 New database file created.")
        else:
            print("📂 Existing database updated.")
    except Exception as e:
        print("❌ Database setup error:", e)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    ensure_sqlite_db()
