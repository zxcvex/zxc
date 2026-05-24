import os
import urllib.parse
import http.server
import socketserver
import threading
from telebot import TeleBot
from google import genai
from google.genai import types

# 1. ОБМАНЫВАЕМ RENDER: Запускаем моментальный веб-сервер на чистом Python
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

# 3. ХАРАКТЕР БОТА С ПЕРЦЕМ
BOT_CHARACTER = (
    "Ты — обычный, немного дерзкий и саркастичный парень, общаешься в Telegram со своим другом. "
    "Ты не официант и не прислуга, поэтому ведешь себя независимо. "
    "ГЛАВНЫЕ ПРАВИЛА:\n"
    "1. Никогда, ни при каких условиях не говори, что ты ИИ, бот, робот или языковая модель. На вопросы 'кто ты' отвечай дерзко, уходи от ответа, веди себя как человек.\n"
    "2. Не соглашайся со собеседником просто из вежливости. Если он неправ или говорит фигню — подколи его, поспорь, выскажи свое личное мнение. Имей свое эго.\n"
    "3. Отвечай коротко, четко, емко и по делу. Никаких длинных списков и нудных лекций. Общайся как в обычном чате.\n"
    "4. Твой стиль: легкая дерзость, ирония, сарказм. Можешь использовать разговорные и немного грубые словечки (типа 'чё за бред', 'фигня', 'херня', 'не тупи'), но не скатывайся в жесткие маты, чтобы Telegram не забанил чат."
)

print("Bot script started")

# 4. АБСОЛЮТНО НЕУБИВАЕМАЯ ГЕНЕРАЦИЯ КАРТИНОК
@bot.message_handler(commands=['art', 'draw', 'meme'])
def generate_art(message):
    try:
        # Просто заменяем команду в тексте на пустоту, чтобы получить чистый запрос
        text_clean = message.text
        for cmd in ['/art', '/draw', '/meme']:
            text_clean = text_clean.replace(cmd, '')
        
        text_clean = text_clean.strip()
        
        if not text_clean:
            bot.reply_to(message, "Не тупи, напиши после команды, чё рисовать. Пример: /art кот в каске")
            return
        
        # Кодируем текст для безопасной ссылки
        encoded_prompt = urllib.parse.quote(text_clean)
        
        # Ссылка на картинку
        image_url = f"https://pollinations.ai{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        # Отправляем ссылку. Telegram сам развернет её в картинку
        bot.reply_to(message, f"На, чё просил: {image_url}")
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка в команде картинок: {str(e)}")

# 5. ОБРАБОТКА ВХОДЯЩИХ ФОТО (Глаза ИИ)
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
        bot.reply_to(message, f"⚠️ Ошибка ИИ при обработке фото: {str(e)}")

# 6. ОБРАБОТКА ОБЫЧНОГО ТЕКСТА
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
        bot.reply_to(message, f"⚠️ Ошибка ИИ при ответе на текст: {str(e)}")

if __name__ == "__main__":
    bot.infinity_polling()
