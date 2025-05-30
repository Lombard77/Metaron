import sqlite3
log_path = "logs/metatron.db"

def migrate_kbmeta_to_goals():
    print("🚚 Starting goals table migration...")

    conn = sqlite3.connect(log_path)
    c = conn.cursor()

    # Check for existing goals table
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='goals'")
    if not c.fetchone():
        print("❌ Goals table does not exist. Run schema creation first.")
        return

    # Get all distinct goals from kb_meta
    c.execute("SELECT DISTINCT goal_id, user_id, kb_name, created_at FROM kb_meta")
    rows = c.fetchall()

    inserted = 0
    for row in rows:
        goal_id, user_id, title, created_at = row
        updated_at = created_at  # We'll treat created = updated for now

        try:
            c.execute('''
                INSERT INTO goals (goal_id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (goal_id, user_id, title, created_at, updated_at))
            inserted += 1
        except sqlite3.IntegrityError:
            continue  # Goal already exists, skip

    conn.commit()
    conn.close()
    print(f"✅ Migration complete. Inserted {inserted} new goals.")
