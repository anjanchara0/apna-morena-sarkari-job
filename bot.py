import os
import io
import time
import threading
import telebot
from telebot import types
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request
import feedparser
import requests
from bs4 import BeautifulSoup

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. कॉन्फ़िगरेशन
# ==========================================
BOT_TOKEN = "8526721171:AAEJy5j04q3zB-rBcywxwxIjyKFGVzef24Q"
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
    return "✅ Master Student Platform Engine Live 24/7!", 200

# ==========================================
# 3. ऑल-इंडिया डायरेक्ट फॉर्म + हिंदी न्यूज़ इंजन
# ==========================================
sent_jobs = set()

def fetch_sarkari_result_direct():
    url = "https://www.sarkariresult.com/latestjob/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            post_div = soup.find('div', id='post')
            if post_div:
                links = post_div.find_all('a')
                for a in links[:3]:
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
                        time.sleep(2)
    except Exception as e:
        print(f"Direct Scraping Error: {e}")

def fetch_all_india_hindi_news():
    hindi_channels_rss = [
        "https://news.google.com/rss/search?q=सरकारी+नौकरी+भर्ती+when:1d&hl=hi&gl=IN&ceid=IN:hi",
        "https://news.google.com/rss/search?q=SSC+रेलवे+UPSC+भर्ती+when:1d&hl=hi&gl=IN&ceid=IN:hi",
        "https://news.google.com/rss/search?q=पुलिस+कांस्टेबल+शिक्षक+भर्ती+when:1d&hl=hi&gl=IN&ceid=IN:hi"
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
                        f"👉 **पूरी खबर व जानकारी:**\n{entry.link}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ सबसे तेज़ और सही अपडेट्स के लिए शेयर करें!"
                    )
                    bot.send_message(CHANNEL_ID, msg)
                    time.sleep(2)
        except Exception as e:
            print(f"Hindi News Error: {e}")

def job_alert_scheduler():
    time.sleep(15)
    fetch_sarkari_result_direct()
    fetch_all_india_hindi_news()
    while True:
        time.sleep(600)
        fetch_sarkari_result_direct()
        fetch_all_india_hindi_news()

# ==========================================
# 4. इन-मेमोरी स्टेट और मेन मेनू
# ==========================================
user_sessions = {}

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton("📐 फोटो / सिग्नेचर रिसाइज़र")
    b2 = types.KeyboardButton("🏷️ फोटो पर नाम व तारीख प्रिंट करें")
    b3 = types.KeyboardButton("📄 प्रोफेशनल रिज्यूम / CV बनाएँ")
    b4 = types.KeyboardButton("🧠 सरकारी एग्जाम डेली क्विज़")
    markup.add(b1, b2, b3, b4)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 **ऑल-इन-वन स्टूडेंट सुपर-टूल में आपका स्वागत है!** 🇮🇳\n\n"
        "यहाँ आपको सरकारी और प्राइवेट करियर की हर सुविधा मिलती है:\n"
        "• 📷 सटीक KB में फोटो/साइन रिसाइज़ करें\n"
        "• 🏷️ फोटो पर नाम व तारीख प्रिंट करें\n"
        "• 📄 स्टेप-बाय-स्टेप आधुनिक 2-कॉलम CV मेकर\n"
        "• 🧠 डेली परीक्षा टेस्ट क्विज़\n\n"
        "नीचे दिए गए मेनू से अपनी सेवा चुनें 👇"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=get_main_menu())

# ==========================================
# 5. फीचर 1: इमेज और सिग्नेचर रिसाइज़र
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
        if size_kb <= max_kb:
            return buf.getvalue(), size_kb
        quality -= 5

    img_resized = img_resized.resize((int(target_width * 0.75), int(h_size * 0.75)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img_resized.save(buf, format="JPEG", quality=65, optimize=True)
    return buf.getvalue(), len(buf.getvalue()) / 1024

@bot.callback_query_handler(func=lambda call: call.data.startswith("res_"))
def process_resize_callback(call):
    chat_id = call.message.chat.id
    session = user_sessions.get(chat_id, {})
    if 'temp_photo' not in session:
        bot.answer_callback_query(call.id, "कृपया फोटो दोबारा भेजें।")
        return

    bot.answer_callback_query(call.id, "प्रोसेसिंग...")
    msg = bot.send_message(chat_id, "⏳ सटीक KB में तैयार किया जा रहा है...")

    try:
        image = Image.open(io.BytesIO(session['temp_photo'])).convert("RGB")
        target = call.data
        if target == "res_sign":
            final_bytes, size_kb = resize_to_target_kb(image, max_kb=19, target_width=300)
            tag = "सिग्नेचर (10-20 KB)"
        elif target == "res_photo":
            final_bytes, size_kb = resize_to_target_kb(image, max_kb=48, target_width=450)
            tag = "पासपोर्ट फोटो (20-50 KB)"
        elif target == "res_doc":
            final_bytes, size_kb = resize_to_target_kb(image, max_kb=95, target_width=800)
            tag = "डॉक्यूमेंट (50-100 KB)"
        else:
            final_bytes, size_kb = resize_to_target_kb(image, max_kb=190, target_width=1100)
            tag = "डॉक्यूमेंट (100-200 KB)"

        out_file = io.BytesIO(final_bytes)
        out_file.name = "Sarkari_Ready.jpg"
        bot.send_document(chat_id, out_file, caption=f"✅ **{tag} तैयार है!**\n📏 साइज़: `{size_kb:.1f} KB`", parse_mode="Markdown")
        bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ एरर: {e}", chat_id, msg.message_id)

# ==========================================
# 6. फीचर 2: फोटो पर नाम व तारीख प्रिंटर
# ==========================================
def apply_name_and_date(image_bytes, name, date_text):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    
    strip_height = int(height * 0.20)
    new_image = Image.new("RGB", (width, height + strip_height), "white")
    new_image.paste(image, (0, 0))
    
    draw = ImageDraw.Draw(new_image)
    font = ImageFont.load_default()
    
    draw.text((int(width * 0.08), height + int(strip_height * 0.15)), f"NAME: {name.upper()}", fill="black", font=font)
    draw.text((int(width * 0.08), height + int(strip_height * 0.55)), f"DATE: {date_text}", fill="black", font=font)
    
    buf = io.BytesIO()
    new_image.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

# ==========================================
# 7. फीचर 3: डेली सरकारी एग्जाम क्विज़
# ==========================================
quiz_bank = [
    {
        "q": "भारत में 'राष्ट्रीय युवा दिवस' किस महापुरुष की स्मृति में मनाया जाता है?",
        "options": ["स्वामी विवेकानंद", "भगत सिंह", "सुभाष चंद्र बोस", "महात्मा गांधी"],
        "correct": 0
    },
    {
        "q": "भारतीय संविधान के किस अनुच्छेद में 'मौलिक अधिकारों' का वर्णन है?",
        "options": ["अनुच्छेद 5 से 11", "अनुच्छेद 12 से 35", "अनुच्छेद 36 से 51", "अनुच्छेद 51A"],
        "correct": 1
    }
]

@bot.callback_query_handler(func=lambda call: call.data.startswith("quiz_"))
def process_quiz_answer(call):
    _, q_idx, opt_idx = call.data.split("_")
    q_data = quiz_bank[int(q_idx)]
    if int(opt_idx) == q_data["correct"]:
        bot.answer_callback_query(call.id, "🎉 सही उत्तर! बहुत बढ़िया!", show_alert=True)
    else:
        correct_ans = q_data["options"][q_data["correct"]]
        bot.answer_callback_query(call.id, f"❌ गलत उत्तर!\nसही उत्तर है: {correct_ans}", show_alert=True)

# ==========================================
# 8. फीचर 4: आधुनिक डायनामिक 2-कॉलम सीवी इंजन
# ==========================================
def is_valid_input(val):
    if not val:
        return False
    v = val.strip().lower()
    return v not in ['na', 'n/a', 'no', 'nahi', 'none', 'skip', '-', '0']

def generate_full_resume_pdf(data):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, 
        pagesize=letter, 
        rightMargin=14, 
        leftMargin=14, 
        topMargin=14, 
        bottomMargin=14
    )
    story = []
    styles = getSampleStyleSheet()

    name_style = ParagraphStyle('Name', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=colors.HexColor("#0F172A"))
    sub_title_style = ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=colors.HexColor("#0284C7"))
    
    sec_heading_right = ParagraphStyle('SecRight', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor("#0F172A"), spaceAfter=5)
    sec_heading_left = ParagraphStyle('SecLeft', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.white, spaceAfter=5)
    
    left_body = ParagraphStyle('LeftBody', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor("#E2E8F0"))
    right_body = ParagraphStyle('RightBody', fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor("#334155"))
    table_cell = ParagraphStyle('TCell', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor("#1E293B"))
    table_head = ParagraphStyle('THead', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=colors.white)

    # -------------------------------------------------------------
    # बायां कॉलम (Dark Navy Sidebar)
    # -------------------------------------------------------------
    left_elements = []
    
    if 'photo' in data:
        try:
            p_stream = io.BytesIO(data['photo'])
            img = RLImage(p_stream, width=90, height=110)
            left_elements.append(img)
            left_elements.append(Spacer(1, 10))
        except:
            pass

    left_elements.append(Paragraph("CONTACT INFO", sec_heading_left))
    left_elements.append(Paragraph(f"<b>Phone:</b> {data.get('phone', 'N/A')}", left_body))
    left_elements.append(Paragraph(f"<b>Email:</b> {data.get('email', 'N/A')}", left_body))
    left_elements.append(Paragraph(f"<b>Address:</b> {data.get('address', 'India')}", left_body))
    left_elements.append(Spacer(1, 10))

    left_elements.append(Paragraph("KEY SKILLS", sec_heading_left))
    raw_skills = data.get('skills', 'Computer Basic, MS Office, Communication')
    for s in [x.strip() for x in raw_skills.replace(',', '\n').split('\n') if x.strip()]:
        left_elements.append(Paragraph(f"• {s}", left_body))
    left_elements.append(Spacer(1, 10))

    if is_valid_input(data.get('certs')):
        left_elements.append(Paragraph("CERTIFICATIONS", sec_heading_left))
        for c in [x.strip() for x in data['certs'].replace(',', '\n').split('\n') if x.strip()]:
            left_elements.append(Paragraph(f"• {c}", left_body))
        left_elements.append(Spacer(1, 10))

    left_elements.append(Paragraph("PERSONAL DETAILS", sec_heading_left))
    left_elements.append(Paragraph(f"<b>Father:</b> {data.get('father', 'N/A')}", left_body))
    left_elements.append(Paragraph(f"<b>DOB:</b> {data.get('dob', 'N/A')}", left_body))
    left_elements.append(Paragraph(f"<b>Languages:</b> {data.get('lang', 'Hindi, English')}", left_body))
    left_elements.append(Paragraph("<b>Nationality:</b> Indian", left_body))

    # -------------------------------------------------------------
    # दायां कॉलम (Main Content)
    # -------------------------------------------------------------
    right_elements = []
    
    cand_name = data.get('name', 'CANDIDATE NAME').upper()
    right_elements.append(Paragraph(cand_name, name_style))
    right_elements.append(Paragraph("CURRICULUM VITAE / PROFESSIONAL RESUME", sub_title_style))
    right_elements.append(Spacer(1, 8))

    right_elements.append(Paragraph("PROFESSIONAL SUMMARY", sec_heading_right))
    summary_text = (
        "Motivated and detail-oriented candidate seeking an opportunity to leverage academic foundation, "
        "practical skills, and strong work ethic in a progressive organization to achieve professional growth."
    )
    right_elements.append(Paragraph(summary_text, right_body))
    right_elements.append(Spacer(1, 10))

    if is_valid_input(data.get('exp')):
        right_elements.append(Paragraph("WORK EXPERIENCE", sec_heading_right))
        right_elements.append(Paragraph(f"• {data['exp']}", right_body))
        right_elements.append(Spacer(1, 10))

    # योग्यता टेबल (साफ़ 3 कॉलम: Qualification, Board/Univ, Percentage)
    edu_table_data = [
        [Paragraph("Course / Qualification", table_head), Paragraph("Board / University / Institute", table_head), Paragraph("Percentage / Marks", table_head)]
    ]

    # 1. PG
    if is_valid_input(data.get('pg_course')):
        edu_table_data.append([
            Paragraph(f"<b>PG: {data['pg_course']}</b>", table_cell),
            Paragraph(data.get('pg_univ', '-'), table_cell),
            Paragraph(data.get('pg_pct', '-'), table_cell)
        ])

    # 2. Graduation
    if is_valid_input(data.get('grad_course')):
        edu_table_data.append([
            Paragraph(f"<b>Grad: {data['grad_course']}</b>", table_cell),
            Paragraph(data.get('grad_univ', '-'), table_cell),
            Paragraph(data.get('grad_pct', '-'), table_cell)
        ])

    # 3. Diploma / ITI
    if is_valid_input(data.get('dip_course')):
        edu_table_data.append([
            Paragraph(f"<b>Diploma: {data['dip_course']}</b>", table_cell),
            Paragraph(data.get('dip_univ', '-'), table_cell),
            Paragraph(data.get('dip_pct', '-'), table_cell)
        ])

    # 4. 12th
    if is_valid_input(data.get('edu_12th_board')):
        edu_table_data.append([
            Paragraph("<b>12th Standard</b>", table_cell),
            Paragraph(data.get('edu_12th_board', '-'), table_cell),
            Paragraph(data.get('edu_12th_pct', '-'), table_cell)
        ])

    # 5. 10th
    if is_valid_input(data.get('edu_10th_board')):
        edu_table_data.append([
            Paragraph("<b>10th Standard</b>", table_cell),
            Paragraph(data.get('edu_10th_board', '-'), table_cell),
            Paragraph(data.get('edu_10th_pct', '-'), table_cell)
        ])

    if len(edu_table_data) > 1:
        right_elements.append(Paragraph("ACADEMIC QUALIFICATIONS", sec_heading_right))
        edu_table = Table(edu_table_data, colWidths=[125, 175, 85])
        edu_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        right_elements.append(edu_table)
        right_elements.append(Spacer(1, 10))

    right_elements.append(Paragraph("DECLARATION", sec_heading_right))
    right_elements.append(Paragraph("I solemnly declare that the details furnished above are true and correct to the best of my knowledge and belief.", right_body))

    # -------------------------------------------------------------
    # 2-कॉलम मास्टर टेबल
    # -------------------------------------------------------------
    master_table = Table([[left_elements, right_elements]], colWidths=[185, 395])
    master_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#0F172A")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 12),
        ('RIGHTPADDING', (0, 0), (0, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING', (1, 0), (1, -1), 16),
        ('RIGHTPADDING', (1, 0), (1, -1), 8),
    ]))
    
    story.append(master_table)
    doc.build(story)
    return pdf_buffer.getvalue()

# ==========================================
# 9. टेक्स्ट इनपुट्स व स्टेप-बाय-स्टेप फ्लो (Data Never Lost)
# ==========================================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    txt = message.text.strip()
    session = user_sessions.setdefault(chat_id, {})

    if txt == "📐 फोटो / सिग्नेचर रिसाइज़र":
        session['mode'] = 'resizer'
        bot.send_message(chat_id, "📷 कृपया वह **फोटो या सिग्नेचर** भेजें जिसे रिसाइज़ करना है:")
        return

    elif txt == "🏷️ फोटो पर नाम व तारीख प्रिंट करें":
        session['mode'] = 'name_date'
        session['step'] = 'wait_photo'
        bot.send_message(chat_id, "📷 कृपया अपनी **पासपोर्ट फोटो** भेजें:")
        return

    elif txt == "🧠 सरकारी एग्जाम डेली क्विज़":
        q = quiz_bank[0]
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, opt in enumerate(q["options"]):
            markup.add(types.InlineKeyboardButton(opt, callback_data=f"quiz_0_{i}"))
        bot.send_message(chat_id, f"📝 **डेली टेस्ट क्विज़:**\n\n{q['q']}", reply_markup=markup, parse_mode="Markdown")
        return

    elif txt in ["📄 प्रोफेशनल रिज्यूम बनाएँ", "📄 प्रोफेशनल रिज्यूम / CV बनाएँ"]:
        # अगर डेटा पहले से मौजूद है, तो दोबारा पूछने के बजाय ऑप्शन दें
        if 'rdata' in session and session['rdata'].get('name'):
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("🔄 पुरानी डिटेल्स से ही PDF फिर बनाएँ / फोटो बदलें", callback_data="cv_reuse"),
                types.InlineKeyboardButton("🆕 पुरानी डिटेल्स हटाकर बिल्कुल नया CV बनाएँ", callback_data="cv_new_start")
            )
            bot.send_message(chat_id, "💡 आपकी पुरानी डिटेल्स पहले से सेव हैं! आप क्या करना चाहते हैं?", reply_markup=markup)
            return

        session['mode'] = 'resume'
        session['step'] = 's_name'
        session['rdata'] = {}
        bot.send_message(chat_id, "💼 **कंप्लीट CV / रिज्यूम बिल्डर शुरू!**\n\n(नोट: जो चीज़ लागू न हो उस पर बेझिझक **NA** या **No** लिख दें)\n\n👉 सबसे पहले अपना **पूरा नाम (Full Name)** लिखें:")
        return

    mode = session.get('mode')
    step = session.get('step')

    # नाम व तारीख फोटो प्रिंटर फ्लो
    if mode == 'name_date':
        if step == 'wait_name':
            session['nd_name'] = txt
            session['step'] = 'wait_date'
            bot.send_message(chat_id, "📅 अब फोटो खींचने की तारीख भेजें (उदा: `10/09/2026`):", parse_mode="Markdown")
        elif step == 'wait_date':
            photo_bytes = session.get('nd_photo')
            if photo_bytes:
                processed = apply_name_and_date(photo_bytes, session.get('nd_name', ''), txt)
                out = io.BytesIO(processed)
                out.name = "Photo_With_Name_Date.jpg"
                bot.send_document(chat_id, out, caption="✅ **नाम व तारीख वाली फोटो तैयार है!**")
                session.pop('nd_photo', None)

    # संपूर्ण डायनामिक CV फ्लो
    elif mode == 'resume':
        r = session.setdefault('rdata', {})

        if step == 's_name':
            r['name'] = txt
            session['step'] = 's_phone'
            bot.send_message(chat_id, "📱 अपना **मोबाइल नंबर** भेजें:")

        elif step == 's_phone':
            r['phone'] = txt
            session['step'] = 's_email'
            bot.send_message(chat_id, "✉️ अपनी **ईमेल आईडी** भेजें:")

        elif step == 's_email':
            r['email'] = txt
            session['step'] = 's_address'
            bot.send_message(chat_id, "📍 अपना **शहर / पता (Address)** भेजें (उदा: `Morena, MP`):")

        elif step == 's_address':
            r['address'] = txt
            session['step'] = 's_father'
            bot.send_message(chat_id, "👨‍👦 **पिता का नाम (Father's Name)** भेजें:")

        elif step == 's_father':
            r['father'] = txt
            session['step'] = 's_dob'
            bot.send_message(chat_id, "🎂 अपनी **जन्मतिथि (DOB)** भेजें (उदा: `15/08/2002`):")

        elif step == 's_dob':
            r['dob'] = txt
            session['step'] = 's_pg'
            bot.send_message(chat_id, "🎓 **पोस्ट ग्रेजुएशन (Master's / PG):**\nडिग्री, कॉलेज, प्रतिशत लिखें (उदा: `MCA, Jiwaji Univ, 78%`)\n*(नहीं किया है तो **NA** लिखें)*:")

        elif step == 's_pg':
            if is_valid_input(txt):
                parts = [p.strip() for p in txt.split(',')]
                r['pg_course'] = parts[0]
                r['pg_board'] = parts[1] if len(parts) > 1 else "University"
                r['pg_score'] = parts[2] if len(parts) > 2 else "Passed"
            session['step'] = 's_ug'
            bot.send_message(chat_id, "🏛️ **ग्रेजुएशन (Graduation / Degree):**\nकोर्स, यूनिवर्सिटी, प्रतिशत लिखें (उदा: `B.Sc, Jiwaji Univ, 72%`)\n*(नहीं किया है तो **NA** लिखें)*:")

        elif step == 's_ug':
            if is_valid_input(txt):
                parts = [p.strip() for p in txt.split(',')]
                r['ug_course'] = parts[0]
                r['ug_board'] = parts[1] if len(parts) > 1 else "University"
                r['ug_score'] = parts[2] if len(parts) > 2 else "Passed"
            session['step'] = 's_dip'
            bot.send_message(chat_id, "⚙️ **डिप्लोमा / ITI / पॉलिटेक्निक:**\nट्रेड, इंस्टीट्यूट, प्रतिशत (उदा: `ITI COPA, NCVT, 82%`)\n*(नहीं किया है तो **NA** लिखें)*:")

        elif step == 's_dip':
            if is_valid_input(txt):
                parts = [p.strip() for p in txt.split(',')]
                r['dip_course'] = parts[0]
                r['dip_board'] = parts[1] if len(parts) > 1 else "Institute"
                r['dip_score'] = parts[2] if len(parts) > 2 else "Passed"
            session['step'] = 's_12th'
            bot.send_message(chat_id, "📚 **12वीं (12th Standard):**\nबोर्ड और प्रतिशत लिखें (उदा: `MP Board, 75%`)\n*(अगर लागू न हो तो **NA** लिखें)*:")

        elif step == 's_12th':
            if is_valid_input(txt):
                parts = [p.strip() for p in txt.split(',')]
                r['edu_12th_board'] = parts[0]
                r['edu_12th_score'] = parts[1] if len(parts) > 1 else "Passed"
            session['step'] = 's_10th'
            bot.send_message(chat_id, "📖 **10वीं (10th Standard):**\nबोर्ड और प्रतिशत लिखें (उदा: `MP Board, 80%`):")

        elif step == 's_10th':
            if is_valid_input(txt):
                parts = [p.strip() for p in txt.split(',')]
                r['edu_10th_board'] = parts[0]
                r['edu_10th_score'] = parts[1] if len(parts) > 1 else "Passed"
            session['step'] = 's_skills'
            bot.send_message(chat_id, "⚡ अपनी **स्किल्स (Skills)** लिखें:\n(उदा: `MS Office, Tally Prime, Hindi/English Typing, Communication`):")

        elif step == 's_skills':
            r['skills'] = txt
            session['step'] = 's_exp'
            bot.send_message(chat_id, "💼 **कार्य अनुभव (Work Experience):**\n(उदा: `2 Years as Computer Operator` या फ्रेशर हैं तो **Fresher** लिखें):")

        elif step == 's_exp':
            r['exp'] = txt
            session['step'] = 's_certs'
            bot.send_message(chat_id, "📜 **अन्य कोर्सेज / सर्टिफिकेट्स (Certifications):**\n(उदा: `CCC, ADCA, CPCT Qualified` या नहीं है तो **NA** लिखें):")

        elif step == 's_certs':
            r['certs'] = txt
            session['step'] = 's_photo'
            
            # यहाँ छात्र को विकल्प मिलेगा कि फोटो भेजें या बिना फोटो के बनाएँ
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🚫 बिना फोटो के ही CV बनाएँ", callback_data="cv_no_photo"))
            bot.send_message(chat_id, "📷 **अंतिम चरण: अपनी पासपोर्ट फोटो भेजें**\n\n(अगर फोटो नहीं लगाना चाहते तो नीचे बटन दबाएँ):", reply_markup=markup)

# ==========================================
# 10. फोटो व डॉक्यूमेंट हैंडलर (With Smart Recovery)
# ==========================================
def deliver_cv_pdf(chat_id, rdata):
    msg = bot.send_message(chat_id, "⏳ **आपका मॉडर्न 2-कॉलम प्रोफेशनल CV तैयार किया जा रहा है...**")
    try:
        pdf_bytes = generate_full_resume_pdf(rdata)
        out_pdf = io.BytesIO(pdf_bytes)
        out_pdf.name = f"{rdata.get('name', 'Professional')}_CV.pdf"
        
        # बटन जिससे दोबारा कभी पूरा फॉर्म न भरना पड़े!
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔄 दूसरी फोटो लगाकर नया PDF निकालें", callback_data="cv_change_photo"),
            types.InlineKeyboardButton("🚫 फोटो हटाकर सिंपल PDF निकालें", callback_data="cv_no_photo"),
            types.InlineKeyboardButton("🆕 किसी दूसरे व्यक्ति का CV बनाएँ", callback_data="cv_new_start")
        )
        bot.send_document(chat_id, out_pdf, caption="🎉 **आपका संपूर्ण प्रोफेशनल CV (PDF) तैयार है!**\n\n💡 अगर फोटो बदलना चाहें तो नीचे दिए बटन से तुरंत बदल सकते हैं, कोई भी डिटेल दोबारा नहीं भरनी पड़ेगी!", reply_markup=markup)
        bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ CV जनरेशन में त्रुटि: {e}", chat_id, msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cv_"))
def process_cv_actions(call):
    chat_id = call.message.chat.id
    session = user_sessions.setdefault(chat_id, {})
    rdata = session.get('rdata', {})

    if call.data == "cv_no_photo":
        rdata.pop('photo', None)
        bot.answer_callback_query(call.id, "बिना फोटो के PDF तैयार हो रहा है...")
        deliver_cv_pdf(chat_id, rdata)

    elif call.data in ["cv_change_photo", "cv_reuse"]:
        session['mode'] = 'resume'
        session['step'] = 's_photo'
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📷 **बस अपनी नई फोटो भेज दीजिए**, आपकी सारी पुरानी जानकारी सुरक्षित है! तुरंत नया CV बन जाएगा:")

    elif call.data == "cv_new_start":
        session['mode'] = 'resume'
        session['step'] = 's_name'
        session['rdata'] = {}
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "💼 **नया CV शुरू!**\n\n👉 अपना **पूरा नाम (Full Name)** लिखकर भेजें:")

@bot.message_handler(content_types=['photo', 'document'])
def handle_photos_and_docs(message):
    chat_id = message.chat.id
    session = user_sessions.setdefault(chat_id, {})
    mode = session.get('mode')
    step = session.get('step')

    file_id = message.photo[-1].file_id if message.content_type == 'photo' else message.document.file_id
    file_info = bot.get_file(file_id)
    downloaded = bot.download_file(file_info.file_path)

    if mode == 'name_date' and step == 'wait_photo':
        session['nd_photo'] = downloaded
        session['step'] = 'wait_name'
        bot.send_message(chat_id, "✍️ अपना **पूरा नाम** लिखें जो फोटो पर प्रिंट करना है:")

    elif mode == 'resume' and (step == 's_photo' or 'rdata' in session):
        # अंतिम स्टेप: फोटो मिलते ही तुरंत PDF बनाएँ (डेटा डिलीट नहीं होगा)
        rdata = session.setdefault('rdata', {})
        rdata['photo'] = downloaded
        deliver_cv_pdf(chat_id, rdata)

    else:
        # डिफ़ॉल्ट: फोटो रिसाइज़र मोड
        session['temp_photo'] = downloaded
        markup = types.InlineKeyboardMarkup(row_width=2)
        b1 = types.InlineKeyboardButton("📷 पासपोर्ट फोटो (20-50 KB)", callback_data="res_photo")
        b2 = types.InlineKeyboardButton("✍️ सिग्नेचर (10-20 KB)", callback_data="res_sign")
        b3 = types.InlineKeyboardButton("📄 डॉक्यूमेंट (50-100 KB)", callback_data="res_doc")
        b4 = types.InlineKeyboardButton("📁 हैवी डॉक्यूमेंट (100-200 KB)", callback_data="res_heavy")
        markup.add(b1, b2, b3, b4)
        bot.reply_to(message, "⚙️ **किस सरकारी मानक साइज़ में कन्वर्ट करना है?**", reply_markup=markup, parse_mode="Markdown")
# ==========================================
# 11. मुख्य रनर
# ==========================================
if __name__ == '__main__':
    threading.Thread(target=job_alert_scheduler, daemon=True).start()

    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    print(f"🚀 Master Bot Engine active at {WEBHOOK_URL}")

    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)
