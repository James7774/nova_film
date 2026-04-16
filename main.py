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

async def handle_get_movies(request):
    from database.db import get_all_codes
    movies = await get_all_codes() # returns list of (code, title)
    data = [{"code": m[0], "title": m[1]} for m in movies]
    return web.json_response(data)

async def handle_is_admin(request):
    from config import ADMINS
    user_id = request.query.get('id')
    if not user_id:
        return web.json_response({"is_admin": False})
    try:
        is_admin = int(user_id) in ADMINS
    except:
        is_admin = False
    return web.json_response({"is_admin": is_admin})

async def handle_add_movie(request):
    from database.db import add_video, check_code_exists
    from config import ADMINS
    data = await request.json()
    admin_id = data.get('admin_id')
    if not admin_id or int(admin_id) not in ADMINS:
        return web.json_response({"success": False, "error": "Unauthorized"}, status=403)
    
    code = data.get('code')
    title = data.get('title')
    
    if not code or not title:
        return web.json_response({"success": False, "error": "Missing data"}, status=400)
    
    if await check_code_exists(code):
        return web.json_response({"success": False, "error": "Code already exists"}, status=400)
    
    await add_video(code=code, title=title, quality="HD", file_id=None)
    return web.json_response({"success": True})

async def handle_delete_movie(request):
    from database.db import delete_code
    from config import ADMINS
    data = await request.json()
    admin_id = data.get('admin_id')
    if not admin_id or int(admin_id) not in ADMINS:
        return web.json_response({"success": False, "error": "Unauthorized"}, status=403)
    
    code = data.get('code')
    if not code:
        return web.json_response({"success": False, "error": "Missing code"}, status=400)
    
    await delete_code(code)
    return web.json_response({"success": True})

async def handle_get_stats(request):
    from database.db import get_global_stats
    from config import ADMINS
    admin_id = request.query.get('id')
    if not admin_id or int(admin_id) not in ADMINS:
        return web.json_response({"success": False, "error": "Unauthorized"}, status=403)
    
    total_users, active_users, total_videos = await get_global_stats()
    return web.json_response({
        "total_users": total_users,
        "active_users": active_users,
        "total_videos": total_videos
    })

async def handle_webapp(request):
    with open("webapp/index.html", "r", encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="text/html")

async def main():
    # Initialize database
    await init_db()
    
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Set Menu Button (Web App)
    from aiogram.types import WebAppInfo, MenuButtonWebApp
    webapp_url = os.getenv("WEBAPP_URL", "https://vaqtinchalik-url.uz") # Replace with your real URL
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Kino kodlari", web_app=WebAppInfo(url=webapp_url))
        )
        logger.info(f"✅ Menu button set to: {webapp_url}")
    except Exception as e:
        logger.error(f"❌ Could not set menu button: {e}")
    
    # Register middleware
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    
    # Include routers
    dp.include_router(admin_router)
    dp.include_router(user_router)
    # Start web server
    try:
        app = web.Application()
        app.router.add_get("/", handle_webapp)
        app.router.add_get("/health", handle_health_check)
        app.router.add_get("/api/movies", handle_get_movies)
        app.router.add_get("/api/is_admin", handle_is_admin)
        app.router.add_post("/api/add_movie", handle_add_movie)
        app.router.add_post("/api/delete_movie", handle_delete_movie)
        app.router.add_get("/api/stats", handle_get_stats)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.getenv("PORT", 8080))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Health check server started on port {port}")
    except Exception as e:
        logger.warning(f"Could not start health check server: {e}. If you are running locally, this is normal.")

    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
