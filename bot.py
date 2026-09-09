import os
import io
import time
import threading
import urllib.request
from flask import Flask
from PIL import Image
import telebot
from telebot import types
import feedparser

server = Flask(__name__)

@server.route('/')
def home():
    return "Sarkari Tool & Auto-Alert Bot is Running 24/7 on Railway!"

def start_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8526721171:AAENlzSLW1DkNqf6EaZwDFfW5-bcfvkTa6M"          # BotFather से मिला टोकन
CHANNEL_USERNAME = "@apnamorenasarkarijobbot"  # अपने चैनल का यूजरनेम (@ के साथ)
# =======================================================

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

user_images = {}
posted_links = set()

FEEDS = [
    "https://timesofindia.indiatimes.com/rssfeeds/913168846.cms",
    "https://www.jagranjosh.com/rss/josh/sarkari-naukri.xml"
]

def fetch_feed_with_headers(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return feedparser.parse(resp.read())

def job_alert_scheduler():
    # चैनल कनेक्शन टेस्ट करने के लिए 5 सेकंड में टेस्ट मैसेज
    time.sleep(5)
    try:
        test_msg = (
            "🚀 **अलर्ट सिस्टम चालू हो गया है!**\n\n"
            "इस चैनल पर अब सभी सरकारी नौकरी, एडमिट कार्ड और रिजल्ट की अपडेट्स लाइव मिलेंगी।"
        )
        bot.send_message(CHANNEL_USERNAME, test_msg, parse_mode="Markdown")
        print("Test message sent successfully to channel!")
    except Exception as e:
        print(f"CRITICAL: Failed to post test message to channel: {e}")

    while True:
        try:
            for feed_url in FEEDS:
                feed = fetch_feed_with_headers(feed_url)
                for entry in feed.entries[:2]:
                    link = entry.get('link', '')
                    title = entry.get('title', 'नई सरकारी भर्ती सूचना')

                    if link and link not in posted_links:
                        posted_links.add(link)

                        message_text = (
                            "📢 **सरकारी नौकरी / परीक्षा नई अपडेट!**\n\n"
                            f"📌 **{title}**\n\n"
                            "ℹ️ पूरी जानकारी व ऑनलाइन आवेदन के लिए नीचे दिए गए लिंक पर जाएँ:\n"
                            f"🔗 {link}\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔔 तुरंत अपडेट्स के लिए जुड़े रहें: {CHANNEL_USERNAME}\n"
                            "⚡ फोटो/साइन 20KB-50KB करने के लिए हमारे बॉट का उपयोग करें।"
                        )

                        bot.send_message(
                            CHANNEL_USERNAME,
                            message_text,
                            parse_mode="Markdown",
                            disable_web_page_preview=False
                        )
                        time.sleep(5)
        except Exception as e:
            print(f"RSS Alert Loop Error: {e}")

        time.sleep(1800)

def is_user_subscribed(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Check error: {e}")
        return False

def get_join_markup():
    markup = types.InlineKeyboardMarkup()
    clean_channel = CHANNEL_USERNAME.replace('@', '')
    btn_join = types.InlineKeyboardButton("📢 चैनल जॉइन करें", url=f"https://t.me/{clean_channel}")
    btn_check = types.InlineKeyboardButton("🔄 जॉइन कर लिया (Check)", callback_data="check_join")
    markup.add(btn_join)
    markup.add(btn_check)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if not is_user_subscribed(CHANNEL_USERNAME, user_id):
        text = (
            "👋 **नमस्ते!**\n\n"
            "सरकारी फॉर्म की फोटो और सिग्नेचर 2 सेकंड में 20KB-50KB करने के लिए, "
            "कृपया पहले हमारे मुख्य चैनल को जॉइन करें।\n\n"
            "जॉइन करने के बाद नीचे **'जॉइन कर लिया'** बटन दबाएं।"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=get_join_markup())
        return

    text = (
        "✅ **स्वागत है!**\n\n"
        "यह बॉट सरकारी फॉर्म (SSC, Railway, Police, State Exams) के लिए फोटो का साइज बिल्कुल सही बनाता है।\n\n"
        "📸 **अपनी फोटो या सिग्नेचर इमेज यहाँ भेजें:**"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def handle_check_join(call):
    user_id = call.from_user.id
    if is_user_subscribed(CHANNEL_USERNAME, user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            "🎉 **वेरिफिकेशन सफल रहा!**\n\nअब आप अपनी फोटो या सिग्नेचर भेज सकते हैं।"
        )
    else:
        bot.answer_callback_query(call.id, "❌ आपने अभी तक चैनल जॉइन नहीं किया है! कृपया पहले जॉइन करें।", show_alert=True)

@bot.message_handler(content_types=['photo', 'document'])
def handle_image(message):
    user_id = message.from_user.id
    if not is_user_subscribed(CHANNEL_USERNAME, user_id):
        bot.send_message(
            message.chat.id,
            "⚠️ कृपया टूल का उपयोग करने से पहले हमारे चैनल को जॉइन करें:",
            reply_markup=get_join_markup()
        )
        return

    try:
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        else:
            file_id = message.document.file_id

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        user_images[user_id] = downloaded_file

        markup = types.InlineKeyboardMarkup(row_width=1)
        btn1 = types.InlineKeyboardButton("🖼️ पासपोर्ट फोटो (20KB - 50KB)", callback_data="size_photo")
        btn2 = types.InlineKeyboardButton("✍️ सिग्नेचर (10KB - 20KB)", callback_data="size_sign")
        markup.add(btn1, btn2)

        bot.reply_to(message, "👇 **आपको किस साइज में बदलना है?**", reply_markup=markup, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "❌ इमेज पढ़ने में दिक्कत आई। कृपया दोबारा भेजें।")

def compress_to_target(image_bytes, min_kb, max_kb):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail((800, 800), Image.Resampling.LANCZOS)

    out_io = io.BytesIO()
    for q in range(95, 10, -5):
        out_io.seek(0)
        out_io.truncate(0)
        img.save(out_io, format='JPEG', quality=q, optimize=True)
        size_kb = len(out_io.getvalue()) / 1024
        if size_kb <= max_kb:
            break

    return out_io.getvalue()

@bot.callback_query_handler(func=lambda call: call.data in ["size_photo", "size_sign"])
def handle_compression(call):
    user_id = call.from_user.id
    if user_id not in user_images:
        bot.answer_callback_query(call.id, "फोटो एक्सपायर हो गई, कृपया दोबारा भेजें।", show_alert=True)
        return

    msg = bot.send_message(call.message.chat.id, "⚡ इमेज तैयार हो रही है...")
    raw_data = user_images[user_id]

    if call.data == "size_photo":
        final_bytes = compress_to_target(raw_data, 20, 48)
        caption_type = "पासपोर्ट फोटो (20KB - 50KB के अंदर)"
    else:
        final_bytes = compress_to_target(raw_data, 10, 19)
        caption_type = "सिग्नेचर (10KB - 20KB के अंदर)"

    size_kb = len(final_bytes) / 1024
    out_file = io.BytesIO(final_bytes)
    out_file.name = "Sarkari_Form_Image.jpg"

    bot.send_document(
        call.message.chat.id,
        out_file,
        caption=f"✅ **{caption_type} तैयार है!**\n📏 साइज: `{size_kb:.1f} KB`\n\n📢 अपने दोस्तों के साथ शेयर करें!",
        parse_mode="Markdown"
    )
    bot.delete_message(call.message.chat.id, msg.message_id)

if __name__ == '__main__':
    t_flask = threading.Thread(target=start_flask)
    t_flask.daemon = True
    t_flask.start()

    t_alerts = threading.Thread(target=job_alert_scheduler)
    t_alerts.daemon = True
    t_alerts.start()

    print("Bot is Running with Auto-Alerts Engine!")
    bot.polling(none_stop=True, interval=2, timeout=30)
