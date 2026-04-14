import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def test():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT id, code, title FROM videos LIMIT 5")
    for r in rows:
        print(f"ID: {r['id']}, Code: {r['code']}, Title: {r['title'][:30]}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test())
