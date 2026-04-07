import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot
from aiogram.types import Update

from Bottechno import dp, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook_app")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_PATH = "/webhook"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN пустой")

bot = Bot(token=BOT_TOKEN)

async def on_startup(app: web.Application):
    await init_db()
    logger.info("Startup complete: DB initialized")

async def on_cleanup(app: web.Application):
    await bot.session.close()
    logger.info("Cleanup complete: bot session closed")

async def health(request: web.Request):
    return web.json_response({"ok": True})

# Хранилище активных задач для предотвращения их GC
_active_tasks: set = set()

async def telegram_webhook(request: web.Request):
    # Telegram присылает Update JSON
    data = await request.json()
    update = Update.model_validate(data)

    # Главное: сразу ответить 200 OK, а обработку сделать async
    task = asyncio.create_task(dp.feed_update(bot, update))
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)

    return web.Response(text="ok")

def main():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_post(WEBHOOK_PATH, telegram_webhook)

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    port = int(os.getenv("PORT", "8080"))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
