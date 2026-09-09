import os
import io
import time
import threading
import telebot
from telebot import types
from PIL import Image
from flask import Flask, request
import feedparser

# ==========================================
# 1. कॉन्फ़िगरेशन (यहाँ अपनी डिटेल्स डालें)
# ==========================================
BOT_TOKEN = "8526721171:AAENlzSLW1DkNqf6EaZwDFfW5-bcfvkTa6M"
CHANNEL_ID = "@apnamorenasarkarijob"
WEBHOOK_URL = "https://apna-morena-sarkari-job.onrender.com"  # आपका Render URL

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)

# ==========================================
# 2. Webhook Endpoints (परमानेंट नो-कन्फ्लिक्ट सेटअप)
# ==========================================
@server.route('/' + BOT_TOKEN, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@server.route('/')
def webhook_status():
    return "✅ Webhook Bot Engine is Active 24/7!", 200

# ==========================================
# 3. सरकारी जॉब ऑटो-अलर्ट इंजन (100% Working)
# ==========================================
sent_jobs = set()

def fetch_and_post_jobs():
    # Google News की लाइव RSS फीड (SSC, Sarkari Naukri, Admit Card)
    rss_urls = [
        "https://news.google.com/rss/search?q=Sarkari+Naukri+SSC+when:2d&hl=hi&gl=IN&ceid=IN:hi",
        "https://news.google.com/rss/search?q=Government+Job+Vacancy+India+when:2d&hl=en-IN&gl=IN&ceid=IN:en"
    ]
    
    print("🔍 Fetching live jobs from RSS...")
    
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            print(f"📡 Feed loaded, found {len(feed.entries)} entries.")
            
            for entry in feed.entries[:3]:  # हर फीड से ताज़ा 3 पोस्ट
                job_id = entry.link
                if job_id not in sent_jobs:
                    sent_jobs.add(job_id)
                    title = entry.title
                    link = entry.link
                    
                    alert_text = (
                        f"📢 **सरकारी भर्ती / एग्ज़ाम अपडेट**\n\n"
                        f"📌 **हेडलाइन:** {title}\n\n"
                        f"🔗 **पूरी जानकारी और लिंक:**\n{link}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"ताज़ा सरकारी अपडेट्स के लिए चैनल से जुड़े रहें!"
                    )
                    
                    bot.send_message(CHANNEL_ID, alert_text)
                    print(f"✅ Alert posted: {title[:30]}...")
                    time.sleep(3)
        except Exception as e:
            print(f"⚠️ Feed error: {e}")

def job_alert_scheduler():
    # सर्वर चालू होने के 10 सेकंड बाद तुरंत पहला अलर्ट भेजेगा
    time.sleep(10)
    fetch_and_post_jobs()
    
    # इसके बाद हर 30 मिनट में चेक करेगा
    while True:
        time.sleep(1800)
        fetch_and_post_jobs()
def job_alert_scheduler():
    time.sleep(15)
    fetch_and_post_jobs()
    while True:
        time.sleep(1800)  # हर 30 मिनट में चेक
        fetch_and_post_jobs()

# ==========================================
# 4. इमेज और सिग्नेचर रिसाइज़र
# ==========================================
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 **सरकारी फॉर्म इमेज/सिग्नेचर रिसाइज़र**\n\n"
        "अपनी फोटो या सिग्नेचर भेजें। बॉट उसे सटीक KB साइज़ में तैयार करेगा।"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'document'])
def handle_docs_photo(message):
    try:
        file_id = message.photo[-1].file_id if message.content_type == 'photo' else message.document.file_id
        file_info = bot.get_file(file_id)
        user_data[message.chat.id] = bot.download_file(file_info.file_path)

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
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    img_resized = image.resize((target_width, h_size), Image.Resampling.LANCZOS)

    quality = 90
    while quality >= 10:
        buf = io.BytesIO()
        img_resized.save(buf, format="JPEG", quality=quality, optimize=True)
        size_kb = len(buf.getvalue()) / 1024
        if size_kb <= max_kb:
            return buf.getvalue(), size_kb
        quality -= 5

    img_resized = img_resized.resize((int(target_width * 0.75), int(h_size * 0.75)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img_resized.save(buf, format="JPEG", quality=65, optimize=True)
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
        out_file.name = "Sarkari_Valid_Image.jpg"

        caption = f"✅ **{tag} तैयार है!**\n📏 सटीक साइज़: `{size_kb:.1f} KB`"
        bot.send_document(chat_id, out_file, caption=caption, parse_mode="Markdown")
        bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ रिसाइज़ में त्रुटि: {e}", chat_id, msg.message_id)

# ==========================================
# 5. मुख्य सेटअप (Webhook रजिस्ट्रेशन और रनर)
# ==========================================
if __name__ == '__main__':
    # अलर्ट थ्रेड चालू करें
    threading.Thread(target=job_alert_scheduler, daemon=True).start()

    # पुराना कनेक्शन हटाकर Webhook सेट करें
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    print(f"🚀 Webhook successfully set to {WEBHOOK_URL}")

    # Flask सर्वर सीधे मुख्य प्रोसेस में चलेगा (Render कभी Timed Out नहीं होगा)
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)
