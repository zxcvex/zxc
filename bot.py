import os
import urllib.parse
import http.server
import socketserver
import threading
from telebot import TeleBot
from google import genai
from google.genai import types

def run_backup_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        print("Backup server running")
        httpd.serve_forever()

threading.Thread(target=run_backup_server, daemon=True).start()

TG_TOKEN = os.environ.get("TG_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

bot = TeleBot(TG_TOKEN)
ai_client = genai.Client(api_key=GEMINI_KEY)

# Личность на английском, но с приказом отвечать по-русски (для стабильности кодировки)
BOT_CHARACTER = (
    "You are a regular, slightly bold and sarcastic guy chatting with your friend in Russian. "
    "Do not say you are an AI, robot or bot. Keep answers short and catchy. "
    "Do not agree out of politeness, joke and argue if needed. Use simple words. "
    "ALWAYS RESPOND IN RUSSIAN LANGUAGE."
)

print("Bot script started")

def handle_ai_error(message, exception):
    error_str = str(exception)
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "Quota exceeded" in error_str:
        bot.reply_to(message, "Притормози, лимиты кончились. Зайди позже.")
    else:
        # Выводим реальный текст ошибки, чтобы наконец увидеть, ЧТО именно ломается!
        bot.reply_to(message, f"Ошибка сети или кода: {error_str[:100]}")

@bot.message_handler(commands=['art', 'draw', 'meme'])
def generate_art(message):
    try:
        user_prompt = message.text.split(' ', 1)
        if len(user_prompt) < 2:
            bot.reply_to(message, "Напиши после команды, чё нарисовать.")
            return
        
        prompt_text = user_prompt[1]
        bot.send_chat_action(message.chat.id, 'upload_photo')
        
        encoded_prompt = urllib.parse.quote(prompt_text)
        image_url = f"https://pollinations.ai{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        bot.send_photo(message.chat.id, image_url, caption=f"На, чё просил: {prompt_text}")
    except Exception as e:
        handle_ai_error(message, e)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        raw_file = message.photo[-1]
        file_info = bot.get_file(raw_file.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        user_text = message.caption if message.caption else "What is on this photo?"
        
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[types.Part.from_bytes(data=downloaded_file, mime_type='image/jpeg'), user_text],
            config=types.GenerateContentConfig(system_instruction=BOT_CHARACTER)
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        handle_ai_error(message, e)

@bot.message_handler(func=lambda message: True)
def get_ai_answer(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
            config=types.GenerateContentConfig(system_instruction=BOT_CHARACTER)
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        handle_ai_error(message, e)

if __name__ == "__main__":
    bot.infinity_polling()
