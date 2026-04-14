import asyncio
import asyncpg
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def check():
    url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(url)
    
    code = "1232"
    now = datetime.now()
    
    # Same query as get_video_by_code
    rows = await conn.fetch('''
        SELECT title, quality, file_id, views_count, id, file_type, storage_channel_id, storage_message_id FROM videos 
        WHERE code = $1 AND (expires_at IS NULL OR expires_at > $2)
    ''', code, now)
    
    print(f"get_video_by_code('{code}'): found {len(rows)} results")
    for r in rows:
        print(f"  Title: {r['title'][:40]}...")
    
    await conn.close()

asyncio.run(check())
