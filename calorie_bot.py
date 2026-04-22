import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from PIL import Image
import io

# --- НАСТРОЙКА ---
TELEGRAM_TOKEN = "8782272205:AAHoB4B6oHFa996lqDtRt5Lgt2Fm_ByAcsM"
GEMINI_API_KEY = "AIzaSyDHeZXF5-RUDwjqGpvu561K6jYFy1MlE24"

# Файл для хранения ID пользователей
USER_FILE = "users.json"

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

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

# --- ОБРАБОТЧИКИ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    await update.message.reply_text(
        "👋 Привет! Я **Calorie Copbot** — бот-диетолог.\n"
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
    image = Image.open(io.BytesIO(photo_bytes))
    
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
    
    response = model.generate_content([prompt, image])
    await update.message.reply_text(response.text)

# --- ЗАПУСК ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ Бот Calorie Copbot запущен и работает 24/7")
    app.run_polling()

if __name__ == "__main__":
    main()
