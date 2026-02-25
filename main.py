import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers.user import user_router
from handlers.admin import admin_router
from database.db import init_db

from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def handle_health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    # Initialize database
    await init_db()
    
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Include routers
    dp.include_router(admin_router)
    dp.include_router(user_router)
    # Start web server for Render health check (wrapped in try-except to avoid crash on local runs)
    try:
        app = web.Application()
        app.router.add_get("/", handle_health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.getenv("PORT", 8080))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Health check server started on port {port}")
    except Exception as e:
        logger.warning(f"Could not start health check server: {e}. If you are running locally, this is normal.")

    # Start polling
    logger.info(f"Bot started! Health check server on port {os.getenv('PORT', 8080)}")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")

