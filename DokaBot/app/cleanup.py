import asyncio
from aiogram import Bot
import os
from dotenv import load_dotenv

load_dotenv()
async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    await bot.delete_webhook(drop_pending_updates=True)
    print("Готово! Вебхук удален, старые сообщения стерты.")
    await bot.session.close()

asyncio.run(main())