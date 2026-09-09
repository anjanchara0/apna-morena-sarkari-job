import os
import io
import time
import threading
import telebot
from telebot import types
from PIL import Image
from flask import Flask

# ==========================================
# 1. कॉन्फ़िगरेशन (यहाँ अपना टोकन और चैनल यूज़रनेम डालें)
# ==========================================
BOT_TOKEN = "8526721171:AAENlzSLW1DkNqf6EaZwDFfW5-bcfvkTa6M"
CHANNEL_ID = "@apnamorenasarkarijobbot"  # उदाहरण: "@apna_morena_sarkari_job"

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# 2. Render Uptime के लिए Flask वेब सर्वर
# ==========================================
server = Flask(__name__)

@server.route('/')
def home():
    return "✅ Sarkari Job & Resizer Bot 24/7 Live on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ==========================================
# 3. सरकारी जॉब ऑटो-अलर्ट इंजन
# ==========================================
def send_welcome_alert():
    try:
        msg = (
            "🚀 **अलर्ट सिस्टम लाइव हो चुका है!**\n\n"
            "इस चैनल पर सभी सरकारी नौकरी, एडमिट कार्ड और रिजल्ट की अपडेट्स स्वतः प्राप्त होंगी।"
        )
        bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
        print("✅ Channel Welcome Alert Sent Successfully!")
    except Exception as e:
        print(f"⚠️ Welcome message error (Check Admin & Channel ID): {e}")

def job_alert_scheduler():
    # पहला मैसेज बूट होते ही 10 सेकंड बाद भेजेगा
    time.sleep(10)
    send_welcome_alert()
    
    while True:
        # यहाँ पर हर 6 घंटे (21600 सेकंड) में नया अपडेट चेक करने का लूप
        time.sleep(21600)
        # भविष्य में स्क्रैपिंग कोड यहाँ ऑटो रन होगा

# ==========================================
# 4. टेलीग्राम बॉट कमांड्स और इमेज रिसाइज़र
# ==========================================
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **नमस्ते! सरकारी फॉर्म असिस्टेंट बॉट में आपका स्वागत है।**\n\n"
        "📸 **इमेज और सिग्नेचर रिसाइज़ करने के लिए:**\n"
        "बस अपनी फोटो या सिग्नेचर को डॉक्यूमेंट (File) या फोटो के रूप में यहाँ भेजें।"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'document'])
def handle_docs_photo(message):
    try:
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        user_data[message.chat.id] = downloaded_file

        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("📷 फोटो (20 - 50 KB)", callback_data="photo_50")
        btn2 = types.InlineKeyboardButton("✍️ सिग्नेचर (10 - 20 KB)", callback_data="sign_20")
        btn3 = types.InlineKeyboardButton("📄 डॉक्यूमेंट (50 - 100 KB)", callback_data="doc_100")
        btn4 = types.InlineKeyboardButton("📁 हैवी डॉक्यूमेंट (100 - 200 KB)", callback_data="doc_200")
        markup.add(btn1, btn2, btn3, btn4)

        bot.reply_to(message, "⚙️ **कृपया अपनी आवश्यकता अनुसार साइज़ चुनें:**", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ इमेज लोड करने में त्रुटि: {e}")

@bot.callback_query_handler(func=lambda call: True)
def process_resize(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "कृपया फोटो दोबारा भेजें।")
        return

    target_kb = 50
    caption_type = "इमेज"
    if call.data == "photo_50":
        target_kb = 45
        caption_type = "पासपोर्ट फोटो"
    elif call.data == "sign_20":
        target_kb = 18
        caption_type = "सिग्नेचर"
    elif call.data == "doc_100":
        target_kb = 90
        caption_type = "डॉक्यूमेंट"
    elif call.data == "doc_200":
        target_kb = 180
        caption_type = "हैवी डॉक्यूमेंट"

    bot.answer_callback_query(call.id, "प्रोसेसिंग शुरू...")
    msg = bot.send_message(chat_id, "⏳ इमेज रिसाइज़ हो रही है, कृपया प्रतीक्षा करें...")

    try:
        img_bytes = user_data[chat_id]
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # कंप्रेशन लॉजिक
        quality = 95
        step = 5
        final_bytes = None

        while quality > 10:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            size_kb = len(buffer.getvalue()) / 1024
            if size_kb <= target_kb:
                final_bytes = buffer.getvalue()
                break
            quality -= step

        if not final_bytes:
            # अगर सिर्फ क्वालिटी कम करने से नहीं हुआ तो डायमेंशन घटाएँ
            image.thumbnail((image.width * 0.7, image.height * 0.7))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=75, optimize=True)
            final_bytes = buffer.getvalue()

        size_kb = len(final_bytes) / 1024
        out_file = io.BytesIO(final_bytes)
        out_file.name = "Sarkari_Form_Image.jpg"

        caption = f"✅ **{caption_type} तैयार है!**\n📏 साइज़: `{size_kb:.1f} KB`"
        bot.send_document(chat_id, out_file, caption=caption, parse_mode="Markdown")
        bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ रिसाइज़ में त्रुटि: {e}", chat_id, msg.message_id)

# ==========================================
# 5. मुख्य एग्जीक्यूशन (Conflict-Free Setup)
# ==========================================
if __name__ == '__main__':
    # 1. Flask को बैकग्राउंड थ्रेड में चलाएँ
    t_web = threading.Thread(target=run_flask, daemon=True)
    t_web.start()

    # 2. जॉब अलर्ट शेड्यूलर को बैकग्राउंड थ्रेड में चलाएँ
    t_alerts = threading.Thread(target=job_alert_scheduler, daemon=True)
    t_alerts.start()

    print("🚀 Bot Engine Started without Conflicts!")
    # 3. skip_pending=True पुराने सभी अटके हुए कनेक्शन और मैसेज हटाकर फ्रेश शुरुआत करता है
    bot.infinity_polling(skip_pending=True)
