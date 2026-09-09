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

BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"  # Apna bot token yahan dalein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! Instagram Reel ya Post link bhejein, poori audio ke saath video mil jayegi.")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Downloading (with Audio)...")
    file_path = f"dl_{m.chat.id}_{m.message_id}.mp4"

    try:
        # INSTAGRAM SPECIFIC HANDLER (Guaranteed Audio)
        if 'instagram.com' in url:
            clean_url = url.split('?')[0].rstrip('/')
            match = re.search(r'/(reel|p|reels)/([A-Za-z0-9_-]+)', clean_url)
            if not match:
                raise Exception("Instagram link sahi nahi hai.")

            shortcode = match.group(2)
            # DDInstagram API direct clean CDN deta hai jisme audio saath hoti hai
            api_url = f"https://api.ddinstagram.com/posts/{shortcode}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(api_url, headers=headers, timeout=20).json()
            item = res.get('item', {})

            video_url = item.get('video_url')
            if video_url:
                # Direct stream download
                with requests.get(video_url, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
            else:
                # Agar sirf Photo ho
                if item.get('image_versions2'):
                    img_url = item['image_versions2']['candidates'][0]['url']
                    img_path = f"dl_{m.chat.id}_{m.message_id}.jpg"
                    with open(img_path, 'wb') as f:
                        f.write(requests.get(img_url, headers=headers, timeout=20).content)
                    with open(img_path, 'rb') as f:
                        bot.send_photo(m.chat.id, f, timeout=300)
                    os.remove(img_path)
                    bot.delete_message(m.chat.id, msg.message_id)
                    return
                else:
                    raise Exception("Video stream nahi mili.")

        # OTHER PLATFORMS / FALLBACK YT-DLP
        else:
            opts = {
                'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'outtmpl': f"dl_{m.chat.id}_{m.message_id}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            downloaded = glob.glob(f"dl_{m.chat.id}_{m.message_id}.*")
            if downloaded:
                file_path = downloaded[0]
            else:
                raise Exception("Media download nahi ho saka.")

        if not os.path.exists(file_path):
            raise Exception("File save nahi ho saki.")

        bot.edit_message_text("🚀 Uploading to Telegram...", m.chat.id, msg.message_id)

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
