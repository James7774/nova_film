import sqlite3
import os

DATABASE_NAME = "bot_database.db"

def migrate():
    if not os.path.exists(DATABASE_NAME):
        print(f"{DATABASE_NAME} not found.")
        return

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Check videos table columns
    cursor.execute("PRAGMA table_info(videos)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'file_type' not in columns:
        print("Adding 'file_type' column to 'videos' table...")
        cursor.execute("ALTER TABLE videos ADD COLUMN file_type TEXT DEFAULT 'video'")
    
    if 'expires_at' not in columns:
        print("Adding 'expires_at' column to 'videos' table...")
        cursor.execute("ALTER TABLE videos ADD COLUMN expires_at TIMESTAMP")

    if 'storage_channel_id' not in columns:
        print("Adding 'storage_channel_id' column to 'videos' table...")
        cursor.execute("ALTER TABLE videos ADD COLUMN storage_channel_id TEXT")

    if 'storage_message_id' not in columns:
        print("Adding 'storage_message_id' column to 'videos' table...")
        cursor.execute("ALTER TABLE videos ADD COLUMN storage_message_id INTEGER")

    # Check users table columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'language' not in columns:
        print("Adding 'language' column to 'users' table...")
        cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'uz'")
        
    if 'daily_requests' not in columns:
        print("Adding 'daily_requests' column to 'users' table...")
        cursor.execute("ALTER TABLE users ADD COLUMN daily_requests INTEGER DEFAULT 0")

    if 'last_request_date' not in columns:
        print("Adding 'last_request_date' column to 'users' table...")
        cursor.execute("ALTER TABLE users ADD COLUMN last_request_date DATE")

    # Ratings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER,
            user_id INTEGER,
            rating INTEGER,
            UNIQUE(video_id, user_id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
