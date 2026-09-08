import os
import re
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

BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"  # Apna asli BotFather token yahan dalein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! YouTube ya Instagram ka koi bhi Video/Reel link bhejein.")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Processing video...")
    file_path = f"vid_{m.chat.id}_{m.message_id}.mp4"

    try:
        download_url = None

        # 1. INSTAGRAM (Fast CDN Resolver)
        if 'instagram.com' in url:
            clean_url = url.split('?')[0].rstrip('/')
            match = re.search(r'/(reel|p|reels)/([A-Za-z0-9_-]+)', clean_url)
            if not match:
                raise Exception("Galat Instagram link.")
            
            shortcode = match.group(2)
            # Direct meta parser via public gateway
            api_endpoint = f"https://api.vkrdown.com/api/get?url=https://www.instagram.com/reel/{shortcode}/"
            res = requests.get(api_endpoint, timeout=20).json()
            
            if res.get('data') and res['data'].get('downloadUrl'):
                download_url = res['data']['downloadUrl']
            elif res.get('downloadUrl'):
                download_url = res['downloadUrl']
            else:
                # Alternate direct endpoint
                alt_api = f"https://instavideosave.net/api/convert?url={clean_url}"
                r_alt = requests.get(alt_api, timeout=20).json()
                if r_alt.get('url'):
                    download_url = r_alt['url'][0].get('url')

            if not download_url:
                raise Exception("Instagram video ka direct link nahi mila.")

        # 2. YOUTUBE (Direct Media Streamer)
        elif 'youtube.com' in url or 'youtu.be' in url:
            api_endpoint = f"https://api.vkrdown.com/api/get?url={url}"
            res = requests.get(api_endpoint, timeout=25).json()

            if res.get('data') and res['data'].get('downloads'):
                # Best 720p ya 480p format select karna
                formats = res['data']['downloads']
                for f in formats:
                    if f.get('format_id') in ['22', '18'] or '720' in f.get('format', '') or '480' in f.get('format', ''):
                        download_url = f.get('url')
                        break
                if not download_url and formats:
                    download_url = formats[0].get('url')

            if not download_url:
                raise Exception("YouTube download link extract nahi ho saka.")

        else:
            bot.edit_message_text("Sirf Instagram aur YouTube ke links bhej sakte hain.", m.chat.id, msg.message_id)
            return

        bot.edit_message_text("🚀 Downloading & Uploading...", m.chat.id, msg.message_id)

        # Video chunk streaming
        headers = {'User-Agent': 'Mozilla/5.0'}
        with requests.get(download_url, stream=True, headers=headers, timeout=120) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)

        # 50MB check
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 49:
            bot.edit_message_text("❌ Video 50MB se badi hai, Telegram bot 50MB limit cross nahi kar sakta.", m.chat.id, msg.message_id)
        else:
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
