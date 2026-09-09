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

def get_yt_video_id(url):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None

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

        # 1. YOUTUBE
        if 'youtube.com' in url or 'youtu.be' in url:
            vid = get_yt_video_id(url)
            if not vid:
                raise Exception("YouTube Video ID nahi mili.")

            # Invidious reliable public instances jo bot block nahi karti
            instances = [
                "https://invidious.nerdvpn.de",
                "https://inv.nadeko.net",
                "https://invidious.private.coffee"
            ]

            for inst in instances:
                try:
                    r = requests.get(f"{inst}/api/v1/videos/{vid}", timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        # Formats me se best 480p/720p nikalna
                        formats = data.get('formatStreams', [])
                        if formats:
                            # 360p ya 720p combined stream
                            download_url = formats[-1].get('url')
                            if download_url and not download_url.startswith('http'):
                                download_url = f"{inst}{download_url}"
                            break
                except:
                    continue

            if not download_url:
                raise Exception("YouTube stream fetch nahi ho saki, dusra link try karein.")

        # 2. INSTAGRAM
        elif 'instagram.com' in url:
            clean_url = url.split('?')[0]
            # DDInstagram API direct CDN stream
            match = re.search(r'/(reel|p|reels)/([A-Za-z0-9_-]+)', clean_url)
            if not match:
                raise Exception("Galat Instagram link.")
            shortcode = match.group(2)
            
            dd_api = f"https://api.ddinstagram.com/posts/{shortcode}"
            r = requests.get(dd_api, timeout=15).json()
            item = r.get('item', {})
            download_url = item.get('video_url')
            
            if not download_url and item.get('image_versions2'):
                img_url = item['image_versions2']['candidates'][0]['url']
                img_path = f"dl_{m.chat.id}_{m.message_id}.jpg"
                img_data = requests.get(img_url, timeout=20).content
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                with open(img_path, 'rb') as f:
                    bot.send_photo(m.chat.id, f, timeout=300)
                os.remove(img_path)
                bot.delete_message(m.chat.id, msg.message_id)
                return

            if not download_url:
                raise Exception("Instagram video direct link nahi mila.")

        else:
            bot.edit_message_text("Kripya sirf YouTube ya Instagram ka link bhejein.", m.chat.id, msg.message_id)
            return

        bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)

        # Stream download
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
