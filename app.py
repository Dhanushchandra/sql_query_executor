# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from psycopg2 import sql
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]
JWT_EXP_MINUTES = int(os.environ["JWT_EXP_MINUTES"])

app = Flask(__name__)
CORS(app)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# --- Authentication helpers ---
def create_token(user_id, username):
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXP_MINUTES)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # PyJWT >=2 returns str
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", None)
        if not auth:
            return jsonify({"error": "Authorization header missing"}), 401
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Authorization header must be: Bearer <token>"}), 401
        token = parts[1]
        try:
            payload = decode_token(token)
            # attach user info to request context
            request.user = {"id": payload.get("sub"), "username": payload.get("username")}
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


# --- Auth endpoints ---
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    hashed = generate_password_hash(password)

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s;", (username,))
        if cur.fetchone():
            return jsonify({"error": "username already exists"}), 400
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id;",
            (username, hashed)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"message": "user created", "user_id": user_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s;", (username,))
        user = cur.fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "invalid credentials"}), 401
        token = create_token(user["id"], user["username"])
        return jsonify({"access_token": token, "token_type": "bearer", "expires_in_minutes": JWT_EXP_MINUTES})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


# --- Protected DB endpoints (examples) ---
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/tables", methods=["GET"])
@token_required
def list_tables():
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [r["table_name"] for r in cur.fetchall()]
        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/table/<table_name>", methods=["GET"])
@token_required
def table_info(table_name):
    if not table_name.isidentifier():
        return jsonify({"error": "Invalid table name"}), 400
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s;
        """, (table_name,))
        columns = cur.fetchall()
        cur.execute(sql.SQL("SELECT * FROM {} LIMIT 5;").format(sql.Identifier(table_name)))
        # Note: psycopg2.sql.Identifier isn't used above to keep code straightforward.
        # We'll fetch rows via standard execute
        cur.execute(f"SELECT * FROM {table_name} LIMIT 5;")
        sample = cur.fetchall()
        return jsonify({"columns": columns, "sample": sample})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/execute", methods=["POST"])
@token_required
def execute():
    payload = request.get_json(force=True, silent=True)
    if not payload or "query" not in payload:
        return jsonify({"error": "Missing JSON body with 'query'"}), 400

    query = payload["query"]
    q_upper = query.strip().upper()

    forbidden = ["ATTACH", "DETACH", "PRAGMA writable_schema", "sqlite_schema", "sqlite_master"]
    if any(token in q_upper for token in forbidden):
        return jsonify({"error": "Forbidden operation in query"}), 403

    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query)
        if q_upper.startswith("SELECT") or q_upper.startswith("WITH"):
            rows = cur.fetchall()
            columns = [desc.name for desc in cur.description] if cur.description else []
            return jsonify({"columns": columns, "rows": rows})
        else:
            conn.commit()
            return jsonify({"message": "Query executed", "rows_affected": cur.rowcount})
    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    # debug mode reads .env via python-dotenv
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
