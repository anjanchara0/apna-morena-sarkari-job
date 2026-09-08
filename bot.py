import os
from threading import Thread
from flask import Flask
import telebot
from telebot import apihelper
import yt_dlp

# Render ko zinda rakhne ke liye chhota web server
app = Flask(__name__)


@app.route('/')
def home():
  return 'Bot 24/7 chal raha hai!'


def run_web():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


# Telegram Bot Setup
apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

BOT_TOKEN = 'APNA_TOKEN_YAHAN'  # Apna asli token yahan dalein
bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(m):
  bot.reply_to(m, 'Namaste! Mujhe video link bhejein.')


@bot.message_handler(func=lambda m: True)
def dl(m):
  url = m.text.strip()
  if not url.startswith('http'):
    bot.reply_to(m, 'Kripya sahi link bhejein.')
    return

  msg = bot.reply_to(m, '⚡ Downloading...')
  opts = {
      'format': (
          'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best'
      ),
      'outtmpl': 'fast_vid.%(ext)s',
      'quiet': True,
      'no_warnings': True,
  }

  try:
    with yt_dlp.YoutubeDL(opts) as ydl:
      info = ydl.extract_info(url, download=True)
      fn = ydl.prepare_filename(info)

    bot.edit_message_text(
        '🚀 Uploading to Telegram...', m.chat.id, msg.message_id
    )

    with open(fn, 'rb') as vf:
      bot.send_video(m.chat.id, vf, timeout=300)

    if os.path.exists(fn):
      os.remove(fn)
    bot.delete_message(m.chat.id, msg.message_id)

  except Exception as e:
    bot.edit_message_text(
        f'Dikkat aayi: {str(e)[:100]}', m.chat.id, msg.message_id
    )


if __name__ == '__main__':
  # Web server ko background thread me chalayein
  t = Thread(target=run_web)
  t.start()
  print('Bot chalu ho gaya hai!')
  bot.infinity_polling(timeout=60, long_polling_timeout=60)
