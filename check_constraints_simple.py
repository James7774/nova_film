import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def test():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'ratings'::regclass")
    for r in rows:
        print(f"DEF: {r[0]}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test())
