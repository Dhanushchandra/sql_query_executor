from flask import Flask,send_from_directory, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.environ["DATABASE_PATH"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]
JWT_EXP_MINUTES = int(os.environ["JWT_EXP_MINUTES"])

app = Flask(__name__, static_folder="client/build", static_url_path="/")
CORS(app)


# --- DB connection helper ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# --- JWT helpers ---
def create_token(user_id, username):
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXP_MINUTES),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"error": "Authorization header missing"}), 401
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Authorization header must be: Bearer <token>"}), 401
        try:
            payload = decode_token(parts[1])
            request.user = {"id": payload.get("sub"), "username": payload.get("username")}
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)

    return decorated


# --- Initialize DB if needed ---
def ensure_users_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


# --- Auth endpoints ---
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    hashed = generate_password_hash(password)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            return jsonify({"error": "username already exists"}), 400
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hashed),
        )
        conn.commit()
        return jsonify({"message": "user created"}), 201
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            return jsonify({"error": "invalid credentials"}), 401
        token = create_token(row["id"], row["username"])
        return jsonify({"access_token": token, "token_type": "bearer", "expires_in_minutes": JWT_EXP_MINUTES})
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# --- Protected SQL endpoints ---
@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/tables")
@token_required
def list_tables():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [r["name"] for r in cur.fetchall()]
        return jsonify({"tables": tables})
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/table/<table_name>")
@token_required
def table_info(table_name):
    # basic validation for safe identifiers
    if not table_name.isidentifier():
        return jsonify({"error": "Invalid table name"}), 400

    # restrict access to 'users' table
    if table_name.lower() == "users":
        return jsonify({"error": "Access to 'users' table is restricted"}), 403

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # fetch schema info
        cur.execute(f"PRAGMA table_info({table_name});")
        columns = [{"column_name": r[1], "data_type": r[2]} for r in cur.fetchall()]

        # fetch sample rows
        cur.execute(f"SELECT * FROM {table_name} LIMIT 5;")
        # convert rows to dicts
        col_names = [desc[0] for desc in cur.description]
        rows = [dict(zip(col_names, row)) for row in cur.fetchall()]

        return jsonify({"columns": columns, "sample": rows})
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()



@app.route("/execute", methods=["POST"])
@token_required
def execute():
    payload = request.get_json(force=True, silent=True)
    if not payload or "query" not in payload:
        return jsonify({"error": "Missing JSON body with 'query'"}), 400

    query = payload["query"].strip()
    q_upper = query.upper()

    # Forbidden SQL keywords and schema operations
    forbidden = [
        "ATTACH",
        "DETACH",
        "PRAGMA WRITABLE_SCHEMA",
        "SQLITE_SCHEMA",
        "SQLITE_MASTER"
    ]
    if any(token in q_upper for token in forbidden):
        return jsonify({"error": "Forbidden operation in query"}), 403

    # 🚫 Block any query touching the users table
    if "USERS" in q_upper:
        return jsonify({"error": "Access to 'users' table is restricted"}), 403

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query)

        # Handle SELECT / WITH queries (return result)
        if q_upper.startswith("SELECT") or q_upper.startswith("WITH"):
            rows = [dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]
            columns = [col[0] for col in cur.description]
            return jsonify({"columns": columns, "rows": rows})
        else:
            conn.commit()
            return jsonify({"message": "Query executed", "rows_affected": cur.rowcount})

    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    ensure_users_table()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
