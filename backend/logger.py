# File: backend/logger.py

import sqlite3
from datetime import datetime
import os

# Create a folder to store the database if it doesn't exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Path to the SQLite database file
log_path = os.path.join(log_dir, "chat_logs.db")

# Create or connect to the database, and initialize tables
conn = sqlite3.connect(log_path)
c = conn.cursor()

# Table 1: Logs for chat questions and responses
c.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        timestamp TEXT,
        session_id TEXT,
        question TEXT,
        response TEXT
    )
''')

# Table 2: Logs for uploaded file names (helps track sources)
c.execute('''
    CREATE TABLE IF NOT EXISTS uploads (
        timestamp TEXT,
        session_id TEXT,
        filename TEXT
    )
''')

conn.commit()
conn.close()

# ---------------------
# Function: log_chat
# ---------------------
def log_chat(session_id, question, response):
    """
    Logs each user question and GPT response with timestamp.
    Useful for reviewing what was asked and answered.
    """
    timestamp = datetime.utcnow().isoformat()
    conn = sqlite3.connect(log_path)
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs VALUES (?, ?, ?, ?)",
        (timestamp, session_id, question, response)
    )
    conn.commit()
    conn.close()

# ---------------------
# Function: log_uploaded_files
# ---------------------
def log_uploaded_files(session_id, filenames):
    """
    Logs all filenames uploaded in a given session.
    Useful for tracking what sources each user interacted with.
    """
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
