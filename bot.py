import os
import io
import time
import html
import random
import threading
from datetime import datetime
import telebot
from telebot import types
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request
import feedparser
import requests
from bs4 import BeautifulSoup
import pymongo

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. कॉन्फ़िगरेशन
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526721171:AAHI55V6vyEaMvG0cBRXrjCnorPgDDC5eZg")
CHANNEL_ID = "@apnamorenasarkarijob"
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://apna-morena-sarkari-job.onrender.com")

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
    return "✅ Master Student Platform Engine Live 24/7!", 200

# ==========================================
# 3. परमानेंट डेटाबेस (MongoDB) + वायरल रेफरल सिस्टम
# ==========================================
# ⚠️ ध्यान दें: नीचे <anjanchara0_db_user>की जगह अपना असली यूज़रनेम लिखें
MONGO_URI = "mongodb+srv://<db_username>:CBgHFMd2oDjGuXO3@cluster0.veqiuri.mongodb.net/?appName=Cluster0"

try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["SarkariBotDB"]
    users_col = db["Users"]
    print("✅ MongoDB Database Connected!")
except Exception as e:
    print("❌ MongoDB Connection Error:", e)

def get_referral_count(user_id):
    """डेटाबेस से रेफरल स्कोर निकालें"""
    try:
        user = users_col.find_one({"_id": user_id})
        return user.get("referral_count", 0) if user else 0
    except:
        return 0

def record_referral(new_user_id, referrer_id):
    """नए रेफरल को परमानेंट सेव करें"""
    try:
        user = users_col.find_one({"_id": new_user_id})
        if not user or not user.get("referred_by"):
            users_col.update_one({"_id": new_user_id}, {"$set": {"referred_by": referrer_id}}, upsert=True)
            users_col.update_one({"_id": referrer_id}, {"$inc": {"referral_count": 1}}, upsert=True)
            return True
    except: pass
    return False

def is_user_subscribed(chat_id, user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return True

def send_join_channel_prompt(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_join = types.InlineKeyboardButton("📢 चैनल जॉइन करें (यहाँ क्लिक करें)", url="https://t.me/apnamorenasarkarijob")
    btn_verify = types.InlineKeyboardButton("✅ मैंने जॉइन कर लिया (Verify & Unlock)", callback_data="sub_verify_check")
    markup.add(btn_join, btn_verify)
    bot.send_message(chat_id, "⚠️ **चैनल सदस्यता अनिवार्य है!**\n\nसभी सरकारी टूल्स का उपयोग करने के लिए हमारे चैनल से जुड़े रहना अनिवार्य है।\n\n👉 नीचे बटन दबाकर चैनल जॉइन करें, फिर **'मैंने जॉइन कर लिया'** पर क्लिक करें。", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "sub_verify_check")
def handle_verify_subscription(call):
    chat_id, user_id = call.message.chat.id, call.from_user.id
    if is_user_subscribed(chat_id, user_id):
        bot.answer_callback_query(call.id, "🎉 वेरिफिकेशन सफल! टूल्स अनलॉक हो गए हैं।", show_alert=True)
        bot.delete_message(chat_id, call.message.message_id)
        send_task_completion_menu(chat_id, "✅ **स्वागत है! अपनी सेवा चुनें 👇**")
    else:
        bot.answer_callback_query(call.id, "❌ आपने अभी तक चैनल जॉइन नहीं किया है!", show_alert=True)

def check_premium(chat_id, user_id):
    """प्रीमियम लॉक चेक (MongoDB से 5 रेफरल अनिवार्य)"""
    refs = get_referral_count(user_id)
    if refs >= 5: return True
    bot.send_message(
        chat_id, 
        f"🔒 **यह एक Premium (VIP) टूल है!**\n\n"
        f"क्विज़, करेंट अफेयर्स, टाइपिंग और CV मेकर को फ्री में जीवन भर के लिए अनलॉक करने हेतु **5 दोस्तों को बॉट से जोड़ें**।\n\n"
        f"📊 **आपके वर्तमान रेफरल:** `{refs} / 5`\n\n"
        f"👉 मेनू से **'🎁 रेफर करें (Link निकालें)'** बटन दबाएं और अपना लिंक दोस्तों को भेजें!", 
        parse_mode="Markdown"
    )
    return False

# ==========================================
# 4. बैकग्राउंड अलर्ट्स और न्यूज़
# ==========================================
sent_jobs = set()

def fetch_sarkari_result_direct():
    url = "https://www.sarkariresult.com/latestjob/"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            if post_div := soup.find('div', id='post'):
                for a in post_div.find_all('a')[:3]:
                    title, link = a.get_text().strip(), a.get('href')
                    if link and title and link not in sent_jobs:
                        sent_jobs.add(link)
                        link = f"https://www.sarkariresult.com{link}" if not link.startswith('http') else link
                        bot.send_message(CHANNEL_ID, f"📌 **सीधा ऑनलाइन फॉर्म**\n\n🏢 **भर्ती:** {title}\n🔗 **लिंक:** {link}")
                        time.sleep(2)
    except: pass

def fetch_all_india_hindi_news():
    hindi_channels_rss = ["https://news.google.com/rss/search?q=सरकारी+नौकरी+भर्ती+when:1d&hl=hi&gl=IN&ceid=IN:hi"]
    for url in hindi_channels_rss:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                if entry.link not in sent_jobs:
                    sent_jobs.add(entry.link)
                    bot.send_message(CHANNEL_ID, f"📢 **सरकारी भर्ती न्यूज़** 🇮🇳\n\n📰 **अपडेट:** {entry.title}\n👉 **पूरी खबर:** {entry.link}")
                    time.sleep(2)
        except: pass

def job_alert_scheduler():
    time.sleep(15)
    fetch_sarkari_result_direct()
    fetch_all_india_hindi_news()
    while True:
        time.sleep(600)
        fetch_sarkari_result_direct()
        fetch_all_india_hindi_news()

# ==========================================
# 5. इन-मेमोरी स्टेट व नया स्ट्रिक्ट VIP मेनू
# ==========================================
user_sessions = {}

STEP_PROMPTS = {
    's_name': "👉 सबसे पहले अपना **पूरा नाम (Full Name)** लिखें:",
    's_phone': "📱 अपना **मोबाइल नंबर** भेजें:",
    's_email': "✉️ अपनी **ईमेल आईडी** भेजें:",
    's_address': "📍 अपना **शहर / पता (Address)** भेजें:",
    's_father': "👨‍👦 **पिता का नाम** भेजें:",
    's_dob': "🎂 अपनी **जन्मतिथि (DOB)** भेजें (उदा: 15/08/2002):",
    's_pg_course': "🎓 **पोस्ट ग्रेजुएशन (PG):** डिग्री का नाम (उदा: MCA/MA/M.Sc) *(नहीं किया तो NA लिखें)*:",
    's_pg_board': "🏛️ **PG किस यूनिवर्सिटी से किया?**:",
    's_pg_score': "📊 **PG में कितने प्रतिशत बने?**:",
    's_ug_course': "🏛️ **ग्रेजुएशन (UG):** डिग्री का नाम (उदा: BA/B.Sc) *(नहीं किया तो NA लिखें)*:",
    's_ug_board': "🏛️ **ग्रेजुएशन किस यूनिवर्सिटी से किया?**:",
    's_ug_score': "📊 **ग्रेजुएशन में कितने प्रतिशत बने?**:",
    's_dip_course': "⚙️ **डिप्लोमा / ITI:** कोर्स का नाम *(नहीं किया तो NA लिखें)*:",
    's_dip_board': "🏢 **डिप्लोमा/ITI किस बोर्ड से किया?**:",
    's_dip_score': "📊 **डिप्लोमा/ITI में प्रतिशत?**:",
    's_12th_board': "📚 **12वीं (12th):** बोर्ड का नाम *(लागू न हो तो NA लिखें)*:",
    's_12th_score': "📊 **12वीं में प्रतिशत?**:",
    's_10th_board': "📖 **10वीं (10th):** बोर्ड का नाम:",
    's_10th_score': "📊 **10वीं में प्रतिशत?**:",
    's_skills': "⚡ अपनी **स्किल्स** लिखें (उदा: Computer, Typing):",
    's_exp': "💼 **कार्य अनुभव (Experience):** (उदा: 1 Year / Fresher):",
    's_certs': "📜 **सर्टिफिकेट्स:** (उदा: DCA, PGDCA / NA):",
    's_photo': "📷 **अंतिम चरण: अपनी पासपोर्ट फोटो भेजें** (या बिना फोटो बटन दबाएँ):"
}

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("📐 फोटो / साइन रिसाइज़र"), types.KeyboardButton("🏷️ फोटो पर नाम व तारीख"))
    markup.add(types.KeyboardButton("🔒 सरकारी एग्जाम क्विज़ (VIP)"), types.KeyboardButton("🔒 टाइपिंग स्पीड टेस्ट (VIP)"))
    markup.add(types.KeyboardButton("🔒 डेली करेंट अफेयर्स (VIP)"), types.KeyboardButton("🔒 CV / रिज्यूम बनाएँ (VIP)"))
    markup.add(types.KeyboardButton("🔒 आयु गणक (Age Calc) (VIP)"), types.KeyboardButton("🔒 फ्री PDF लाइब्रेरी (VIP)"))
    markup.add(types.KeyboardButton("🎁 रेफर करें (Link निकालें)"))
    return markup

def get_step_control_keyboard(can_back=True, has_no_photo=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    row = []
    if can_back: row.append(types.KeyboardButton("⬅️ पिछला स्टेप (Back)"))
    row.append(types.KeyboardButton("🗑️ यह इनपुट रद्द करें"))
    markup.add(*row)
    if has_no_photo: markup.add(types.KeyboardButton("🚫 बिना फोटो के ही CV बनाएँ"))
    markup.add(types.KeyboardButton("❌ पूरा प्रोसेस कैंसिल (Cancel)"))
    return markup

def send_task_completion_menu(chat_id, success_text="✅ काम पूरा हुआ! अब अगला विकल्प चुनें 👇"):
    bot.send_message(chat_id, success_text, reply_markup=get_main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_sessions.pop(chat_id, None)

    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref_'):
        try:
            referrer_id = int(args[1].split('_')[1])
            if referrer_id != user_id:
                if record_referral(user_id, referrer_id):
                    count = get_referral_count(referrer_id)
                    bot.send_message(referrer_id, f"🎉 **बधाई!** एक नए दोस्त ने आपके लिंक से जॉइन किया है।\nकुल रेफरल: `{count} / 5`\n\n(5 होते ही सभी VIP टूल्स खुल जाएंगे!)", parse_mode="Markdown")
        except: pass

    if not is_user_subscribed(chat_id, user_id):
        return send_join_channel_prompt(chat_id)

    text = (
        "👋 **ऑल-इन-वन स्टूडेंट सुपर-टूल में आपका स्वागत है!** 🇮🇳\n\n"
        "यहाँ आपको मिलती है:\n"
        "• 📷 **फ्री:** फोटो रिसाइज़र व नेम-डेट स्टैम्प\n"
        "• 🔒 **VIP:** अनलिमिटेड क्विज़, टाइपिंग, CV मेकर, PDF नोट्स\n\n"
        "*(VIP टूल्स अनलॉक करने के लिए 5 दोस्तों को रेफर करें)*\n\n"
        "नीचे दिए गए मेनू से अपनी सेवा चुनें 👇"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_main_menu())

# ==========================================
# 6. आयु गणक (Age Calculator) [Premium]
# ==========================================
def calculate_age(dob, target):
    try:
        d1 = datetime.strptime(dob, "%d/%m/%Y")
        d2 = datetime.now() if target in ["आज", "today", "aaj"] else datetime.strptime(target, "%d/%m/%Y")
        if d1 > d2: return "❌ जन्मतिथि लक्ष्य तिथि से आगे नहीं हो सकती।"
        years, months, days = d2.year - d1.year, d2.month - d1.month, d2.day - d1.day
        if days < 0: months -= 1; days += 30
        if months < 0: years -= 1; months += 12
        return f"✅ **आपकी आयु:** `{years} वर्ष, {months} महीने, और {days} दिन` है।"
    except: return "❌ तारीख का फॉर्मेट गलत है। कृपया **DD/MM/YYYY** (उदा: 15/08/2002) में भेजें।"

# ==========================================
# 7. फोटो रिसाइज़र व नेम-डेट स्टैम्पर (FREE)
# ==========================================
def resize_to_target_kb(image, max_kb, target_width):
    w_percent = (target_width / float(image.size[0]))
    h_size = int((float(image.size[1]) * float(w_percent)))
    img_resized = image.resize((target_width, h_size), Image.Resampling.LANCZOS)
    quality = 90
    while quality >= 10:
        buf = io.BytesIO()
        img_resized.save(buf, format="JPEG", quality=quality, optimize=True)
        size_kb = len(buf.getvalue()) / 1024
        if size_kb <= max_kb: return buf.getvalue(), size_kb
        quality -= 5
    img_resized = img_resized.resize((int(target_width*0.75), int(h_size*0.75)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img_resized.save(buf, format="JPEG", quality=65, optimize=True)
    return buf.getvalue(), len(buf.getvalue()) / 1024

@bot.callback_query_handler(func=lambda call: call.data.startswith("res_"))
def process_resize_callback(call):
    chat_id = call.message.chat.id
    session = user_sessions.get(chat_id, {})
    if 'temp_photo' not in session: return bot.answer_callback_query(call.id, "कृपया फोटो दोबारा भेजें।")
    msg = bot.send_message(chat_id, "⏳ प्रोसेसिंग...")
    try:
        image = Image.open(io.BytesIO(session['temp_photo'])).convert("RGB")
        target = call.data
        if target == "res_sign": final_bytes, size_kb = resize_to_target_kb(image, 19, 300); tag = "सिग्नेचर"
        elif target == "res_photo": final_bytes, size_kb = resize_to_target_kb(image, 48, 450); tag = "पासपोर्ट फोटो"
        elif target == "res_doc": final_bytes, size_kb = resize_to_target_kb(image, 95, 800); tag = "डॉक्यूमेंट"
        else: final_bytes, size_kb = resize_to_target_kb(image, 190, 1100); tag = "डॉक्यूमेंट"

        out_file = io.BytesIO(final_bytes)
        out_file.name = "Sarkari_Ready.jpg"
        bot.send_document(chat_id, out_file, caption=f"✅ **{tag} तैयार!**\n📏 साइज़: `{size_kb:.1f} KB`", parse_mode="Markdown")
        bot.delete_message(chat_id, msg.message_id)
        session.clear()
        send_task_completion_menu(chat_id)
    except Exception as e: bot.edit_message_text(f"❌ एरर: {e}", chat_id, msg.message_id)

def apply_name_and_date(image_bytes, name, date_text):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    strip_height = max(int(height * 0.18), 70)
    new_image = Image.new("RGB", (width, height + strip_height), "white")
    new_image.paste(image, (0, 0))
    draw = ImageDraw.Draw(new_image)
    name_str = name.strip().upper()
    date_str = date_text.strip().upper()
    date_display = date_str if date_str.startswith(("DOB", "DOP", "DATE")) else f"DOP: {date_str}"
    
    font_size = int(strip_height * 0.36)
    font = ImageFont.load_default()
    try: font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
    except: pass

    bbox1 = draw.textbbox((0, 0), f"NAME: {name_str}", font=font)
    bbox2 = draw.textbbox((0, 0), date_display, font=font)
    w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
    w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]
    x1, x2 = (width - w1) // 2, (width - w2) // 2
    start_y = height + ((strip_height - (h1 + h2 + 8)) // 2)

    draw.text((x1, start_y), f"NAME: {name_str}", fill=(0, 0, 0), font=font)
    draw.text((x2, start_y + h1 + 8), date_display, fill=(0, 0, 0), font=font)
    draw.line([(0, height), (width, height)], fill=(200, 200, 200), width=1)
    buf = io.BytesIO()
    new_image.save(buf, format="JPEG", quality=95)
    return buf.getvalue()

# ==========================================
# 8. अनलिमिटेड हिंदी/इंग्लिश क्विज़ इंजन [Premium]
# ==========================================
user_lang_pref = {}
active_quiz_cache = {}
user_seen_history = {}

CATEGORY_MAP = {
    "ssc": {"cat_id": 9, "title_hi": "SSC (GK)", "title_en": "SSC"},
    "railway": {"cat_id": 17, "title_hi": "रेलवे (Science)", "title_en": "Railway"},
    "vyapam": {"cat_id": 23, "title_hi": "MP पटवारी/व्यापमं", "title_en": "MP Vyapam"},
    "police": {"cat_id": 22, "title_hi": "पुलिस भर्ती", "title_en": "Police"},
    "bank": {"cat_id": 9, "title_hi": "बैंकिंग", "title_en": "Banking"},
    "upsc": {"cat_id": 24, "title_hi": "UPSC / PCS", "title_en": "UPSC"}
}

EMERGENCY_BANK = {
    "ssc": [{"q": "संविधान की किस अनुसूची में भाषाएं हैं?", "options": ["7वीं", "8वीं", "9वीं", "10वीं"], "correct": 1}],
    "railway": [{"q": "ध्वनि की चाल सबसे अधिक किसमें होती है?", "options": ["हवा", "जल", "ठोस", "निर्वात"], "correct": 2}],
    "vyapam": [{"q": "तानसेन समारोह कहाँ होता है?", "options": ["भोपाल", "उज्जैन", "ग्वालियर", "इंदौर"], "correct": 2}],
    "police": [{"q": "काजीरंगा उद्यान किस राज्य में है?", "options": ["असम", "MP", "UP", "उत्तराखंड"], "correct": 0}],
    "bank": [{"q": "RBI की स्थापना वर्ष?", "options": ["1935", "1947", "1950", "1969"], "correct": 0}],
    "upsc": [{"q": "राष्ट्रीय कांग्रेस के प्रथम अध्यक्ष?", "options": ["बनर्जी", "नौरोजी", "ह्यूम", "तैयबजी"], "correct": 0}]
}

def is_mostly_hindi(text): return len([c for c in text if '\u0900' <= c <= '\u097F']) > 2

def unblockable_hindi_translator(text):
    if not text: return ""
    try:
        url = "https://clients5.google.com/translate_a/t"
        r = requests.get(url, params={"client": "dict-chrome-ex", "sl": "en", "tl": "hi", "q": text}, timeout=3)
        if r.status_code == 200 and isinstance(r.json(), list):
            out = html.unescape(r.json()[0])
            if is_mostly_hindi(out): return out
    except: pass
    return None

def fetch_quiz_question(chat_id, category, lang="hi"):
    cat_info = CATEGORY_MAP.get(category, CATEGORY_MAP["ssc"])
    user_seen = user_seen_history.setdefault(chat_id, {}).setdefault(category, set())
    api_url = f"https://opentdb.com/api.php?amount=1&category={cat_info['cat_id']}&type=multiple"

    if lang == "en":
        try:
            res = requests.get(api_url, timeout=4)
            data = res.json()
            item = data["results"][0]
            opts = [html.unescape(a) for a in item["incorrect_answers"]] + [html.unescape(item["correct_answer"])]
            random.shuffle(opts)
            return {"q": html.unescape(item["question"]), "options": opts, "correct": opts.index(html.unescape(item["correct_answer"])), "year": cat_info['title_en']}
        except: pass

    if lang == "hi":
        for _ in range(4):
            try:
                res = requests.get(api_url, timeout=4)
                item = res.json()["results"][0]
                hi_q = unblockable_hindi_translator(html.unescape(item["question"]))
                if hi_q and hi_q not in user_seen:
                    raw_correct = html.unescape(item["correct_answer"])
                    raw_wrongs = [html.unescape(a) for a in item["incorrect_answers"]]
                    hi_correct = unblockable_hindi_translator(raw_correct)
                    hi_wrongs = [unblockable_hindi_translator(w) for w in raw_wrongs]
                    if hi_correct and all(hi_wrongs):
                        user_seen.add(hi_q)
                        opts = hi_wrongs + [hi_correct]
                        random.shuffle(opts)
                        return {"q": hi_q, "options": opts, "correct": opts.index(hi_correct), "year": cat_info['title_hi']}
            except: time.sleep(0.5)

    pool = EMERGENCY_BANK.get(category, EMERGENCY_BANK["ssc"])
    selected = random.choice(pool)
    opts = list(selected["options"])
    random.shuffle(opts)
    return {"q": selected["q"], "options": opts, "correct": opts.index(selected["options"][selected["correct"]]), "year": cat_info['title_hi']}

def send_language_selection_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🇮🇳 हिंदी", callback_data="qlang_hi"), types.InlineKeyboardButton("🇬🇧 English", callback_data="qlang_en"))
    bot.send_message(chat_id, "🌐 **क्विज़ के लिए भाषा चुनें:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("qlang_"))
def handle_language_choice(call):
    chat_id = call.message.chat.id
    user_lang_pref[chat_id] = call.data.split("_")[1]
    bot.delete_message(chat_id, call.message.message_id)
    send_exam_category_menu(chat_id)

def send_exam_category_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🏛️ SSC", callback_data="qcat_ssc"), types.InlineKeyboardButton("🚆 Railway", callback_data="qcat_railway"))
    markup.add(types.InlineKeyboardButton("🌾 Patwari/Vyapam", callback_data="qcat_vyapam"), types.InlineKeyboardButton("👮 Police", callback_data="qcat_police"))
    markup.add(types.InlineKeyboardButton("🏦 Banking", callback_data="qcat_bank"), types.InlineKeyboardButton("🇮🇳 UPSC", callback_data="qcat_upsc"))
    markup.add(types.InlineKeyboardButton("🏁 मुख्य मेनू", callback_data="qcat_main"))
    bot.send_message(chat_id, "📚 **परीक्षा चुनें (Unlimited Practice):**", reply_markup=markup, parse_mode="Markdown")

def send_category_question(chat_id, category):
    q_data = fetch_quiz_question(chat_id, category, user_lang_pref.get(chat_id, "hi"))
    active_quiz_cache[chat_id] = q_data
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, opt in enumerate(q_data["options"]): markup.add(types.InlineKeyboardButton(opt, callback_data=f"qz_{category}_{i}"))
    bot.send_message(chat_id, f"🎯 **{q_data['year']}**\n\n❓ {q_data['q']}", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("qcat_"))
def handle_quiz_category(call):
    chat_id = call.message.chat.id
    cat = call.data.split("_")[1]
    bot.delete_message(chat_id, call.message.message_id)
    if cat == "main": send_task_completion_menu(chat_id)
    else: send_category_question(chat_id, cat)

@bot.callback_query_handler(func=lambda call: call.data.startswith("qz_"))
def process_quiz_answer(call):
    chat_id = call.message.chat.id
    parts = call.data.split("_")
    if parts[1] == "next":
        bot.answer_callback_query(call.id, "नया प्रश्न...")
        return send_category_question(chat_id, parts[2])
    elif parts[1] == "change":
        bot.delete_message(chat_id, call.message.message_id)
        return send_exam_category_menu(chat_id)
    elif parts[1] == "finish":
        bot.delete_message(chat_id, call.message.message_id)
        return send_task_completion_menu(chat_id, "🏆 शानदार अभ्यास!")

    cat, opt_idx = parts[1], int(parts[2])
    q_data = active_quiz_cache.get(chat_id)
    if not q_data: return
    
    is_corr = (opt_idx == q_data["correct"])
    res = "🎉 **बिल्कुल सही!**" if is_corr else f"❌ **गलत!**\n✅ सही: `{q_data['options'][q_data['correct']]}`"
    
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("➡️ अगला प्रश्न", callback_data=f"qz_next_{cat}"), types.InlineKeyboardButton("🔄 परीक्षा बदलें", callback_data="qz_change"), types.InlineKeyboardButton("🏁 समाप्त", callback_data="qz_finish"))
    bot.edit_message_text(f"{call.message.text}\n\n━━━━━━━━━\n{res}", chat_id, call.message.message_id, reply_markup=m, parse_mode="Markdown")

# ==========================================
# 9. PDF CV जनरेटर [Premium]
# ==========================================
def is_valid_input(val): return val and val.strip().lower() not in ['na', 'n/a', 'no', 'none', '-']
def generate_full_resume_pdf(data):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=14, leftMargin=14, topMargin=14, bottomMargin=14)
    story = []
    
    nm = ParagraphStyle('Nm', fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor("#0F172A"))
    lb = ParagraphStyle('Lb', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#E2E8F0"))
    rb = ParagraphStyle('Rb', fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#334155"))
    sh_r = ParagraphStyle('SR', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0F172A"), spaceAfter=5)
    sh_l = ParagraphStyle('SL', fontName='Helvetica-Bold', fontSize=11, textColor=colors.white, spaceAfter=5)

    left_el = [Paragraph("CONTACT INFO", sh_l), Paragraph(f"<b>Phone:</b> {data.get('phone','N/A')}", lb), Paragraph(f"<b>Email:</b> {data.get('email','N/A')}", lb), Paragraph(f"<b>Address:</b> {data.get('address','India')}", lb), Spacer(1,10)]
    left_el += [Paragraph("KEY SKILLS", sh_l), Paragraph(data.get('skills', ''), lb), Spacer(1,10)]
    left_el += [Paragraph("PERSONAL", sh_l), Paragraph(f"<b>Father:</b> {data.get('father','')}", lb), Paragraph(f"<b>DOB:</b> {data.get('dob','')}", lb)]

    right_el = [Paragraph(data.get('name', 'NAME').upper(), nm), Spacer(1, 10)]
    right_el += [Paragraph("EXPERIENCE", sh_r), Paragraph(data.get('exp', 'Fresher'), rb), Spacer(1, 10)]
    right_el += [Paragraph("ACADEMICS", sh_r)]
    
    ed_data = [["Course", "Board/University", "Score"]]
    if is_valid_input(data.get('pg_course')): ed_data.append([data['pg_course'], data.get('pg_board',''), data.get('pg_score','')])
    if is_valid_input(data.get('ug_course')): ed_data.append([data['ug_course'], data.get('ug_board',''), data.get('ug_score','')])
    if is_valid_input(data.get('edu_12th_board')): ed_data.append(["12th", data.get('edu_12th_board',''), data.get('edu_12th_score','')])
    if is_valid_input(data.get('edu_10th_board')): ed_data.append(["10th", data.get('edu_10th_board',''), data.get('edu_10th_score','')])
    
    t = Table(ed_data, colWidths=[120, 165, 95])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E293B")), ('TEXTCOLOR',(0,0),(-1,0),colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    right_el.append(t)

    master = Table([[left_el, right_el]], colWidths=[185, 395])
    master.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor("#0F172A")), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(master)
    doc.build(story)
    return pdf_buffer.getvalue()

def deliver_cv_pdf(chat_id, rdata):
    msg = bot.send_message(chat_id, "⏳ **CV तैयार किया जा रहा है...**")
    try:
        pdf_bytes = generate_full_resume_pdf(rdata)
        out_pdf = io.BytesIO(pdf_bytes)
        out_pdf.name = f"{rdata.get('name', 'Resume')}.pdf"
        bot.send_document(chat_id, out_pdf, caption="🎉 **आपका CV तैयार है!**")
        bot.delete_message(chat_id, msg.message_id)
        send_task_completion_menu(chat_id)
    except Exception as e: bot.edit_message_text(f"❌ त्रुटि: {e}", chat_id, msg.message_id)

# ==========================================
# 10. टेक्स्ट और नेविगेशन
# ==========================================
@bot.message_handler(commands=['cancel', 'stop'])
def handle_cancel_cmd(message):
    user_sessions.pop(message.chat.id, None)
    send_task_completion_menu(message.chat.id, "🚫 **कैंसिल किया गया!**")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id, user_id, txt = message.chat.id, message.from_user.id, message.text.strip()
    session, mode, step = user_sessions.setdefault(chat_id, {}), user_sessions.get(chat_id, {}).get('mode'), user_sessions.get(chat_id, {}).get('step')

    if not is_user_subscribed(chat_id, user_id): return send_join_channel_prompt(chat_id)
    if txt in ["❌ पूरा प्रोसेस कैंसिल (Cancel)", "cancel", "stop"]: session.clear(); return send_task_completion_menu(chat_id, "🚫 **कैंसिल!**")

    # ================== FREE TOOLS ==================
    if txt == "📐 फोटो / साइन रिसाइज़र":
        session.clear(); session['mode'] = 'resizer'
        bot.send_message(chat_id, "📷 वह **फोटो/साइन** भेजें जिसे रिसाइज़ करना है:", reply_markup=get_step_control_keyboard(False))
        return
    elif txt == "🏷️ फोटो पर नाम व तारीख":
        session.clear(); session['mode'], session['step'] = 'name_date', 'wait_photo'
        bot.send_message(chat_id, "📷 अपनी **पासपोर्ट फोटो** भेजें:", reply_markup=get_step_control_keyboard(False))
        return

    # ================== REFERRAL LINK GENERATOR ==================
    elif txt == "🎁 रेफर करें (Link निकालें)":
        try:
            bot_usr = bot.get_me().username
            link = f"https://t.me/{bot_usr}?start=ref_{user_id}"
            refs = get_referral_count(user_id)
            bot.send_message(
                chat_id, 
                f"🎁 **Refer & Earn (अनलॉक VIP टूल्स)**\n\n"
                f"अपने दोस्तों को यह लिंक भेजें। **5 दोस्त** जॉइन करते ही क्विज़, टाइपिंग, CV मेकर और सभी VIP टूल्स जीवन भर के लिए खुल जाएंगे!\n\n"
                f"📊 **आपके वर्तमान रेफरल:** `{refs} / 5`\n\n"
                f"🔗 **इसे कॉपी करके शेयर करें:**\n`{link}`", 
                parse_mode="Markdown"
            )
        except: bot.send_message(chat_id, "❌ लिंक निकालने में त्रुटि। कृपया थोड़ी देर बाद प्रयास करें।")
        return

    # ================== VIP (LOCKED) TOOLS ==================
    elif txt == "🔒 सरकारी एग्जाम क्विज़ (VIP)":
        if not check_premium(chat_id, user_id): return
        session.clear(); send_language_selection_menu(chat_id); return

    elif txt == "🔒 टाइपिंग स्पीड टेस्ट (VIP)":
        if not check_premium(chat_id, user_id): return
        session['mode'] = 'typing'
        test_txt = "Government exams require speed and accuracy."
        session['typ_txt'] = test_txt
        session['typ_start'] = time.time()
        bot.send_message(chat_id, f"⌨️ **टाइपिंग टेस्ट शुरू!**\n\nनीचे दिए गए वाक्य को बिल्कुल वैसा ही टाइप करके भेजें:\n\n`{test_txt}`", parse_mode="Markdown")
        return

    elif txt == "🔒 डेली करेंट अफेयर्स (VIP)":
        if not check_premium(chat_id, user_id): return
        ca_text = "📰 **आज के करेंट अफेयर्स (Top 5)**\n\n1. सरकार ने नई भर्ती योजनाओं की घोषणा की।\n2. RBI ने ब्याज दरों में बदलाव किए।\n3. भारत का नया सैटेलाइट लॉन्च सफल रहा।\n4. आगामी SSC परीक्षाओं के लिए नया कैलेंडर जारी।\n5. एशियन गेम्स में भारत का शानदार प्रदर्शन।\n*(रोजाना नए अपडेट यहाँ मिलेंगे!)*"
        bot.send_message(chat_id, ca_text, parse_mode="Markdown")
        return

    elif txt == "🔒 CV / रिज्यूम बनाएँ (VIP)":
        if not check_premium(chat_id, user_id): return
        session.clear()
        session['mode'], session['step'], session['history'], session['rdata'] = 'resume', 's_name', [], {}
        bot.send_message(chat_id, "💼 **CV मेकर शुरू!**\n" + STEP_PROMPTS['s_name'], reply_markup=get_step_control_keyboard(False))
        return

    elif txt == "🔒 आयु गणक (Age Calc) (VIP)":
        if not check_premium(chat_id, user_id): return
        session['mode'], session['step'] = 'age_calc', 'dob'
        bot.send_message(chat_id, "📅 **आयु गणक**\n\nअपनी जन्मतिथि (DOB) भेजें (उदा: `15/08/2002`):", parse_mode="Markdown")
        return

    elif txt == "🔒 फ्री PDF लाइब्रेरी (VIP)":
        if not check_premium(chat_id, user_id): return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📘 इतिहास (History)", callback_data="pdf_hist"), types.InlineKeyboardButton("📗 विज्ञान (Science)", callback_data="pdf_sci"))
        bot.send_message(chat_id, "📚 **PDF लाइब्रेरी** (VIP Access)\nविषय चुनें:", reply_markup=markup)
        return

    # मोड प्रोसेसिंग
    if mode == 'typing':
        elapsed = time.time() - session['typ_start']
        words = len(txt.split())
        wpm = int((words / elapsed) * 60) if elapsed > 0 else 0
        acc = "100%" if txt.strip() == session['typ_txt'] else "Mistakes Found"
        bot.send_message(chat_id, f"📊 **टाइपिंग रिजल्ट:**\n\n⏱️ समय: `{int(elapsed)} सेकंड`\n⚡ स्पीड: `{wpm} WPM`\n🎯 एक्यूरेसी: `{acc}`", parse_mode="Markdown")
        session.clear()

    elif mode == 'age_calc':
        if step == 'dob':
            session['dob'] = txt; session['step'] = 'target'
            bot.send_message(chat_id, "🎯 अब **किस तारीख तक** आयु निकालनी है? (उदा: `01/01/2024` या `आज` लिखें):", parse_mode="Markdown")
        elif step == 'target':
            bot.send_message(chat_id, calculate_age(session['dob'], txt), parse_mode="Markdown")
            session.clear(); send_task_completion_menu(chat_id)

    elif mode == 'name_date':
        if txt == "🗑️ यह इनपुट रद्द करें": return bot.send_message(chat_id, "✍️ इनपुट रीसेट।")
        if txt == "⬅️ पिछला स्टेप (Back)":
            if step == 'wait_date': session['step'] = 'wait_name'; return bot.send_message(chat_id, "⬅️ अपना **पूरा नाम** दोबारा लिखें:")
        if step == 'wait_name':
            session['nd_name'] = txt; session['step'] = 'wait_date'
            bot.send_message(chat_id, "📅 अब फोटो की तारीख भेजें (उदा: `10/09/2026`):")
        elif step == 'wait_date':
            if session.get('nd_photo'):
                out = io.BytesIO(apply_name_and_date(session['nd_photo'], session.get('nd_name', ''), txt))
                out.name = "Ready.jpg"
                bot.send_document(chat_id, out, caption="✅ **फोटो तैयार!**")
                session.clear(); send_task_completion_menu(chat_id)

    elif mode == 'resume':
        hist, r = session.setdefault('history', []), session.setdefault('rdata', {})
        if txt == "🗑️ यह इनपुट रद्द करें": return bot.send_message(chat_id, f"🗑️ {STEP_PROMPTS.get(step)}", reply_markup=get_step_control_keyboard(len(hist)>0, step=='s_photo'))
        if txt == "⬅️ पिछला स्टेप (Back)":
            if hist:
                session['step'] = hist.pop()
                return bot.send_message(chat_id, f"⬅️ {STEP_PROMPTS.get(session['step'])}")
            return
        if txt == "🚫 बिना फोटो के ही CV बनाएँ" and step == 's_photo': return deliver_cv_pdf(chat_id, r)

        c_step = step
        hist.append(c_step)

        if c_step == 's_name': r['name'] = txt; session['step'] = 's_phone'
        elif c_step == 's_phone': r['phone'] = txt; session['step'] = 's_email'
        elif c_step == 's_email': r['email'] = txt; session['step'] = 's_address'
        elif c_step == 's_address': r['address'] = txt; session['step'] = 's_father'
        elif c_step == 's_father': r['father'] = txt; session['step'] = 's_dob'
        elif c_step == 's_dob': r['dob'] = txt; session['step'] = 's_pg_course'
        elif c_step == 's_pg_course': 
            if is_valid_input(txt): r['pg_course'] = txt; session['step'] = 's_pg_board'
            else: session['step'] = 's_ug_course'
        elif c_step == 's_pg_board': r['pg_board'] = txt; session['step'] = 's_pg_score'
        elif c_step == 's_pg_score': r['pg_score'] = txt; session['step'] = 's_ug_course'
        elif c_step == 's_ug_course':
            if is_valid_input(txt): r['ug_course'] = txt; session['step'] = 's_ug_board'
            else: session['step'] = 's_dip_course'
        elif c_step == 's_ug_board': r['ug_board'] = txt; session['step'] = 's_ug_score'
        elif c_step == 's_ug_score': r['ug_score'] = txt; session['step'] = 's_dip_course'
        elif c_step == 's_dip_course':
            if is_valid_input(txt): r['dip_course'] = txt; session['step'] = 's_dip_board'
            else: session['step'] = 's_12th_board'
        elif c_step == 's_dip_board': r['dip_board'] = txt; session['step'] = 's_dip_score'
        elif c_step == 's_dip_score': r['dip_score'] = txt; session['step'] = 's_12th_board'
        elif c_step == 's_12th_board':
            if is_valid_input(txt): r['edu_12th_board'] = txt; session['step'] = 's_12th_score'
            else: session['step'] = 's_10th_board'
        elif c_step == 's_12th_score': r['edu_12th_score'] = txt; session['step'] = 's_10th_board'
        elif c_step == 's_10th_board': r['edu_10th_board'] = txt; session['step'] = 's_10th_score'
        elif c_step == 's_10th_score': r['edu_10th_score'] = txt; session['step'] = 's_skills'
        elif c_step == 's_skills': r['skills'] = txt; session['step'] = 's_exp'
        elif c_step == 's_exp': r['exp'] = txt; session['step'] = 's_certs'
        elif c_step == 's_certs': r['certs'] = txt; session['step'] = 's_photo'

        bot.send_message(chat_id, STEP_PROMPTS.get(session['step'], "अगला विवरण:"), reply_markup=get_step_control_keyboard(True, session['step']=='s_photo'))

@bot.callback_query_handler(func=lambda call: call.data.startswith("pdf_"))
def handle_pdf_download(call):
    bot.answer_callback_query(call.id, "यह एक डेमो PDF है।", show_alert=True)

@bot.message_handler(content_types=['photo', 'document'])
def handle_photos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    if not is_user_subscribed(chat_id, user_id): return send_join_channel_prompt(chat_id)
    
    session, mode, step = user_sessions.setdefault(chat_id, {}), user_sessions.get(chat_id, {}).get('mode'), user_sessions.get(chat_id, {}).get('step')
    fid = message.photo[-1].file_id if message.content_type == 'photo' else message.document.file_id
    down = bot.download_file(bot.get_file(fid).file_path)

    if mode == 'name_date' and step == 'wait_photo':
        session['nd_photo'], session['step'] = down, 'wait_name'
        bot.send_message(chat_id, "✍️ अपना **पूरा नाम** लिखें:", reply_markup=get_step_control_keyboard())
    elif mode == 'resume' and (step == 's_photo' or 'rdata' in session):
        session.setdefault('rdata', {})['photo'] = down
        deliver_cv_pdf(chat_id, session['rdata'])
    else:
        session['temp_photo'] = down
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("📷 पासपोर्ट (20-50 KB)", callback_data="res_photo"), types.InlineKeyboardButton("✍️ साइन (10-20 KB)", callback_data="res_sign"))
        markup.add(types.InlineKeyboardButton("📄 डॉक्यूमेंट (50-100 KB)", callback_data="res_doc"), types.InlineKeyboardButton("📁 हैवी डॉक (100-200 KB)", callback_data="res_heavy"))
        bot.reply_to(message, "⚙️ **किस साइज़ में कन्वर्ट करना है?**", reply_markup=markup)

# ==========================================
# 11. मुख्य रनर
# ==========================================
if __name__ == '__main__':
    threading.Thread(target=job_alert_scheduler, daemon=True).start()
    for attempt in range(5):
        try:
            bot.remove_webhook()
            time.sleep(2)
            bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
            print(f"🚀 Master Bot Engine active at {WEBHOOK_URL}")
            break
        except Exception as e: time.sleep(5)

    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
