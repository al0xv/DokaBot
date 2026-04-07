import os
import asyncio
from dotenv import load_dotenv
import openai

# Загружаем ключи из .env
load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()

async def upload_and_create_vector_store():
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        print("Ошибка: Убедитесь, что YANDEX_API_KEY и YANDEX_FOLDER_ID есть в .env")
        return

    # Инициализируем клиент
    client = openai.AsyncOpenAI(
        api_key=YANDEX_API_KEY,
        base_url="https://rest-assistant.api.cloud.yandex.net/v1",
        project=YANDEX_FOLDER_ID,
    )

    file_path = "docs.md"
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл {file_path} не найден!")
        return

    try:
        print("1. Загружаем файл на серверы Yandex Cloud...")
        with open(file_path, "rb") as f:
            uploaded_file = await client.files.create(
                file=f,
                purpose="assistants"
            )
        print(f"   ✓ Файл загружен. File ID: {uploaded_file.id}\n")

        print("2. Создаем облачное векторное хранилище (Search Index)...")
        # Убрали .beta. — обращаемся напрямую к vector_stores
        vector_store = await client.vector_stores.create(
            name="School Documents Base"
        )
        print(f"   ✓ Хранилище создано. Vector Store ID: {vector_store.id}\n")

        print("3. Индексируем файл...")
        # Убрали .beta. и здесь
        await client.vector_stores.files.create(
            vector_store_id=vector_store.id,
            file_id=uploaded_file.id
        )
        print("   ✓ Файл успешно привязан к хранилищу!\n")

        print("=" * 60)
        print("🎉 ГОТОВО! СКОПИРУЙТЕ ID НИЖЕ И ВСТАВЬТЕ В .ENV ФАЙЛ:")
        print(f"VECTOR_STORE_ID={vector_store.id}")
        print("=" * 60)

    except Exception as e:
        print(f"Произошла ошибка при обращении к Yandex API: {e}")

if __name__ == "__main__":
    asyncio.run(upload_and_create_vector_store())