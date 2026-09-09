import os
import io
import time
import threading
import telebot
from telebot import types
from PIL import Image
from flask import Flask, request
import feedparser
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. कॉन्फ़िगरेशन
# ==========================================
BOT_TOKEN = "8526721171:AAENlzSLW1DkNqf6EaZwDFfW5-bcfvkTa6M"
CHANNEL_ID = "@apnamorenasarkarijob"
WEBHOOK_URL = "https://apna-morena-sarkari-job.onrender.com"

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)

# ==========================================
# 2. Render Webhook Endpoints
# ==========================================
@server.route('/' + BOT_TOKEN, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@server.route('/')
def webhook_status():
    return "✅ All-India Sarkari Job Engine Active 24/7!", 200

# ==========================================
# 3. ऑल-इंडिया डायरेक्ट फॉर्म + हिंदी न्यूज़ इंजन
# ==========================================
sent_jobs = set()

def fetch_sarkari_result_direct():
    """सीधे SarkariResult से डायरेक्ट ऑनलाइन फॉर्म लिंक्स"""
    url = "https://www.sarkariresult.com/latestjob/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            post_div = soup.find('div', id='post')
            if post_div:
                links = post_div.find_all('a')
                for a in links[:3]:  # ताज़ा 3 सीधे फॉर्म
                    title = a.get_text().strip()
                    link = a.get('href')
                    if link and title and link not in sent_jobs:
                        sent_jobs.add(link)
                        if not link.startswith('http'):
                            link = f"https://www.sarkariresult.com{link}"
                        
                        msg = (
                            f"📌 **सीधा ऑनलाइन फॉर्म (Direct Application)**\n\n"
                            f"🏢 **भर्ती:** {title}\n\n"
                            f"🔗 **सीधा फॉर्म लिंक:**\n{link}\n\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"🎯 ताज़ा सरकारी फॉर्म के लिए जुड़े रहें!"
                        )
                        bot.send_message(CHANNEL_ID, msg)
                        time.sleep(3)
    except Exception as e:
        print(f"Direct Scraping Error: {e}")

def fetch_all_india_hindi_news():
    """ऑल-इंडिया प्रमुख हिंदी न्यूज़ चैनल्स (दैनिक भास्कर, अमर उजाला, आज तक, NBT, जागरण)"""
    hindi_channels_rss = [
        # ऑल-इंडिया केंद्र व राज्य भर्तियां (दैनिक भास्कर/अमर उजाला/जागरण जोश नेटवर्क)
        "https://news.google.com/rss/search?q=सरकारी+नौकरी+भर्ती+when:1d&hl=hi&gl=IN&ceid=IN:hi",
        # SSC, रेलवे, बैंक, UPSC स्पेशल
        "https://news.google.com/rss/search?q=SSC+रेलवे+UPSC+भर्ती+when:1d&hl=hi&gl=IN&ceid=IN:hi",
        # पुलिस, शिक्षक, पटवारी, राज्य स्तरीय परीक्षाएं
        "https://news.google.com/rss/search?q=पुलिस+कांस्टेबल+शिक्षक+भर्ती+when:1d&hl=hi&gl=IN&ceid=IN:hi",
        # एडमिट कार्ड और आंसर-की सूचना
        "https://news.google.com/rss/search?q=एडमिट+कार्ड+रिजल्ट+घोषित+when:1d&hl=hi&gl=IN&ceid=IN:hi"
    ]
    
    for url in hindi_channels_rss:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                if entry.link not in sent_jobs:
                    sent_jobs.add(entry.link)
                    
                    msg = (
                        f"📢 **सरकारी भर्ती सूचना (न्यूज़ नेटवर्क)** 🇮🇳\n\n"
                        f"📰 **अपडेट:** {entry.title}\n\n"
                        f"👉 **पूरी खबर व आधिकारिक जानकारी:**\n{entry.link}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ सबसे तेज़ और सही अपडेट्स के लिए शेयर करें!"
                    )
                    bot.send_message(CHANNEL_ID, msg)
                    time.sleep(3)
        except Exception as e:
            print(f"Hindi News Error: {e}")

def job_alert_scheduler():
    time.sleep(15)
    # बूट होते ही तुरंत पहली बार अपडेट चेक
    fetch_sarkari_result_direct()
    fetch_all_india_hindi_news()
    
    # इसके बाद हर 10 मिनट (600 सेकंड) में चेक करेगा
    while True:
        time.sleep(600)
        fetch_sarkari_result_direct()
        fetch_all_india_hindi_news()

# ==========================================
# 4. इमेज और सिग्नेचर रिसाइज़र (सटीक सरकारी मानक)
# ==========================================
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 **सरकारी फॉर्म इमेज/सिग्नेचर रिसाइज़र**\n\n"
        "अपनी फोटो या सिग्नेचर भेजें। बॉट उसे SSC, UPSC, MP Police आदि के लिए सही KB में कन्वर्ट करेगा।"
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
        out_file.name = "Sarkari_Job_Resized.jpg"

        caption = f"✅ **{tag} तैयार है!**\n📏 सटीक साइज़: `{size_kb:.1f} KB`"
        bot.send_document(chat_id, out_file, caption=caption, parse_mode="Markdown")
        bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ रिसाइज़ में त्रुटि: {e}", chat_id, msg.message_id)

# ==========================================
# 5. मुख्य एग्जीक्यूशन
# ==========================================
if __name__ == '__main__':
    threading.Thread(target=job_alert_scheduler, daemon=True).start()

    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    print(f"🚀 Master Bot Engine active at {WEBHOOK_URL}")

    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)
