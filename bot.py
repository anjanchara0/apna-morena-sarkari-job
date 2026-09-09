import os
import glob
import threading
from flask import Flask
import telebot
from telebot import apihelper
import yt_dlp
import imageio_ffmpeg

server = Flask(__name__)

@server.route('/')
def home():
    return "Bot is running 24/7 on Railway!"

def start_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"  # अपना असली बॉट टोकन डालें
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

COOKIE_CONTENT = os.environ.get('YOUTUBE_COOKIES', '')
COOKIE_FILE = '/tmp/youtube_cookies.txt'
if COOKIE_CONTENT:
    with open(COOKIE_FILE, 'w', encoding='utf-8') as cf:
        cf.write(COOKIE_CONTENT)

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "Namaste! YouTube ya Instagram link bhejein. (50MB ke andar video aur bada hone par MP3 audio mil jayega).")

@bot.message_handler(func=lambda m: True)
def dl(m):
    url = m.text.strip()
    if not url.startswith('http'):
        bot.reply_to(m, "Kripya sahi link bhejein.")
        return

    msg = bot.reply_to(m, "⚡ Downloading (Optimizing size)...")
    out_tmpl = f"dl_{m.chat.id}_{m.message_id}.%(ext)s"

    # 1. Pehle 480p/360p video download karne ki koshish karega (taaki 50MB limit cross na ho)
    opts = {
        'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
        'merge_output_format': 'mp4',
        'ffmpeg_location': FFMPEG_PATH,
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
    }

    if os.path.exists(COOKIE_FILE):
        opts['cookiefile'] = COOKIE_FILE

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        files = glob.glob(f"dl_{m.chat.id}_{m.message_id}*")
        if not files:
            raise Exception("Video download nahi ho saki.")

        file_path = files[0]
        size_mb = os.path.getsize(file_path) / (1024 * 1024)

        # Agar video 48MB se chhoti hai toh seedha video bhej dega
        if size_mb <= 48:
            bot.edit_message_text("🚀 Uploading Video...", m.chat.id, msg.message_id)
            with open(file_path, 'rb') as vf:
                bot.send_video(m.chat.id, vf, timeout=300, supports_streaming=True)
            bot.delete_message(m.chat.id, msg.message_id)
        else:
            # Agar video 48MB se badi hai, toh fail hone ke badle MP3 Audio download karega
            bot.edit_message_text(f"⚠️ Video {size_mb:.1f}MB ki hai (Telegram limit 50MB hai). MP3 Audio convert kiya ja raha hai...", m.chat.id, msg.message_id)
            try:
                os.remove(file_path)
            except:
                pass

            audio_tmpl = f"dl_{m.chat.id}_{m.message_id}_audio.%(ext)s"
            audio_opts = {
                'format': 'bestaudio/best',
                'ffmpeg_location': FFMPEG_PATH,
                'outtmpl': audio_tmpl,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
            }
            if os.path.exists(COOKIE_FILE):
                audio_opts['cookiefile'] = COOKIE_FILE

            with yt_dlp.YoutubeDL(audio_opts) as ydl_audio:
                ydl_audio.download([url])

            audio_files = glob.glob(f"dl_{m.chat.id}_{m.message_id}_audio*")
            if audio_files:
                audio_path = audio_files[0]
                with open(audio_path, 'rb') as af:
                    bot.send_audio(m.chat.id, af, caption="🎵 Song Audio (Size limit bypass)", timeout=300)
                bot.delete_message(m.chat.id, msg.message_id)
            else:
                bot.edit_message_text("❌ Audio extract nahi ho saka.", m.chat.id, msg.message_id)

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
