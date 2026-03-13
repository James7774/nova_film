import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def test():
    conn = await asyncpg.connect(DATABASE_URL)
    # Check constraints on ratings
    rows = await conn.fetch("""
        SELECT conname, pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE nspname = 'public' AND conrelid = 'ratings'::regclass;
    """)
    for r in rows:
        print(f"Constraint: {r[0]}, Def: {r[1]}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test())
