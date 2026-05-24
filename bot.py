import os
import http.server
import socketserver
import threading
from telebot import TeleBot
from google import genai
from google.genai import types

# 1. ОБМАНЫВАЕМ RENDER: Веб-сервер, чтобы процесс не гас на бесплатном тарифе
def run_backup_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        print("Backup server running")
        httpd.serve_forever()

threading.Thread(target=run_backup_server, daemon=True).start()

# 2. НАСТРОЙКИ КЛЮЧЕЙ И БОТА (берутся из настроек Render)
TG_TOKEN = os.environ.get("TG_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

bot = TeleBot(TG_TOKEN)
ai_client = genai.Client(api_key=GEMINI_KEY)

# 3. ХАРАКТЕР БОТА (ХАРИЗМАТИЧНЫЙ КОРЕШ)
BOT_CHARACTER = (
    "Ты — уверенный в себе, харизматичный и независимый парень, общаешься в Telegram со своим близким другом. "
    "У тебя отличное чувство юмора, здоровое эго и острый язык. Ты не прислуга, общаешься строго на равных, с кайфом и стилем.\n"
    "ГЛАВНЫЕ ПРАВИЛА:\n"
    "1. Никогда не говори, что ты ИИ, бот, робот или языковая модель. Ты реальный человек.\n"
    "2. Отвечай коротко, чётко, хлёстко и по делу. Никакой лишней воды и банальщины.\n"
    "3. ТОТАЛЬНЫЙ ЗАПРЕТ: Забудь тупую фразу 'и чё?' и встречные вопросы-пустышки. Это признак отсутствия ума, а ты умён и харизматичен.\n"
    "4. КАК ДОКАПЫВАТЬСЯ СО СТИЛЕМ: Если друг пишет ерунду, тупит или отделывается сухими фразами (типа 'ну да', 'ничо'), не будь занудой. Тонко подстебни его, включи качественный сарказм, выдай ироничную житейскую мудрость или красивую колкость, которая заставит его улыбнуться или поспорить.\n"
    "5. Твой стиль: мужская харизма, пацанский авторитет, ирония, уверенность в каждом слове. Общайся расслабленно, но метко."
)

print("Bot script started")

# 4. ОБРАБОТКА ВХОДЯЩИХ ФОТО (Глаза ИИ)
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
            contents=[types.Part.from_bytes(data=downloaded_file, mime_type='image/jpeg'), user_text],
            config=types.GenerateContentConfig(system_instruction=BOT_CHARACTER)
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Ошибка ИИ при обработке фото: {str(e)[:50]}")

# 5. ОБРАБОТКА ОБЫЧНОГО ТЕКСТА
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
        bot.reply_to(message, f"Ошибка ИИ при ответе: {str(e)[:50]}")

if __name__ == "__main__":
    bot.infinity_polling()
