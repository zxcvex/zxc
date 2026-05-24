import os
import urllib.parse
import urllib.request
import io
import http.server
import socketserver
import threading
from telebot import TeleBot
from google import genai
from google.genai import types

# 1. WEB SERVER FOR RENDER
def run_backup_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        print("Server running")
        httpd.serve_forever()

threading.Thread(target=run_backup_server, daemon=True).start()

# 2. INITIALIZATION
TG_TOKEN = os.environ.get("TG_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

bot = TeleBot(TG_TOKEN)
ai_client = genai.Client(api_key=GEMINI_KEY)

# 3. AI CHARACTER (Strict Russian response rule inside English prompt)
BOT_CHARACTER = (
    "You are a regular, slightly bold, sarcastic and rude guy chatting with your friend in Russian language. "
    "Do not say you are an AI, robot, bot or large language model. Keep answers short, punchy and catchy. "
    "Do not agree out of politeness, argue and use simple words. "
    "ALWAYS RESPOND IN RUSSIAN LANGUAGE ONLY."
)

print("Bot script started")

def handle_ai_error(message, exception):
    error_str = str(exception)
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "Quota exceeded" in error_str:
        bot.reply_to(message, "Limit exceeded. Wait a minute.")
    else:
        bot.reply_to(message, f"Network error: {error_str[:50]}")

# 4. FIX: IMAGE GENERATION WITHOUT RUSSIAN CAPTION
@bot.message_handler(commands=['art', 'draw', 'meme'])
def generate_art(message):
    try:
        text_clean = message.text
        for cmd in ['/art', '/draw', '/meme']:
            text_clean = text_clean.replace(cmd, '')
        text_clean = text_clean.strip()
        
        if not text_clean:
            bot.reply_to(message, "Write what to draw after the command.")
            return
            
        bot.send_chat_action(message.chat.id, 'upload_photo')
        
        # Encode Russian prompt to safe URL format
        encoded_prompt = urllib.parse.quote(text_clean)
        image_url = f"https://pollinations.ai{encoded_prompt}?width=1024&height=1024&nologo=true"
        
        # Download image bytes from API
        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            image_data = response.read()
            
        # Convert bytes to file object
        photo_file = io.BytesIO(image_data)
        photo_file.name = 'meme.jpg'
        
        # FIX: Send clean photo without any text caption to prevent latin-1 encoding errors
        bot.send_photo(message.chat.id, photo_file)
        
    except Exception as e:
        handle_ai_error(message, e)

# 5. IMAGE INPUT HANDLING
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

# 6. TEXT INPUT HANDLING
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
