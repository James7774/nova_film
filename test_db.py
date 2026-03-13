import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def test():
    print(f"Connecting to {DATABASE_URL[:20]}...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected!")
        res = await conn.fetchval("SELECT 1")
        print(f"Query Result: {res}")
        await conn.close()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
