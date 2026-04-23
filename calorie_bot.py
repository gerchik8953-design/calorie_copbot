import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from mistralai import Mistral
from PIL import Image
import io
import base64

# --- НАСТРОЙКА ---
TELEGRAM_TOKEN = "8782272205:AAHoB4B6oHFa996lqDtRt5Lgt2Fm_ByAcsM"
MISTRAL_API_KEY = "pjWEoYsJgGKwyga1mp2Hb0UKBjT4ZXLs"  # ← ВСТАВЬТЕ СВОЙ КЛЮЧ

# Файл для хранения ID пользователей
USER_FILE = "users.json"

# Настройка Mistral
client = Mistral(api_key=MISTRAL_API_KEY)

# Логирование
logging.basicConfig(level=logging.INFO)

# --- СЧЁТЧИК ПОЛЬЗОВАТЕЛЕЙ ---
def load_users():
    if not os.path.exists(USER_FILE):
        return []
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

# --- ФУНКЦИЯ ЗАПРОСА К MISTRAL (С АНАЛИЗОМ ИЗОБРАЖЕНИЯ) ---
def ask_mistral(prompt, image_bytes):
    # Кодируем изображение в base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Отправляем запрос к Mistral (модель Pixtral 12B для работы с изображениями)
    response = client.chat.complete(
        model="pixtral-12b-2409",  # ← модель Mistral для работы с изображениями
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image_base64}"
                    }
                ]
            }
        ]
    )
    
    return response.choices[0].message.content

# --- ОБРАБОТЧИКИ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    await update.message.reply_text(
        "👋 Привет! Я **Calorie Copbot** — бот-диетолог (на Mistral AI).\n"
        "Отправь мне фото еды, и я посчитаю калории и БЖУ.\n\n"
        "📌 *Важно:* положи рядом с блюдом **вилку** — так мне проще понять масштаб.\n\n"
        "Команда /stats — сколько людей пользуются ботом.",
        parse_mode='Markdown'
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    count = len(users)
    await update.message.reply_text(f"📊 Ботом воспользовались {count} уникальных пользователей.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    
    await update.message.chat.send_action(action="typing")
    
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    prompt = (
        "Ты — диетолог. На фото — блюдо. Рядом с ним лежит вилка — используй её для оценки размера порции. "
        "Ответь строго в формате:\n"
        "🍽 Блюдо: [название]\n"
        "⚖️ Вес: [г]\n"
        "🔥 Калории: [ккал]\n"
        "🥩 Белки: [г]\n"
        "🧈 Жиры: [г]\n"
        "🍚 Углеводы: [г]\n"
        "💡 Совет: [один короткий совет]"
    )
    
    response_text = ask_mistral(prompt, photo_bytes)
    await update.message.reply_text(response_text)

# --- ЗАПУСК ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ Бот Calorie Copbot (Mistral AI) запущен и работает 24/7")
    app.run_polling()

if __name__ == "__main__":
    main()
