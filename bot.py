import os
from threading import Thread
from flask import Flask
import telebot
from telebot import apihelper
import yt_dlp

app = Flask(__name__)


@app.route('/')
def home():
  return 'Bot is running 24/7!'


def run_web():
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)


apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

BOT_TOKEN = '8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ'  # Apna asli token yahan dalein
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)  # threaded=True se multiple users handle honge


@bot.message_handler(commands=['start'])
def send_welcome(m):
  bot.reply_to(
      m, 'Namaste! Mujhe video link bhejein, main turant download karke dunga.'
  )


@bot.message_handler(func=lambda m: True)
def dl(m):
  url = m.text.strip()
  if not url.startswith('http'):
    bot.reply_to(m, 'Kripya sahi link bhejein.')
    return

  msg = bot.reply_to(m, '⚡ Downloading...')

  # Har user ke liye alag file name (chat_id + message_id) taaki video mix na ho
  unique_filename = f'video_{m.chat.id}_{m.message_id}.%(ext)s'

  opts = {
        'format': (
            'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best'
        ),
        'outtmpl': unique_filename,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            }
        },
    }

  fn = None
  try:
    with yt_dlp.YoutubeDL(opts) as ydl:
      info = ydl.extract_info(url, download=True)
      fn = ydl.prepare_filename(info)

    bot.edit_message_text(
        '🚀 Uploading to Telegram...', m.chat.id, msg.message_id
    )

    with open(fn, 'rb') as vf:
      bot.send_video(m.chat.id, vf, timeout=300)

    bot.delete_message(m.chat.id, msg.message_id)

  except Exception as e:
    bot.edit_message_text(
        f'Dikkat aayi: {str(e)[:100]}', m.chat.id, msg.message_id
    )

  finally:
    # File send hone ke baad turant delete hogi taaki server ki memory na bhare
    if fn and os.path.exists(fn):
      os.remove(fn)


web_thread = Thread(target=run_web)
web_thread.daemon = True
web_thread.start()

print('Bot chalu ho gaya hai!')
bot.infinity_polling(timeout=60, long_polling_timeout=60)
