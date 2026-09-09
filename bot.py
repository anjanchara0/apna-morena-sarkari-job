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
    return "Bot is running 24/7 on Railway!"

def run_web():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"  # Apna bot token dalein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! YouTube ya Instagram ka video link bhejein.")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Downloading...")
    file_path = f"dl_{m.chat.id}_{m.message_id}.mp4"

    try:
        download_url = None

        # 1. YOUTUBE (SaveFrom Direct Engine)
        if 'youtube.com' in url or 'youtu.be' in url:
            sf_url = "https://worker.savefrom.workers.dev/analyze"
            payload = {"url": url}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Content-Type": "application/json"
            }
            res = requests.post(sf_url, json=payload, headers=headers, timeout=20).json()
            
            if res.get('url'):
                # 360p ya 720p stream
                for item in res.get('url', []):
                    if item.get('audio') is not False and item.get('ext') == 'mp4':
                        download_url = item.get('url')
                        break
                if not download_url and res.get('url'):
                    download_url = res['url'][0].get('url')

            if not download_url:
                # Fallback engine
                alt_res = requests.get(f"https://api.allorigins.win/raw?url=https://0x0.st", timeout=5)
                raise Exception("YouTube stream nahi mili, video restricted ho sakti hai.")

        # 2. INSTAGRAM (Fast DD Proxy)
        elif 'instagram.com' in url:
            clean_url = url.split('?')[0].rstrip('/')
            match = re.search(r'/(reel|p|reels)/([A-Za-z0-9_-]+)', clean_url)
            if not match:
                raise Exception("Instagram link sahi nahi hai.")

            shortcode = match.group(2)
            dd_api = f"https://api.ddinstagram.com/posts/{shortcode}"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(dd_api, headers=headers, timeout=20).json()
            item = r.get('item', {})

            download_url = item.get('video_url')
            if not download_url and item.get('image_versions2'):
                img_url = item['image_versions2']['candidates'][0]['url']
                img_path = f"dl_{m.chat.id}_{m.message_id}.jpg"
                with open(img_path, 'wb') as f:
                    f.write(requests.get(img_url, headers=headers, timeout=20).content)
                with open(img_path, 'rb') as f:
                    bot.send_photo(m.chat.id, f, timeout=300)
                os.remove(img_path)
                bot.delete_message(m.chat.id, msg.message_id)
                return

            if not download_url:
                raise Exception("Instagram media fetch nahi ho saki.")

        else:
            bot.edit_message_text("Sirf YouTube ya Instagram ka link bhej sakte hain.", m.chat.id, msg.message_id)
            return

        bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)

        # Video stream fetch
        with requests.get(download_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)

        # Size check
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 49:
            bot.edit_message_text(f"❌ Video 50MB se badi hai ({size_mb:.1f} MB), Telegram allow nahi karta.", m.chat.id, msg.message_id)
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
