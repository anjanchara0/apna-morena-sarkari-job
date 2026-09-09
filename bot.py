import os
import io
import time
import threading
import telebot
from telebot import types
from PIL import Image
from flask import Flask
import feedparser

# ==========================================
# 1. कॉन्फ़िगरेशन
# ==========================================
BOT_TOKEN = "8526721171:AAENlzSLW1DkNqf6EaZwDFfW5-bcfvkTa6M"
CHANNEL_ID = "@apnamorenasarkarijobbot"  # उदाहरण: "@apna_morena_sarkari_job"

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# 2. Render Uptime के लिए Flask सर्वर
# ==========================================
server = Flask(__name__)

@server.route('/')
def home():
    return "✅ Sarkari Job Bot & Resizer Live 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ==========================================
# 3. लाइव सरकारी जॉब और रिजल्ट अलर्ट इंजन
# ==========================================
sent_jobs = set()

def fetch_and_post_jobs():
    rss_urls = [
        "https://www.freejobalert.com/feed",
        "https://www.sarkariresult.com/feed.xml"
    ]
    
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # ताज़ा 5 अपडेट्स
                job_id = entry.link
                if job_id not in sent_jobs:
                    sent_jobs.add(job_id)
                    title = entry.title
                    link = entry.link
                    
                    alert_text = (
                        f"📢 **नई सरकारी नौकरी / अपडेट**\n\n"
                        f"📌 **पद/परीक्षा:** {title}\n\n"
                        f"🔗 **विस्तृत जानकारी व ऑनलाइन फॉर्म:**\n{link}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"रोज़ाना ताज़ा अपडेट के लिए जुड़े रहें!"
                    )
                    
                    bot.send_message(CHANNEL_ID, alert_text, parse_mode="Markdown")
                    time.sleep(3)  # टेलीग्राम की सीमा से बचने के लिए छोटा गैप
        except Exception as e:
            print(f"Feed error ({url}): {e}")

def job_alert_scheduler():
    time.sleep(10)
    # बूट होते ही पहला अलर्ट चेक
    fetch_and_post_jobs()
    
    while True:
        time.sleep(1800)  # हर 30 मिनट में नई वैकेंसी चेक करेगा
        fetch_and_post_jobs()

# ==========================================
# 4. टेलीग्राम बॉट और सटीक KB इमेज रिसाइज़र
# ==========================================
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 **सरकारी फॉर्म फोटो/सिग्नेचर रिसाइज़र में आपका स्वागत है!**\n\n"
        "📸 अपनी फोटो या सिग्नेचर भेजें। बॉट उसे सरकारी फॉर्म (SSC, UPSC, State Exam) "
        "के सटीक KB साइज़ में कन्वर्ट करके देगा।"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

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
        btn1 = types.InlineKeyboardButton("📷 पासपोर्ट फोटो (20 - 50 KB)", callback_data="photo_50")
        btn2 = types.InlineKeyboardButton("✍️ सिग्नेचर (10 - 20 KB)", callback_data="sign_20")
        btn3 = types.InlineKeyboardButton("📄 डॉक्यूमेंट (50 - 100 KB)", callback_data="doc_100")
        btn4 = types.InlineKeyboardButton("📁 हैवी डॉक्यूमेंट (100 - 200 KB)", callback_data="doc_200")
        markup.add(btn1, btn2, btn3, btn4)

        bot.reply_to(message, "⚙️ **किस साइज़ में कन्वर्ट करना है?**", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ एरर: {e}")

def resize_to_target_kb(image, max_kb, target_width):
    # पहलू अनुपात (Aspect Ratio) बनाए रखते हुए डाइमेंशन सेट करें
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    img_resized = image.resize((target_width, h_size), Image.Resampling.LANCZOS)

    # क्वालिटी लूप ताकि साइज़ लक्ष्य के भीतर ही रहे
    quality = 90
    while quality >= 10:
        buf = io.BytesIO()
        img_resized.save(buf, format="JPEG", quality=quality, optimize=True)
        size_kb = len(buf.getvalue()) / 1024
        if size_kb <= max_kb:
            return buf.getvalue(), size_kb
        quality -= 5

    # अगर फिर भी बड़ा रहे तो डाइमेंशन 20% और घटाएँ
    img_resized = img_resized.resize((int(target_width * 0.8), int(h_size * 0.8)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img_resized.save(buf, format="JPEG", quality=70, optimize=True)
    return buf.getvalue(), len(buf.getvalue()) / 1024

@bot.callback_query_handler(func=lambda call: True)
def process_resize(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "कृपया फोटो दोबारा भेजें।")
        return

    bot.answer_callback_query(call.id, "प्रोसेसिंग...")
    msg = bot.send_message(chat_id, "⏳ सटीक KB में कन्वर्ट किया जा रहा है...")

    try:
        img_bytes = user_data[chat_id]
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # सरकारी फॉर्म के अनुसार सटीक चौड़ाई और अधिकतम साइज़
        if call.data == "sign_20":
            final_bytes, size_kb = resize_to_target_kb(image, max_kb=19, target_width=300)
            tag = "सिग्नेचर (10-20 KB)"
        elif call.data == "photo_50":
            final_bytes, size_kb = resize_to_target_kb(image, max_kb=48, target_width=450)
            tag = "पासपोर्ट फोटो (20-50 KB)"
        elif call.data == "doc_100":
            final_bytes, size_kb = resize_to_target_kb(image, max_kb=95, target_width=800)
            tag = "डॉक्यूमेंट (50-100 KB)"
        else:
            final_bytes, size_kb = resize_to_target_kb(image, max_kb=190, target_width=1100)
            tag = "डॉक्यूमेंट (100-200 KB)"

        out_file = io.BytesIO(final_bytes)
        out_file.name = "Sarkari_Form_Valid.jpg"

        caption = f"✅ **{tag} तैयार है!**\n📏 सटीक साइज़: `{size_kb:.1f} KB`\n*(सरकारी पोर्टल पर अपलोड के लिए तैयार)*"
        bot.send_document(chat_id, out_file, caption=caption, parse_mode="Markdown")
        bot.delete_message(chat_id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ रिसाइज़ में त्रुटि: {e}", chat_id, msg.message_id)

# ==========================================
# 5. रनर
# ==========================================
if __name__ == '__main__':
    # वेब सर्वर स्टार्ट
    threading.Thread(target=run_flask, daemon=True).start()
    
    # जॉब अलर्ट इंजन स्टार्ट
    threading.Thread(target=job_alert_scheduler, daemon=True).start()
    
    print("🚀 Bot Engine Initializing...")
    
    # टेलीग्राम पर पुराने किसी भी अटके हुए वेबहुक/कनेक्शन को पहले ड्रॉप करें
    try:
        bot.remove_webhook()
    except Exception:
        pass
    
    time.sleep(2)
    print("🚀 Bot Engine Running with Live Job Feeds & Smart Resizer!")
    
    # रीस्टार्ट के टकराव से बचने के लिए सेफ लूप
    while True:
        try:
            bot.polling(none_stop=True, interval=3, timeout=20, skip_pending=True)
        except Exception as e:
            print(f"Polling recovered from error: {e}")
            time.sleep(5)
