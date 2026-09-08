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

BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"  # Apna asli BotFather token yahan dalein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! YouTube ya Instagram ka koi bhi Video/Reel/Photo link bhejein, main download karke dunga.")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Processing link...")
    file_path = f"media_{m.chat.id}_{m.message_id}"

    try:
        # 1. INSTAGRAM (Photos, Reels, Videos)
        if 'instagram.com' in url:
            api_url = f"https://api.siputzx.my.id/api/d/igdl?url={url}"
            res = requests.get(api_url, timeout=25).json()

            if not res.get('status') or not res.get('data'):
                raise Exception("Instagram post private hai ya link galat hai.")

            media_list = res['data']
            bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)

            for idx, item in enumerate(media_list):
                media_url = item.get('url')
                if not media_url:
                    continue

                r = requests.get(media_url, stream=True, timeout=60)
                is_video = 'video' in r.headers.get('Content-Type', '').lower() or '.mp4' in media_url

                temp_file = f"{file_path}_{idx}.mp4" if is_video else f"{file_path}_{idx}.jpg"
                with open(temp_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)

                with open(temp_file, 'rb') as f:
                    if is_video:
                        bot.send_video(m.chat.id, f, timeout=300)
                    else:
                        bot.send_photo(m.chat.id, f, timeout=300)

                if os.path.exists(temp_file):
                    os.remove(temp_file)

            bot.delete_message(m.chat.id, msg.message_id)

        # 2. YOUTUBE (Videos / Shorts)
        elif 'youtube.com' in url or 'youtu.be' in url:
            api_url = f"https://api.siputzx.my.id/api/d/ytmp4?url={url}"
            res = requests.get(api_url, timeout=30).json()

            if not res.get('status') or not res.get('data'):
                raise Exception("YouTube video extract nahi ho saki.")

            dl_url = res['data'].get('dl')
            if not dl_url:
                raise Exception("Download link generate nahi hua.")

            bot.edit_message_text("🚀 Downloading & Uploading...", m.chat.id, msg.message_id)

            temp_vid = f"{file_path}.mp4"
            with requests.get(dl_url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(temp_vid, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)

            # Check 50MB limit
            file_size_mb = os.path.getsize(temp_vid) / (1024 * 1024)
            if file_size_mb > 49:
                bot.edit_message_text("❌ Video 50MB se badi hai, Telegram bot 50MB se badi file support nahi karta.", m.chat.id, msg.message_id)
            else:
                with open(temp_vid, 'rb') as f:
                    bot.send_video(m.chat.id, f, timeout=300)
                bot.delete_message(m.chat.id, msg.message_id)

            if os.path.exists(temp_vid):
                os.remove(temp_vid)

        else:
            bot.edit_message_text("Sirf Instagram aur YouTube ke links supported hain.", m.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"Dikkat aayi: {str(e)[:120]}", m.chat.id, msg.message_id)

    finally:
        # Cleanup
        for f in os.listdir('.'):
            if f.startswith(f"media_{m.chat.id}_{m.message_id}"):
                try:
                    os.remove(f)
                except:
                    pass

web_thread = Thread(target=run_web)
web_thread.daemon = True
web_thread.start()

print("Bot chalu ho gaya hai!")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
