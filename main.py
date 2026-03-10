import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMINS
from handlers.user import user_router
from handlers.admin import admin_router
from database.db import init_db, close_db, touch_user

from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if hasattr(event, "from_user") and event.from_user:
            asyncio.create_task(touch_user(event.from_user.id))
        return await handler(event, data)

async def handle_health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    # Initialize database
    await init_db()
    
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register middleware
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    
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
    logger.info("🚀 Preparing to start polling...")
    try:
        me = await bot.get_me()
        logger.info(f"✅ Bot is authenticated as @{me.username}")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🧹 Pending updates cleared.")
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"❌ Critical error in polling: {e}")
    finally:
        logger.info("Polling stopped. Closing bot session and database connection...")
        await bot.session.close()
        await close_db()
        logger.info("Bot session and database connection closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
