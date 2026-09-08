import os
import glob
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

BOT_TOKEN = 'APNA_TOKEN_YAHAN'  # Apna asli token yahan dalein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# Instaloader setup
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_history=False
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
        # 1. Agar Instagram ka link hai
        if 'instagram.com' in url:
            # Shortcode extract karna
            parts = [p for p in url.split('?')[0].split('/') if p]
            if len(parts) >= 2 and parts[-2] in ['reel', 'p', 'reels']:
                shortcode = parts[-1]
            else:
                shortcode = parts[-1]

            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=target_dir)

            bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)

            video_files = glob.glob(f"{target_dir}/*.mp4")
            if video_files:
                with open(video_files[0], 'rb') as vf:
                    bot.send_video(m.chat.id, vf, timeout=300)
            else:
                raise Exception("Instagram video file nahi mili.")

        # 2. Agar YouTube ya koi aur link hai
        else:
            out_file = f"{target_dir}.mp4"
            opts = {
                'format': 'best[ext=mp4]/best',
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

            bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)

            if os.path.exists(out_file):
                with open(out_file, 'rb') as vf:
                    bot.send_video(m.chat.id, vf, timeout=300)
                os.remove(out_file)

        bot.delete_message(m.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"Dikkat aayi: {str(e)[:120]}", m.chat.id, msg.message_id)

    finally:
        # Cleanup folder
        if os.path.exists(target_dir):
            import shutil
            shutil.rmtree(target_dir, ignore_errors=True)

web_thread = Thread(target=run_web)
web_thread.daemon = True
web_thread.start()

print("Bot chalu ho gaya hai!")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
