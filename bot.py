import os
import glob
import re
import threading
import requests
from flask import Flask
import telebot
from telebot import apihelper
import yt_dlp

server = Flask(__name__)

@server.route('/')
def home():
    return "Bot is running 24/7 on Railway!"

def start_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"  # अपना टेलीग्राम बॉट टोकन डालें
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

def extract_yt_id(url):
    pattern = r'(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! YouTube video ka link bhejein, download ho jayegi.")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Processing download...")
    video_id = extract_yt_id(url)

    # 1. PEHLA RASTA: Invidious Proxy API (NO COOKIES REQUIRED, NEVER BLOCKED)
    if video_id:
        instances = [
            "https://inv.tux.pizza",
            "https://invidious.nerdvpn.de",
            "https://invidious.jing.rocks"
        ]
        for inst in instances:
            try:
                api_url = f"{inst}/api/v1/videos/{video_id}"
                r = requests.get(api_url, timeout=10).json()
                formats = r.get('formatStreams', [])
                if formats:
                    # Best pre-merged video with audio चुनना
                    target = formats[-1]
                    stream_url = target.get('url')
                    file_path = f"dl_{m.chat.id}_{m.message_id}.mp4"

                    bot.edit_message_text("⚡ Downloading video...", m.chat.id, msg.message_id)
                    with requests.get(stream_url, stream=True, timeout=120) as vid_req:
                        vid_req.raise_for_status()
                        with open(file_path, 'wb') as f:
                            for chunk in vid_req.iter_content(chunk_size=1024*1024):
                                if chunk:
                                    f.write(chunk)

                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if size_mb > 49:
                        bot.edit_message_text(f"❌ Video 50MB se badi hai ({size_mb:.1f} MB), Telegram bot limit 50MB hai.", m.chat.id, msg.message_id)
                    else:
                        bot.edit_message_text("🚀 Uploading...", m.chat.id, msg.message_id)
                        with open(file_path, 'rb') as vf:
                            bot.send_video(m.chat.id, vf, timeout=300, supports_streaming=True)
                        bot.delete_message(m.chat.id, msg.message_id)

                    try:
                        os.remove(file_path)
                    except:
                        pass
                    return
            except:
                continue

    # 2. DUSRA RASTA: FALLBACK YT-DLP (Android TV client spoofing)
    out_tmpl = f"dl_{m.chat.id}_{m.message_id}.%(ext)s"
    opts = {
        'format': 'b[ext=mp4]/best[ext=mp4]/b/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'android_vr'],
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        files = glob.glob(f"dl_{m.chat.id}_{m.message_id}*")
        if not files:
            raise Exception("Video download nahi ho saki.")

        file_path = files[0]
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 49:
            bot.edit_message_text(f"❌ Video 50MB se badi hai ({size_mb:.1f} MB).", m.chat.id, msg.message_id)
        else:
            with open(file_path, 'rb') as vf:
                bot.send_video(m.chat.id, vf, timeout=300)
            bot.delete_message(m.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"Dikkat aayi: {str(e)[:120]}", m.chat.id, msg.message_id)

    finally:
        for f in glob.glob(f"dl_{m.chat.id}_{m.message_id}*"):
            try:
                os.remove(f)
            except:
                pass

if __name__ == '__main__':
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    print("Bot chalu ho gaya hai!")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
