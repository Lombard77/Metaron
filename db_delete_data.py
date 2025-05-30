import sqlite3

db_path = "backend/logs/metatron.db"  # or metatron.db
tables = ["users", "goals", "kb_meta", "chat_log", "uploads"]  # Add any other tables here

conn = sqlite3.connect(db_path)
c = conn.cursor()

for table in tables:
    try:
        print(f"🧹 Clearing: {table}")
        c.execute(f"DELETE FROM {table}")
        # Optional: Reset AUTOINCREMENT counters (safe even if not used)
       # c.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Skipped {table} — {e}")

conn.commit()
conn.close()
print("✅ Done cleaning all tables that exist.")
