import os
import glob
import shutil
from threading import Thread
from flask import Flask
import telebot
from telebot import apihelper
import yt_dlp
import instaloader

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

BOT_TOKEN = "APNA_TOKEN_YAHAN"  # Apna asli token yahan dalein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# Instaloader setup
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False
)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! YouTube ya Instagram ka video link bhejein.")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi video link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Downloading...")
    target_dir = f"dl_{m.chat.id}_{m.message_id}"

    try:
        # 1. Instagram download logic
        if 'instagram.com' in url:
            parts = [p for p in url.split('?')[0].split('/') if p]
            shortcode = parts[-1]

            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=target_dir)

            video_files = glob.glob(f"{target_dir}/*.mp4")
            if video_files:
                file_size_mb = os.path.getsize(video_files[0]) / (1024 * 1024)
                if file_size_mb > 49:
                    bot.edit_message_text("❌ Video 50MB se badi hai, Telegram allow nahi karta.", m.chat.id, msg.message_id)
                else:
                    bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)
                    with open(video_files[0], 'rb') as vf:
                        bot.send_video(m.chat.id, vf, timeout=300)
                    bot.delete_message(m.chat.id, msg.message_id)
            else:
                raise Exception("Instagram video nahi mili ya account private hai.")

        # 2. YouTube download logic (480p format)
        else:
            out_file = f"{target_dir}.mp4"
            opts = {
                'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]',
                'outtmpl': out_file,
                'quiet': True,
                'no_warnings': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'ios'],
                    }
                }
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            if os.path.exists(out_file):
                file_size_mb = os.path.getsize(out_file) / (1024 * 1024)
                if file_size_mb > 49:
                    bot.edit_message_text("❌ 480p par bhi video 50MB se badi hai, Telegram allow nahi karta.", m.chat.id, msg.message_id)
                else:
                    bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)
                    with open(out_file, 'rb') as vf:
                        bot.send_video(m.chat.id, vf, timeout=300)
                    bot.delete_message(m.chat.id, msg.message_id)
                os.remove(out_file)

    except Exception as e:
        bot.edit_message_text(f"Dikkat aayi: {str(e)[:120]}", m.chat.id, msg.message_id)

    finally:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)

web_thread = Thread(target=run_web)
web_thread.daemon = True
web_thread.start()

print("Bot chalu ho gaya hai!")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
