import sqlite3
from datetime import datetime
import aiosqlite
from config import DATABASE_NAME

async def init_db():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                language TEXT DEFAULT 'uz',
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                daily_requests INTEGER DEFAULT 0,
                last_request_date DATE
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                title TEXT,
                quality TEXT,
                file_id TEXT,
                file_type TEXT DEFAULT 'video',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views_count INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                storage_channel_id TEXT,
                storage_message_id INTEGER
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER,
                user_id INTEGER,
                rating INTEGER,
                UNIQUE(video_id, user_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS broadcast_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id TEXT,
                user_id INTEGER,
                message_id INTEGER
            )
        ''')
        await db.commit()

async def add_user(telegram_id, username):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)', (telegram_id, username))
        await db.commit()

async def set_user_language(telegram_id, lang):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET language = ? WHERE telegram_id = ?', (lang, telegram_id))
        await db.commit()

async def get_user_language(telegram_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT language FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 'uz'

async def get_user_stats(telegram_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT daily_requests, last_request_date FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
            return await cursor.fetchone()

async def update_user_requests(telegram_id, count, date):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE users SET daily_requests = ?, last_request_date = ? WHERE telegram_id = ?', (count, date, telegram_id))
        await db.commit()

async def add_video(code, title, quality, file_id, file_type='video', expires_at=None, storage_channel_id=None, storage_message_id=None):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            INSERT INTO videos (code, title, quality, file_id, file_type, expires_at, storage_channel_id, storage_message_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (code, title, quality, file_id, file_type, expires_at, storage_channel_id, storage_message_id))
        await db.commit()

async def get_video_by_code(code):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        # Filter out expired videos
        now = datetime.now()
        async with db.execute('''
            SELECT title, quality, file_id, views_count, id, file_type, storage_channel_id, storage_message_id FROM videos 
            WHERE code = ? AND (expires_at IS NULL OR expires_at > ?)
        ''', (code, now)) as cursor:
            return await cursor.fetchall()

async def increment_views(video_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('UPDATE videos SET views_count = views_count + 1 WHERE id = ?', (video_id,))
        await db.commit()

async def delete_code(code):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('DELETE FROM videos WHERE code = ?', (code,))
        await db.commit()

async def get_all_codes():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT DISTINCT code, title FROM videos') as cursor:
            return await cursor.fetchall()

async def search_videos_by_title(query):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        now = datetime.now()
        async with db.execute('''
            SELECT DISTINCT code, title FROM videos 
            WHERE title LIKE ? AND (expires_at IS NULL OR expires_at > ?)
        ''', (f'%{query}%', now)) as cursor:
            return await cursor.fetchall()

async def get_video_by_id(video_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT file_id, quality, title, views_count, file_type, storage_channel_id, storage_message_id FROM videos WHERE id = ?', (video_id,)) as cursor:
            return await cursor.fetchone()

async def get_global_stats():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            total_users = (await cursor.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM videos') as cursor:
            total_videos = (await cursor.fetchone())[0]
        return total_users, total_videos

async def add_rating(video_id, user_id, rating):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            INSERT OR REPLACE INTO ratings (video_id, user_id, rating)
            VALUES (?, ?, ?)
        ''', (video_id, user_id, rating))
        await db.commit()

async def get_rating_stats(video_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('''
            SELECT AVG(rating), COUNT(rating) FROM ratings WHERE video_id = ?
        ''', (video_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[1] > 0:
                return round(row[0], 1), row[1]
            return 0, 0

async def get_all_users():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT telegram_id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def save_broadcast_message(broadcast_id, user_id, message_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('INSERT INTO broadcast_messages (broadcast_id, user_id, message_id) VALUES (?, ?, ?)', (broadcast_id, user_id, message_id))
        await db.commit()

async def get_broadcast_messages(broadcast_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        async with db.execute('SELECT user_id, message_id FROM broadcast_messages WHERE broadcast_id = ?', (broadcast_id,)) as cursor:
            return await cursor.fetchall()
