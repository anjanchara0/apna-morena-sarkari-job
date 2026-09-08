import os
import telebot
from telebot import apihelper
import yt_dlp

apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

# Apna bot token quotes ke andar dalein
BOT_TOKEN = "8971427857:AAEaGfBJ3OzIM4j3_uPWLzbZDXwE1MUTZWQ"

bot = telebot.TeleBot(BOT_TOKEN)


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

  # Fast download aur chhota size (Mobile optimized)
  opts = {
      'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best',
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
    print('Error:', e)
    bot.edit_message_text(
        f'Dikkat aayi: {str(e)[:100]}', m.chat.id, msg.message_id
    )


print('Bot chalu ho gaya hai!')
bot.infinity_polling(timeout=60, long_polling_timeout=60)
