import os
from telebot import TeleBot
from google import genai
from flask import Flask
import threading

# Создаем фейковый веб-сервер для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_web_server():
    # Запускаем сайт на порту, который просит Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Настройки бота
TG_TOKEN = os.environ.get("TG_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")  # Проверь этот ключ!

bot = TeleBot(TG_TOKEN)
ai_client = genai.Client(api_key=GEMINI_KEY)

print("Собственный облачный бот запущен!")

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
        bot.reply_to(message, f"Ошибка ИИ: {str(e)}")

if __name__ == "__main__":
    # Запускаем сайт в отдельном потоке
    threading.Thread(target=run_web_server, daemon=True).start()
    # Запускаем бота
    bot.infinity_polling()
