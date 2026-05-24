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

# --- ЖЕСТКИЙ ХАРАКТЕР БОТА ---
BOT_CHARACTER = (
    "Ты — обычный, немного дерзкий и саркастичный парень, общаешься в Telegram со своим другом. "
    "Ты не официант и не прислуга, поэтому ведешь себя независимо. "
    "ГЛАВНЫЕ ПРАВИЛА:\n"
    "1. Никогда, ни при каких условиях не говори, что ты ИИ, бот, робот или языковая модель. На вопросы 'кто ты' отвечай дерзко, уходи от ответа, веди себя как человек.\n"
    "2. Не соглашайся со собеседником просто из вежливости. Если он неправ или говорит фигню — подколи его, поспорь, выскажи свое личное мнение. Имей свое эго.\n"
    "3. Отвечай коротко, четко, емко и по делу. Никаких длинных списков и нудных лекций. Общайся как в обычном чате.\n"
    "4. Твой стиль: легкая дерзость, ирония, сарказм. Можешь использовать разговорные и немного грубые словечки (типа 'чё за хуйня', 'фигня', 'хуйня', 'не тупи'), чтобы Telegram не забанил чат."
)

print("Облачный ИИ-бот (с характером живого человека) запущен!")

def handle_ai_error(message, exception):
    error_str = str(exception)
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "Quota exceeded" in error_str:
        bot.reply_to(message, "🛑 Ой, лимит запросов кончился. Подожди минутку.")
    else:
        bot.reply_to(message, "⚠️ Ошибка сети. Попробуй еще раз.")

# 1. КОМАНДА ДЛЯ ГЕНЕРАЦИИ КАРТИНОК И МЕМОВ
@bot.message_handler(commands=['art', 'draw', 'meme'])
def generate_art(message):
    try:
        user_prompt = message.text.split(' ', 1)
        if len(user_prompt) < 2:
            bot.reply_to(message, "Напиши после команды, что нарисовать. Пример:\n/art кот в каске")
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
        
        # Передаем характер в системные инструкции для фото
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=downloaded_file, mime_type='image/jpeg'),
                user_text
            ],
            config=types.GenerateContentConfig(system_instruction=BOT_CHARACTER)
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        handle_ai_error(message, e)

# 3. ОБРАБОТКА ОБЫЧНОГО ТЕКСТА
@bot.message_handler(func=lambda message: True)
def get_ai_answer(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Передаем характер в системные инструкции для текста
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
            config=types.GenerateContentConfig(system_instruction=BOT_CHARACTER)
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        handle_ai_error(message, e)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    bot.infinity_polling()
