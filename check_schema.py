import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def test():
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'ratings' AND column_name = 'user_id'
    """)
    print(f"Table 'ratings' column 'user_id' type: {row['data_type'] if row else 'NOT FOUND'}")
    
    # Try the migration again explicitly
    try:
        print("Attempting migration...")
        await conn.execute('ALTER TABLE ratings ALTER COLUMN user_id TYPE BIGINT')
        print("Migration successful!")
    except Exception as e:
        print(f"Migration error: {e}")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test())
