# File: backend/logger.py

import sqlite3
from datetime import datetime, timezone
import os
from uuid import uuid4
import hashlib
import uuid
import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("metatron")

# Create logs directory if not exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "metatron.db")

# Init DB
conn = sqlite3.connect(log_path)
c = conn.cursor()

# -------------------- NEW: Goals Table --------------------
c.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        goal_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT,
        updated_at TEXT
    )
''')

# Table: users
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        password_hash TEXT,
        first_name TEXT,
        last_name TEXT,
        age_group TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Table: chat logs
c.execute('''
    CREATE TABLE IF NOT EXISTS logs (
            timestamp TEXT,
            goal_id TEXT,
            user_id TEXT,
            question TEXT,
            response TEXT
    )
''')

# Table: uploads
c.execute('''
    CREATE TABLE IF NOT EXISTS uploads (
        timestamp TEXT,
        session_id TEXT,
        filename TEXT
    )
''')

# Table: coaching goals metadata
c.execute('''
    CREATE TABLE IF NOT EXISTS kb_meta (
        id TEXT PRIMARY KEY,
        organization_id TEXT,
        team_leader_id TEXT,
        user_id TEXT,
        goal_id TEXT,  
        kb_name TEXT,
        intent TEXT,
        timeframe_type TEXT,
        timeframe_value TEXT,
        goal_description TEXT,
        created_at TEXT,
        last_accessed_at TEXT
    )
''')

# 🛡️ Ensure goal_id column exists (for old DBs)
try:
    c.execute("ALTER TABLE kb_meta ADD COLUMN goal_id TEXT")
except sqlite3.OperationalError:
    pass  # Already exists

conn.commit()
conn.close()

# -------------------- USERS --------------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, first_name, last_name, age_group):
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    c.execute("""
        INSERT INTO users (user_id, email, password_hash, first_name, last_name, age_group)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, email, password_hash, first_name, last_name, age_group))
    conn.commit()
    conn.close()
    return user_id  # ✅ Return it

def user_exists(email):
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    conn.close()
    return result is not None

def validate_login(email, password):
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == hash_password(password)

def get_user_profile(user_id):
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    c.execute("SELECT user_id, email, first_name, last_name, age_group, role FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "email": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "age_group": row[4],
            "role": row[5]
        }
    return None

def get_user_id_by_email(email):
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


# -------------------- LOGGING --------------------

def log_chat(goal_id, user_id, question, answer):
    timestamp = datetime.utcnow().isoformat()
    conn = sqlite3.connect(log_path)  # ✅ This uses metatron.db
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs (timestamp, goal_id, user_id, question, response) VALUES (?, ?, ?, ?, ?)",
        (timestamp, goal_id, user_id, question, answer)
    )
    conn.commit()
    conn.close()



def log_uploaded_files(session_id, filenames):
    timestamp = datetime.utcnow().isoformat()
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    for fname in filenames:
        c.execute(
            "INSERT INTO uploads VALUES (?, ?, ?)",
            (timestamp, session_id, fname)
        )
    conn.commit()
    conn.close()

def save_kb_metadata(goal_id, org_id, team_leader_id, user_id, kb_name, intent, timeframe_type, timeframe_value, goal_description, model="Open Source"):
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    record_id = str(uuid4())         # 🔧 original 'id' used for DB record
    now = datetime.utcnow().isoformat()

    c.execute('''
        INSERT INTO kb_meta (
            id, organization_id, team_leader_id, user_id, goal_id, kb_name,
            intent, timeframe_type, timeframe_value, goal_description,
            model, created_at, last_accessed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record_id, org_id, team_leader_id, user_id, goal_id, kb_name,
        intent, timeframe_type, timeframe_value, goal_description,
        model, now, now
    ))

    conn.commit()
    conn.close()
    return goal_id  # ✅ Return goal_id for frontend use

def get_kb_metadata(user_id, kb_name):
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    c.execute('''
        SELECT intent, timeframe_type, timeframe_value, goal_description
        FROM kb_meta
        WHERE user_id = ? AND kb_name = ?
        ORDER BY last_accessed_at DESC
        LIMIT 1
    ''', (user_id, kb_name))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'intent': row[0],
            'timeframe_type': row[1],
            'timeframe_value': row[2],
            'goal_description': row[3],
            "user_id": row[4]
        }
    return None

# -------------------- ERROR LOGGING --------------------

def log_error(context, error_msg):
    """
    Appends an error message to logs/error.log with timestamp and context.
    """
    os.makedirs("logs", exist_ok=True)
    with open("logs/error.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.utcnow().isoformat()}] [{context}] {error_msg}\n")

def log_file_diff(goal_id, added, removed):
    print(f"📋 File diff for {goal_id} — Added: {added}, Removed: {removed}")


