🧠 SQL Runner Dashboard

A full-stack Flask + React application for executing and previewing SQL queries securely — with JWT authentication, responsive UI (MUI), and SQLite as the database backend.

🚀 Features

✅ Run and preview SQL queries securely
✅ View existing tables and sample data
✅ JWT-based user authentication
✅ Responsive, modern UI built with Material UI
✅ Error handling with detailed messages
✅ Backend (Flask) + Frontend (React) containerized via Docker

📂 Project Structure
sql_query_executer/
│
├── app.py
├── setup_db.py
├── requirements.txt
├── Dockerfile
├── .env
│── sql_runner.db
│
├── client/
│ ├── src/
│ ├── package.json
│ ├── Dockerfile
│ └── build/ (generated after React build)
│
└── docker-compose.yml

⚙️ Environment Variables

Your .env file (inside backend) should contain:

DATABASE_PATH
JWT_SECRET
JWT_ALGORITHM
JWT_EXP_MINUTES

🐳 Running with Docker Compose
Step 1️⃣ — Build and start all containers
docker-compose up --build

Step 2️⃣ — Access the app

Frontend: http://localhost:3003

Backend API: http://localhost:5000

🧰 Development Setup (Without Docker)

If you prefer to run manually:

Backend
cd backend
python -m venv venv
source venv/bin/activate # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python setup_db.py
python app.py

Frontend
cd client
npm install
npm start

🧪 Example Queries
-- View all customers
SELECT \* FROM Customers;

-- Join customers with their orders
SELECT c.first_name, c.last_name, o.item, o.amount
FROM Customers c
JOIN Orders o ON c.customer_id = o.customer_id;

-- Total amount spent per customer
SELECT c.first_name, c.last_name, SUM(o.amount) AS total_spent
FROM Customers c
JOIN Orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id;

🛑 Security Notes

Queries on the users table are restricted.

Dangerous SQL operations like ATTACH, DETACH, PRAGMA writable_schema are blocked.

🧱 Tech Stack

| Layer      | Technology              |
| ---------- | ----------------------- |
| Frontend   | React + MUI             |
| Backend    | Flask                   |
| Database   | SQLite                  |
| Auth       | JWT                     |
| Deployment | Docker & Docker Compose |
