import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from contextlib import suppress

import aiosqlite
from dotenv import load_dotenv
import openai

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

load_dotenv()

# -----------------------------
# ENV
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Yandex Rest Assistant (OpenAI-compatible)
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()
YANDEX_ASSISTANT_MODEL = os.getenv("YANDEX_ASSISTANT_MODEL", "yandexgpt").strip()
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "").strip()

# В serverless обычно нужно /tmp
DB_PATH = os.getenv("DB_PATH", "/tmp/school_bot.sqlite3").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN пустой (env var BOT_TOKEN не задан)")
if not YANDEX_API_KEY:
    raise RuntimeError("YANDEX_API_KEY пустой (env var YANDEX_API_KEY не задан)")
if not YANDEX_FOLDER_ID:
    raise RuntimeError("YANDEX_FOLDER_ID пустой (env var YANDEX_FOLDER_ID не задан)")
if not VECTOR_STORE_ID:
    raise RuntimeError("VECTOR_STORE_ID пустой (env var VECTOR_STORE_ID не задан)")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dokabot")

# -----------------------------
# DB (лог вопросов/ответов)
# -----------------------------
SCHEMA_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS qa_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()

async def db_log_qa(user_id: int, q: str, a: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO qa_logs(user_id, question, answer, created_at) VALUES(?, ?, ?, ?)",
            (user_id, q, a, datetime.utcnow().isoformat()),
        )
        await db.commit()

# -----------------------------
# Yandex Rest Assistant (Async)
# -----------------------------
_ASSISTANT_CLIENT: Optional[openai.AsyncOpenAI] = None

ASSISTANT_INSTRUCTIONS = (
    "Вы - администратор школы. Вам предоставлены документы, в которых находится информация о школе."
    " Чтобы ответить на вопрос бери информацию из предоставленных тебе документов,"
    " а также обязателно делай поиск информации в интернете и совмещай ответ из интернета с ответом из индекса."
    " Делай поиск по всему индексу целиком. Всегда приводи цитаты и точные названия документов откуда берешь информацию."
    " Запомни, что директора Технолицея зовут Сизинцева Екатерина Петровна."
    " Курить в Технолицее СТРОГО ЗАПРЕЩЕНО, как и распивать алкоголь."
)

def get_assistant_client() -> openai.AsyncOpenAI:
    global _ASSISTANT_CLIENT
    if _ASSISTANT_CLIENT is None:
        _ASSISTANT_CLIENT = openai.AsyncOpenAI(
            api_key=YANDEX_API_KEY,
            base_url="https://rest-assistant.api.cloud.yandex.net/v1",
            project=YANDEX_FOLDER_ID,
        )
    return _ASSISTANT_CLIENT

async def call_ai(question: str) -> str:
    client = get_assistant_client()

    resp = await client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_ASSISTANT_MODEL}",
        instructions=ASSISTANT_INSTRUCTIONS,
        tools=[{
            "type": "file_search",
            "vector_store_ids": [VECTOR_STORE_ID],
        }],
        input=question,
    )

    text = (getattr(resp, "output_text", "") or "").strip()
    return text if text else "ИИ не смог сформировать ответ."

# -----------------------------
# Rate limit
# -----------------------------
_last_call: dict[int, datetime] = {}
MIN_INTERVAL = timedelta(seconds=2)

def rate_limited(user_id: int) -> bool:
    now = datetime.utcnow()
    last = _last_call.get(user_id)
    if last and now - last < MIN_INTERVAL:
        return True
    _last_call[user_id] = now
    return False

# -----------------------------
# Dispatcher (bot создаётся в app.py)
# -----------------------------
dp = Dispatcher()

WELCOME_TEXT = (
    "Привет! Я **Докабот Технолицея** 🤖\n\n"
    "Задавай любой вопрос про Технолицей и документы — я отвечу по базе.\n"
    "Пример: «Что написано в уставе про ...?»"
)


# -----------------------------
# /start — приветствие (не обязательно)
# -----------------------------
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(WELCOME_TEXT, parse_mode="Markdown")

# -----------------------------
# Любое сообщение = вопрос ИИ
# + "Думаю..." (удаляется после ответа)
# -----------------------------
@dp.message(F.text)
async def handle_question(message: Message):
    q = (message.text or "").strip()
    if not q:
        return

    if rate_limited(message.from_user.id):
        await message.answer("Подожди пару секунд перед следующим вопросом 🙂")
        return

    thinking_msg = await message.answer("Думаю…")

    try:
        answer = await call_ai(q)
        await db_log_qa(message.from_user.id, q, answer)

        if len(answer) > 3800:
            answer = answer[:3800] + "\n\n…(ответ сокращён)"

        await message.answer(answer)

    except Exception:
        logger.exception("AI error")
        await message.answer("Ошибка при получении ответа от ИИ. Попробуй позже.")

    finally:
        with suppress(Exception):
            await thinking_msg.delete()

# -----------------------------
# Local run (polling) — только для локальной отладки!
# В облаке запускается app.py (webhook).
# -----------------------------
async def _local_main():
    from aiogram import Bot
    bot = Bot(token=BOT_TOKEN)
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(_local_main())
    except KeyboardInterrupt:
        pass