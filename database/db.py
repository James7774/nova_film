import os
import asyncpg
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
logger = logging.getLogger(__name__)

# Global pool variable
pg_pool = None

async def get_pool():
    global pg_pool
    if pg_pool is None:
        try:
            pg_pool = await asyncpg.create_pool(DATABASE_URL)
            logger.info("✅ Database pool created successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to create database pool: {e}")
            raise
    return pg_pool

async def init_pg_db():
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL topilmadi!")
        return
        
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Create Tables for Neon (PostgreSQL)
        logger.info("🛠️ Neon.tech (PostgreSQL) jadvallari yaratilmoqda...")
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE,
                username TEXT,
                language TEXT DEFAULT 'uz',
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                daily_requests INTEGER DEFAULT 0,
                last_request_date DATE,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                id SERIAL PRIMARY KEY,
                title TEXT,
                url TEXT,
                channel_id TEXT UNIQUE
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id SERIAL PRIMARY KEY,
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
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                video_id INTEGER,
                user_id BIGINT,
                rating INTEGER,
                UNIQUE(video_id, user_id)
            )
        ''')
        # Migration: Ensure user_id is BIGINT if table already exists
        try:
            await conn.execute('ALTER TABLE ratings ALTER COLUMN user_id TYPE BIGINT')
        except Exception:
            pass
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS broadcast_messages (
                id SERIAL PRIMARY KEY,
                broadcast_id TEXT,
                user_id BIGINT,
                message_id INTEGER
            )
        ''')
        
        logger.info("✅ Jadvallar tayyor.")
        
        # Auto-populate channels from config if empty
        from config import CHANNELS
        exists = await conn.fetchval("SELECT COUNT(*) FROM channels")
        if exists == 0 and CHANNELS:
            logger.info("🚚 Config-dagi kanallarni bazaga ko'chirilmoqda...")
            for ch in CHANNELS:
                url = f"https://t.me/{ch.strip('@')}"
                await conn.execute('INSERT INTO channels (title, url, channel_id) VALUES ($1, $2, $3)', f"Kanal {ch}", url, ch)
        
        # Check if there's any data
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        videos_count = await conn.fetchval("SELECT COUNT(*) FROM videos")
        logger.info(f"📊 Hozirgi holat: {users_count} foydalanuvchi, {videos_count} video.")

async def add_user(telegram_id, username):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO users (telegram_id, username) VALUES ($1, $2) ON CONFLICT (telegram_id) DO NOTHING', telegram_id, username)

async def set_user_language(telegram_id, lang):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET language = $1 WHERE telegram_id = $2', lang, telegram_id)

async def get_user_language(telegram_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT language FROM users WHERE telegram_id = $1', telegram_id)
        return row['language'] if row else 'uz'

async def get_user_stats(telegram_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT daily_requests, last_request_date FROM users WHERE telegram_id = $1', telegram_id)
        if row:
            return row['daily_requests'], row['last_request_date']
        return None

async def update_user_requests(telegram_id, count, date_obj):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET daily_requests = $1, last_request_date = $2 WHERE telegram_id = $3', count, date_obj, telegram_id)

async def add_video(code, title, quality, file_id, file_type='video', expires_at=None, storage_channel_id=None, storage_message_id=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO videos (code, title, quality, file_id, file_type, expires_at, storage_channel_id, storage_message_id) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''', code, title, quality, file_id, file_type, expires_at, storage_channel_id, storage_message_id)

async def check_code_exists(code):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchval('SELECT id FROM videos WHERE code = $1 LIMIT 1', code)
        return row is not None

async def get_video_by_code(code):
    pool = await get_pool()
    async with pool.acquire() as conn:
        now = datetime.now()
        rows = await conn.fetch('''
            SELECT title, quality, file_id, views_count, id, file_type, storage_channel_id, storage_message_id FROM videos 
            WHERE code = $1 AND (expires_at IS NULL OR expires_at > $2)
        ''', code, now)
        return [tuple(row) for row in rows]

async def increment_views(video_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE videos SET views_count = views_count + 1 WHERE id = $1', video_id)

async def delete_code(code):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM videos WHERE code = $1', code)

async def get_all_codes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT DISTINCT code, title FROM videos')
        return [tuple(row) for row in rows]

async def search_videos_by_title(query):
    pool = await get_pool()
    async with pool.acquire() as conn:
        now = datetime.now()
        rows = await conn.fetch('''
            SELECT DISTINCT code, title FROM videos 
            WHERE title ILIKE $1 AND (expires_at IS NULL OR expires_at > $2)
        ''', f'%{query}%', now)
        return [tuple(row) for row in rows]

async def get_video_by_id(video_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT file_id, quality, title, views_count, file_type, storage_channel_id, storage_message_id FROM videos WHERE id = $1', video_id)
        return tuple(row) if row else None

async def touch_user(telegram_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE telegram_id = $1', telegram_id)

async def get_global_stats():
    pool = await get_pool()
    async with pool.acquire() as conn:
        total_users = await conn.fetchval('SELECT COUNT(*) FROM users')
        # Active in last 30 days
        active_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE last_seen > CURRENT_TIMESTAMP - INTERVAL '30 days'")
        total_videos = await conn.fetchval('SELECT COUNT(*) FROM videos')
        return total_users, active_users, total_videos

async def add_rating(video_id, user_id, rating):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO ratings (video_id, user_id, rating)
            VALUES ($1, $2, $3)
            ON CONFLICT (video_id, user_id) DO UPDATE SET rating = EXCLUDED.rating
        ''', video_id, user_id, rating)

async def get_rating_stats(video_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT AVG(rating) as avg, COUNT(rating) as count FROM ratings WHERE video_id = $1
        ''', video_id)
        if row and row['count'] > 0:
            return round(float(row['avg']), 1), row['count']
        return 0, 0

async def get_all_users():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT telegram_id FROM users')
        return [row['telegram_id'] for row in rows]

async def get_all_channels():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT id, title, url, channel_id FROM channels')
        return [dict(row) for row in rows]

async def add_channel(title, url, channel_id=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO channels (title, url, channel_id) VALUES ($1, $2, $3) ON CONFLICT (channel_id) DO UPDATE SET title = EXCLUDED.title, url = EXCLUDED.url', title, url, channel_id)

async def delete_channel(channel_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM channels WHERE id = $1', channel_id)

async def update_channel_title(db_id, new_title):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE channels SET title = $1 WHERE id = $2', new_title, db_id)

async def save_broadcast_message(broadcast_id, user_id, message_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO broadcast_messages (broadcast_id, user_id, message_id) VALUES ($1, $2, $3)', broadcast_id, int(user_id), message_id)

async def get_broadcast_messages(broadcast_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT user_id, message_id FROM broadcast_messages WHERE broadcast_id = $1', broadcast_id)
        return [tuple(row) for row in rows]

async def init_db():
    await init_pg_db()

async def close_db():
    global pg_pool
    if pg_pool:
        await pg_pool.close()
        logger.info("✅ Database pool closed.")

if __name__ == "__main__":
    asyncio.run(init_db())

