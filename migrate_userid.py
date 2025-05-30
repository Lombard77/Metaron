import sqlite3

conn = sqlite3.connect("backend/logs/metatron.db")  # Make sure this is the correct file
c = conn.cursor()

# 1. Build the email → user_id map from users
c.execute("SELECT email, user_id FROM users")
user_map = dict(c.fetchall())

# 2. Update user_id in goals table
for email, user_id in user_map.items():
    print(f"🔁 Updating goals: {email} → {user_id}")
    c.execute("UPDATE goals SET user_id = ? WHERE user_id = ?", (user_id, email))

conn.commit()
conn.close()
print("✅ goals.user_id updated.")
