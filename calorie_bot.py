import os
import json
import logging
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import io
import base64

# --- НАСТРОЙКА ---
TELEGRAM_TOKEN = "8782272205:AAHoB4B6oHFa996lqDtRt5Lgt2Fm_ByAcsM"
MISTRAL_API_KEY = "pjWEoYsJgGKwyga1mp2Hb0UKBjT4ZXLs"

USER_FILE = "users.json"
logging.basicConfig(level=logging.INFO)

# --- HEALTH-СЕРВЕР ДЛЯ RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_health_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

# --- ФУНКЦИЯ ЗАПРОСА К MISTRAL ---
def ask_mistral(prompt, image_bytes):
    url = "https://api.mistral.ai/v1/chat/completions"
    
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "model": "pixtral-12b-2409",
        "messages": [
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
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        logging.error(f"Mistral API error: {response.status_code} - {response.text}")
        return "❌ Ошибка при анализе фото. Попробуйте ещё раз."
    
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return "❌ Не удалось распознать блюдо. Попробуйте другое фото."

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
        "💡 Совет: [два коротких совета]"
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
    # Запускаем health-сервер в фоновом потоке
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    # Запускаем основного бота
    main()
