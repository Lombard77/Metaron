import sqlite3

# Path to your SQLite DB
DB_PATH = "backend/logs/metatron.db"  # <-- update to your actual DB path

def introspect_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for (table_name,) in tables:
        print(f"\n🔹 Table: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print("| Column Name | Type | Nullable |")
        print("|-------------|------|----------|")
        for col in columns:
            name = col[1]
            col_type = col[2]
            notnull = "NO" if col[3] else "YES"
            print(f"| {name:<11} | {col_type:<4} | {notnull:<8} |")

    conn.close()

if __name__ == "__main__":
    introspect_schema()
