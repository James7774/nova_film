
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
admins = os.getenv("ADMINS", "").split(",")
print(f"Admins in .env: {admins}")

conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()
cursor.execute("SELECT telegram_id, username FROM users")
users = cursor.fetchall()
print("Registered users:")
for u in users:
    print(u)
conn.close()
