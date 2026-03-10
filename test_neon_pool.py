import asyncio
import os
from database.db import init_db, get_all_codes, add_video, close_db
from dotenv import load_dotenv

load_dotenv()

async def test():
    print("Testing Neon Connection Pool...")
    try:
        await init_db()
        # Try to add a test movie
        await add_video("test_999", "Test Movie", "HD", "file_id_test")
        print("✅ Added test movie.")
        
        codes = await get_all_codes()
        print(f"✅ Current codes in Neon: {len(codes)}")
        
        # Cleanup test
        from database.db import delete_code
        await delete_code("test_999")
        print("✅ Cleanup successful.")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(test())
