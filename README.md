# DokaBot — Докабот Технолицея

Telegram-бот с веб-интерфейсом для управления документами школы и AI-ассистентом на базе Yandex GPT.

## Архитектура

Проект состоит из двух компонентов:

1. **Django веб-приложение** — регистрация школ, загрузка документов, управление файлами
2. **Telegram бот** (aiogram) — AI-ассистент, отвечающий на вопросы по загруженным документам

## Установка

### 1. Зависимости

```bash
pip install -r requirements.txt
```

### 2. Настройка окружения

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

Обязательные переменные:
- `BOT_TOKEN` — токен Telegram бота (от @BotFather)
- `YANDEX_API_KEY` — API ключ Yandex Cloud
- `YANDEX_FOLDER_ID` — ID проекта/папки Yandex Cloud
- `VECTOR_STORE_ID` — ID vector store для поиска по документам
- `SECRET_KEY` — секретный ключ Django

### 3. Миграции

```bash
python manage.py migrate
```

### 4. Запуск Django

```bash
python manage.py runserver
```

Веб-интерфейс доступен по адресу: http://127.0.0.1:8000/

### 5. Запуск Telegram бота

**Режим polling (локальная разработка):**
```bash
cd DokaBot/app && python Bottechno.py
```

**Режим webhook (продакшен):**
```bash
cd DokaBot/app && python app.py
```

## Функционал бота

- **Текстовый режим** — бот отвечает только текстом
- **Текст + Голос** — бот дублирует ответ голосом (Yandex SpeechKit TTS)
- **Rate limiting** — ограничение на частоту запросов (2 сек между вопросами)
- **Логирование** — все вопросы и ответы сохраняются в SQLite

## Функционал веб-интерфейса

- Регистрация школы
- Загрузка документов (PDF, TXT, DOCX и др.)
- Автоматическая синхронизация с Yandex Vector Store
- Удаление документов (из сайта и из датасета)

## Тесты

```bash
python manage.py test web_app
```

## Структура проекта

```
├── config/                 # Настройки Django
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── web_app/                # Django приложение
│   ├── models.py           # Модель Document
│   ├── views.py            # Представления
│   ├── services.py         # Интеграция с vector store
│   └── ...
├── DokaBot/app/            # Telegram бот
│   ├── Bottechno.py        # Основная логика бота
│   ├── app.py              # Webhook сервер (aiohttp)
│   └── cleanup.py          # Утилита для сброса вебхука
├── templates/              # HTML шаблоны
├── vector_store.py         # Модуль для работы с Yandex Vector Store
├── requirements.txt
└── .env.example
```
