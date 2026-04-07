import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from contextlib import suppress
from pathlib import Path

import httpx  # Для запросов к SpeechKit
import aiosqlite
from dotenv import load_dotenv
import openai

from aiogram import Dispatcher, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile

# Добавляем корень проекта в sys.path для импорта vector_store
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from vector_store import (
    get_async_client,
    get_bot_token,
    has_remote_vector_store_config,
    list_local_dataset_files,
)

load_dotenv()

# --- ENV ---
BOT_TOKEN = get_bot_token()
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()
YANDEX_ASSISTANT_MODEL = os.getenv("YANDEX_ASSISTANT_MODEL", "yandexgpt").strip()
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "").strip()
DB_PATH = os.getenv("DB_PATH", "/tmp/school_bot.sqlite3").strip()

USE_REMOTE_VECTOR_STORE = has_remote_vector_store_config()

# Хранилище настроек пользователей (в продакшне лучше перенести в БД)
# По умолчанию ставим "Текст"
user_preferences = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dokabot")

# --- Клавиатура выбора режима ---
def get_main_kb():
    buttons = [
        [KeyboardButton(text="📝 Только текст"), KeyboardButton(text="🎙 Текст + Голос")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- Yandex SpeechKit TTS ---
async def synthesize_speech(text: str) -> bytes:
    """Конвертирует текст в аудио (OggOpus) через Yandex SpeechKit"""
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}"}
    
    # Убираем Markdown разметку из текста для лучшего звучания
    clean_text = text.replace("*", "").replace("#", "").replace("`", "")
    
    data = {
        "text": clean_text,
        "lang": "ru-RU",
        "voice": "marina", # Можно выбрать: marina, alexander, madirus
        "folderId": YANDEX_FOLDER_ID,
        "format": "oggopus"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, data=data, timeout=15.0)
        if resp.status_code == 200:
            return resp.content
        else:
            logger.error(f"SpeechKit Error: {resp.status_code} - {resp.text}")
            return b""

# --- База данных ---
SCHEMA_SQL = """
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
            (user_id, q, a, datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()

# --- AI Ассистент ---
_ASSISTANT_CLIENT: Optional[openai.AsyncOpenAI] = None

def get_assistant_client() -> openai.AsyncOpenAI:
    global _ASSISTANT_CLIENT
    if _ASSISTANT_CLIENT is None:
        _ASSISTANT_CLIENT = get_async_client()
    return _ASSISTANT_CLIENT


def build_local_stub_response(question: str) -> str:
    files = list_local_dataset_files()
    if not files:
        return (
            "Локальный датасет пока пуст. Загрузите документы через веб-интерфейс, "
            "и бот начнет видеть их в stub-режиме."
        )

    visible_files = [path.relative_to(ROOT_DIR) for path in files[:8]]
    files_list = "\n".join(f"- {path.as_posix()}" for path in visible_files)
    return (
        "Yandex API не настроен, поэтому бот работает в локальном stub-режиме.\n\n"
        f"Ваш вопрос: {question}\n\n"
        "Сейчас в локальном датасете есть файлы:\n"
        f"{files_list}\n\n"
        "Документы сохраняются локально по имени пользователя. "
        "Поиск по содержимому пока заменен заглушкой."
    )


ASSISTANT_INSTRUCTIONS = (
    "Вы - администратор школы. Вам предоставлены документы, в которых находится информация о школе."
    " Чтобы ответить на вопрос бери информацию из предоставленных тебе документов,"
    " а также обязателно делай поиск информации в интернете и совмещай ответ из интернета с ответом из индекса."
    " Делай поиск по всему индексу целиком. Всегда приводи цитаты и точные названия документов откуда берешь информацию."
    " Запомни, что директора Технолицея зовут Сизинцева Екатерина Петровна."
    " Курить в Технолицее СТРОГО ЗАПРЕЩЕНО, как и распивать алкоголь."
)


async def call_ai(question: str) -> str:
    if not USE_REMOTE_VECTOR_STORE:
        return build_local_stub_response(question)

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

# --- Обработчики ---
dp = Dispatcher()

WELCOME_TEXT = (
    "Привет! Я **Докабот Технолицея** 🤖\n\n"
    "Задавай любой вопрос про Технолицей и документы — я отвечу по базе.\n"
    "Выберите, как мне отвечать:"
)

if not USE_REMOTE_VECTOR_STORE:
    WELCOME_TEXT += "\n\n⚠️ Сейчас включен локальный stub-режим без Yandex API."

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_kb(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "📝 Только текст")
async def set_text_mode(message: Message):
    user_preferences[message.from_user.id] = "text"
    await message.answer("Режим изменен: присылаю только текст.")

@dp.message(F.text == "🎙 Текст + Голос")
async def set_voice_mode(message: Message):
    user_preferences[message.from_user.id] = "voice"
    await message.answer("Режим изменен: буду дублировать ответы голосом.")

# --- Rate limit ---
_last_call: dict[int, datetime] = {}
MIN_INTERVAL = timedelta(seconds=2)

def rate_limited(user_id: int) -> bool:
    now = datetime.now(timezone.utc)
    last = _last_call.get(user_id)
    if last and now - last < MIN_INTERVAL:
        return True
    _last_call[user_id] = now
    return False


@dp.message(F.text)
async def handle_question(message: Message):
    q = message.text.strip()
    if not q or q in ["📝 Только текст", "🎙 Текст + Голос"]:
        return

    if rate_limited(message.from_user.id):
        await message.answer("Подожди пару секунд перед следующим вопросом 🙂")
        return

    thinking_msg = await message.answer("Думаю…")

    try:
        answer = await call_ai(q)
        await db_log_qa(message.from_user.id, q, answer)

        # 1. Отправляем текст (всегда)
        display_text = answer[:3800] + "\n\n…" if len(answer) > 3800 else answer
        await message.answer(display_text)

        # 2. Если включен режим голоса — синтезируем и отправляем
        if user_preferences.get(message.from_user.id) == "voice":
            voice_data = await synthesize_speech(answer[:1000]) # Ограничим длину для TTS
            if voice_data:
                voice_file = BufferedInputFile(voice_data, filename="answer.ogg")
                await message.answer_voice(voice_file)

    except BaseException as exc:
        if isinstance(exc, asyncio.CancelledError):
            raise
        logger.exception("AI/TTS error")
        await message.answer("Произошла ошибка. Попробуйте позже.")
    finally:
        with suppress(Exception):
            await thinking_msg.delete()

async def _local_main():
    bot = Bot(token=BOT_TOKEN)
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(_local_main())