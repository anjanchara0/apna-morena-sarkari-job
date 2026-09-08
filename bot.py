import os
import requests
from threading import Thread
from flask import Flask
import telebot
from telebot import apihelper

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

BOT_TOKEN = '8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ'  # Apna asli token yahan dalein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! YouTube ya Instagram ka koi bhi link bhejein.")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi video link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Fetching video...")
    file_path = f"video_{m.chat.id}_{m.message_id}.mp4"

    try:
        # Cobalt API ke zariye download (Cloud IP blocks ko bypass karta hai)
        api_url = "https://co.wuk.sh/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "vQuality": "720"
        }

        r = requests.post(api_url, json=payload, headers=headers, timeout=20)
        data = r.json()

        video_download_url = data.get('url')
        if not video_download_url:
            raise Exception("Video extract nahi ho saki ya private hai.")

        bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)

        # Video file stream karke download karna
        with requests.get(video_download_url, stream=True, timeout=60) as v_stream:
            v_stream.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in v_stream.iter_content(chunk_size=1024*1024):
                    f.write(chunk)

        with open(file_path, 'rb') as vf:
            bot.send_video(m.chat.id, vf, timeout=300)

        bot.delete_message(m.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"Dikkat aayi: {str(e)[:120]}", m.chat.id, msg.message_id)

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

web_thread = Thread(target=run_web)
web_thread.daemon = True
web_thread.start()

print("Bot chalu ho gaya hai!")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
