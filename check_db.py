
import sqlite3
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()
cursor.execute("SELECT id, code, title FROM videos")
rows = cursor.fetchall()
print(f"Total videos: {len(rows)}")
for row in rows[:20]:
    print(row)
conn.close()
