import os
import glob
from threading import Thread
from flask import Flask
import telebot
from telebot import apihelper
import yt_dlp

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7 on Railway!"

def run_web():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"  # Apna asli Bot token yahan dalein
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

    msg = bot.reply_to(m, "⚡ Downloading...")
    out_tmpl = f"dl_{m.chat.id}_{m.message_id}_%(id)s.%(ext)s"

    opts = {
        'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android_embedded', 'android_music'],
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        files = glob.glob(f"dl_{m.chat.id}_{m.message_id}_*")
        if not files:
            raise Exception("Media download nahi ho saka.")

        bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)

        for file_path in files:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 49:
                bot.reply_to(m, f"❌ Video 50MB se badi hai ({size_mb:.1f} MB), Telegram allow nahi karta.")
            else:
                ext = file_path.split('.')[-1].lower()
                with open(file_path, 'rb') as f:
                    if ext in ['mp4', 'mkv', 'webm', 'mov']:
                        bot.send_video(m.chat.id, f, timeout=300)
                    elif ext in ['jpg', 'jpeg', 'png', 'webp']:
                        bot.send_photo(m.chat.id, f, timeout=300)
                    else:
                        bot.send_document(m.chat.id, f, timeout=300)

        bot.delete_message(m.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"Dikkat aayi: {str(e)[:120]}", m.chat.id, msg.message_id)

    finally:
        for f in glob.glob(f"dl_{m.chat.id}_{m.message_id}_*"):
            try:
                os.remove(f)
            except:
                pass

web_thread = Thread(target=run_web)
web_thread.daemon = True
web_thread.start()

print("Bot chalu ho gaya hai!")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
