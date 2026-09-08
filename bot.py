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

BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"  # Apna token yahan paste karein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! YouTube ya Instagram ka koi bhi link bhejein.")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Downloading...")
    file_path = f"media_{m.chat.id}_{m.message_id}.mp4"

    try:
        # 1. INSTAGRAM (ddinstagram direct CDN bypass)
        if 'instagram.com' in url:
            clean_url = url.split('?')[0].rstrip('/')
            match = re.search(r'/(reel|p|reels)/([A-Za-z0-9_-]+)', clean_url)
            if not match:
                raise Exception("Instagram link sahi nahi hai.")

            shortcode = match.group(2)
            # ddinstagram meta API - ye direct CDN video mp4 deti hai
            dd_api = f"https://api.ddinstagram.com/posts/{shortcode}"
            headers = {"User-Agent": "Mozilla/5.0"}
            
            res = requests.get(dd_api, headers=headers, timeout=25)
            if res.status_code != 200:
                raise Exception("Instagram post load nahi ho saki.")

            data = res.json()
            media = data.get('item', {})
            
            # Check video or image
            video_url = media.get('video_url')
            if not video_url and media.get('image_versions2'):
                # Single photo
                candidates = media['image_versions2'].get('candidates', [])
                if candidates:
                    img_url = candidates[0]['url']
                    img_path = f"media_{m.chat.id}_{m.message_id}.jpg"
                    r_img = requests.get(img_url, headers=headers, timeout=30)
                    with open(img_path, 'wb') as f:
                        f.write(r_img.content)
                    with open(img_path, 'rb') as f:
                        bot.send_photo(m.chat.id, f, timeout=300)
                    if os.path.exists(img_path):
                        os.remove(img_path)
                    bot.delete_message(m.chat.id, msg.message_id)
                    return

            if not video_url:
                raise Exception("Media link nahi mila.")

            bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)
            with requests.get(video_url, headers=headers, stream=True, timeout=90) as r:
                r.raise_for_status()
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)

            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 49:
                bot.edit_message_text("❌ Video 50MB se badi hai.", m.chat.id, msg.message_id)
            else:
                with open(file_path, 'rb') as vf:
                    bot.send_video(m.chat.id, vf, timeout=300)
                bot.delete_message(m.chat.id, msg.message_id)

        # 2. YOUTUBE
        elif 'youtube.com' in url or 'youtu.be' in url:
            # Multi-backend fallback for YouTube
            cobalt_payload = {"url": url, "videoQuality": "480"}
            cobalt_headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }
            
            # Public verified Cobalt instances
            instances = [
                "https://cobalt-api.kwiatekm.pl",
                "https://api.cobalt.tools"
            ]
            
            stream_url = None
            for inst in instances:
                try:
                    res = requests.post(inst, json=cobalt_payload, headers=cobalt_headers, timeout=15)
                    data = res.json()
                    if data.get('url'):
                        stream_url = data['url']
                        break
                except:
                    continue

            if not stream_url:
                raise Exception("YouTube server se connect nahi hua.")

            bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)
            with requests.get(stream_url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)

            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 49:
                bot.edit_message_text("❌ Video 50MB se badi hai.", m.chat.id, msg.message_id)
            else:
                with open(file_path, 'rb') as vf:
                    bot.send_video(m.chat.id, vf, timeout=300)
                bot.delete_message(m.chat.id, msg.message_id)

        else:
            bot.edit_message_text("Kripya Instagram ya YouTube ka link bhejein.", m.chat.id, msg.message_id)

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
