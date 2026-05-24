import os
import urllib.parse
from telebot import TeleBot
from google import genai
from google.genai import types
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Настройки ключей из Render
TG_TOKEN = os.environ.get("TG_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

bot = TeleBot(TG_TOKEN)
ai_client = genai.Client(api_key=GEMINI_KEY)

print("Облачный ИИ-бот (с красивыми ошибками) запущен!")

# Функция для проверки и красивого вывода ошибок лимита
def handle_ai_error(message, exception):
    error_str = str(exception)
    # Если в ошибке есть коды 429 или слова про лимит/квоту
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "Quota exceeded" in error_str:
        bot.reply_to(message, "🛑 **Ой! Извини, но ты превысил бесплатный лимит запросов к ИИ.**\nПодожди примерно минуту или попробуй продолжить общение завтра.")
    else:
        # Если произошла какая-то другая неизвестная ошибка
        bot.reply_to(message, "⚠️ Произошла какая-то неизвестная ошибка сети. Попробуй еще раз чуть позже.")

# 1. КОМАНДА ДЛЯ ГЕНЕРАЦИИ КАРТИНОК И МЕМОВ
@bot.message_handler(commands=['art', 'draw', 'meme'])
def generate_art(message):
    try:
        user_prompt = message.text.split(' ', 1)
        if len(user_prompt) < 2:
            bot.reply_to(message, "Напиши после команды, что нарисовать. Пример:\n/art кот в каске из Раста")
            return
            
        prompt_text = user_prompt[1]
        bot.send_chat_action(message.chat.id, 'upload_photo')
        
        encoded_prompt = urllib.parse.quote(prompt_text)
        image_url = f"https://pollinations.ai{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        bot.send_photo(message.chat.id, image_url, caption=f"🎨 Твой запрос: {prompt_text}")
        
    except Exception as e:
        handle_ai_error(message, e)

# 2. ОБРАБОТКА ВХОДЯЩИХ ФОТО
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        raw_file = message.photo[-1]
        file_info = bot.get_file(raw_file.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        user_text = message.caption if message.caption else "Что изображено на этом фото?"
        
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=downloaded_file, mime_type='image/jpeg'),
                user_text
            ]
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        handle_ai_error(message, e)

# 3. ОБРАБОТКА ОБЫЧНОГО ТЕКСТА
@bot.message_handler(func=lambda message: True)
def get_ai_answer(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        handle_ai_error(message, e)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling()
