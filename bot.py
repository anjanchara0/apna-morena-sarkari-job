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
    return "✅ Student Super-Bot Engine Active 24/7!", 200

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
        time.sleep(600)  # हर 10 मिनट में ऑटो-चेक
        fetch_sarkari_result_direct()
        fetch_all_india_hindi_news()

# ==========================================
# 4. इन-मेमोरी स्टेट और मुख्य मेनू
# ==========================================
user_sessions = {}

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton("📐 फोटो / सिग्नेचर रिसाइज़र")
    b2 = types.KeyboardButton("🏷️ फोटो पर नाम व तारीख प्रिंट करें")
    b3 = types.KeyboardButton("📄 प्रोफेशनल रिज्यूम बनाएँ")
    b4 = types.KeyboardButton("🧠 सरकारी एग्जाम डेली क्विज़")
    markup.add(b1, b2, b3, b4)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 **ऑल-इन-वन स्टूडेंट सुपर-टूल में आपका स्वागत है!** 🇮🇳\n\n"
        "यहाँ आपको सरकारी फॉर्म और तैयारी की सभी सुविधाएँ एक जगह मिलती हैं:\n"
        "• 📷 सटीक KB में फोटो/साइन रिसाइज़ करें\n"
        "• 🏷️ SSC/Vyapam मानकों अनुसार फोटो पर नाम व तारीख लिखें\n"
        "• 📄 फोटो वाला आकर्षक प्रोफेशनल रिज्यूम PDF बनाएँ\n"
        "• 🧠 GK/GS और करेंट अफेयर्स क्विज़ हल करें\n\n"
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
    try:
        font_size = int(strip_height * 0.35)
        font = ImageFont.load_default()
    except:
        font = None
    
    draw.text((int(width * 0.1), height + int(strip_height * 0.15)), f"NAME: {name.upper()}", fill="black", font=font)
    draw.text((int(width * 0.1), height + int(strip_height * 0.55)), f"DATE: {date_text}", fill="black", font=font)
    
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
    },
    {
        "q": "कंप्यूटर में CPU का पूरा नाम (Full Form) क्या होता है?",
        "options": ["Central Processing Unit", "Central Program Utility", "Control Processing Unit", "Core Power Unit"],
        "correct": 0
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
# 8. फीचर 4: मॉडर्न टू-कॉलम प्रोफेशनल रिज्यूम बिल्डर
# ==========================================
def generate_resume_pdf(data):
    pdf_buffer = io.BytesIO()
    # A4 साइज, मिनिमल मार्जिन
    doc = SimpleDocTemplate(
        pdf_buffer, 
        pagesize=letter, 
        rightMargin=18, 
        leftMargin=18, 
        topMargin=18, 
        bottomMargin=18
    )
    story = []
    styles = getSampleStyleSheet()

    # प्रोफेशनल टाइपोग्राफी (100% ग्लिच-फ्री)
    name_style = ParagraphStyle('Name', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=colors.HexColor("#0F172A"))
    sub_title_style = ParagraphStyle('Sub', fontName='Helvetica', fontSize=11, leading=14, textColor=colors.HexColor("#0284C7"))
    
    sec_heading_right = ParagraphStyle('SecRight', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor("#0F172A"), spaceAfter=6)
    sec_heading_left = ParagraphStyle('SecLeft', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.white, spaceAfter=6)
    
    left_body = ParagraphStyle('LeftBody', fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor("#E2E8F0"))
    right_body = ParagraphStyle('RightBody', fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    table_cell = ParagraphStyle('TCell', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor("#1E293B"))
    table_head = ParagraphStyle('THead', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=colors.white)

    # -------------------------------------------------------------
    # बायां कॉलम (Dark Navy Sidebar: Photo + Contact + Skills)
    # -------------------------------------------------------------
    left_elements = []
    
    # पासपोर्ट फोटो
    if 'photo' in data:
        try:
            p_stream = io.BytesIO(data['photo'])
            img = RLImage(p_stream, width=95, height=115)
            left_elements.append(img)
            left_elements.append(Spacer(1, 15))
        except:
            pass

    # संपर्क सूत्र (Contact)
    left_elements.append(Paragraph("CONTACT INFO", sec_heading_left))
    left_elements.append(Paragraph(f"<b>Phone:</b><br/>{data.get('phone', 'N/A')}", left_body))
    left_elements.append(Spacer(1, 6))
    left_elements.append(Paragraph(f"<b>Email:</b><br/>{data.get('email', 'N/A')}", left_body))
    left_elements.append(Spacer(1, 6))
    left_elements.append(Paragraph("<b>Location:</b><br/>India", left_body))
    left_elements.append(Spacer(1, 15))

    # तकनीकी एवं अन्य कौशल (Skills)
    left_elements.append(Paragraph("KEY SKILLS", sec_heading_left))
    raw_skills = data.get('skills', 'Basic Computer, MS Office, Typing')
    for s in [x.strip() for x in raw_skills.replace(',', '\n').split('\n') if x.strip()]:
        left_elements.append(Paragraph(f"• {s}", left_body))
    left_elements.append(Spacer(1, 15))

    # व्यक्तिगत विवरण (Personal Details)
    left_elements.append(Paragraph("PERSONAL DETAILS", sec_heading_left))
    left_elements.append(Paragraph(f"<b>Father:</b> {data.get('father', 'N/A')}", left_body))
    left_elements.append(Spacer(1, 4))
    left_elements.append(Paragraph("<b>Languages:</b><br/>Hindi, English", left_body))
    left_elements.append(Spacer(1, 4))
    left_elements.append(Paragraph("<b>Nationality:</b> Indian", left_body))

    # -------------------------------------------------------------
    # दायां कॉलम (Main Content: Name + Summary + Education)
    # -------------------------------------------------------------
    right_elements = []
    
    # हेडर
    cand_name = data.get('name', 'CANDIDATE NAME').upper()
    right_elements.append(Paragraph(cand_name, name_style))
    right_elements.append(Paragraph("Job Applicant & Professional Resume", sub_title_style))
    right_elements.append(Spacer(1, 12))

    # कैरियर ऑब्जेक्टिव / समरी
    right_elements.append(Paragraph("PROFESSIONAL SUMMARY", sec_heading_right))
    summary_text = (
        "Enthusiastic and detail-oriented individual aiming to contribute effectively to organizational "
        "goals while leveraging technical and analytical skills in a dynamic work environment."
    )
    right_elements.append(Paragraph(summary_text, right_body))
    right_elements.append(Spacer(1, 15))

    # शैक्षणिक योग्यता टेबल
    right_elements.append(Paragraph("ACADEMIC QUALIFICATIONS", sec_heading_right))
    edu_table_data = [
        [Paragraph("Course / Degree", table_head), Paragraph("Board / University", table_head), Paragraph("Score / Status", table_head)],
        [Paragraph("<b>10th Standard</b>", table_cell), Paragraph(data.get('edu_10th_board', 'State Board'), table_cell), Paragraph(data.get('edu_10th_marks', 'Passed'), table_cell)],
        [Paragraph("<b>12th Standard</b>", table_cell), Paragraph(data.get('edu_12th_board', 'State Board'), table_cell), Paragraph(data.get('edu_12th_marks', 'Passed'), table_cell)],
        [Paragraph("<b>Graduation / Diploma</b>", table_cell), Paragraph(data.get('edu_grad_board', 'University'), table_cell), Paragraph(data.get('edu_grad_marks', 'Passed'), table_cell)]
    ]
    
    edu_table = Table(edu_table_data, colWidths=[120, 160, 90])
    edu_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    right_elements.append(edu_table)
    right_elements.append(Spacer(1, 15))

    # डिक्लेरेशन (Self Declaration)
    right_elements.append(Paragraph("DECLARATION", sec_heading_right))
    dec_text = "I hereby confirm that the information provided above is true and authentic to the best of my knowledge."
    right_elements.append(Paragraph(dec_text, right_body))

    # -------------------------------------------------------------
    # 2-कॉलम मास्टर फ्रेम (35% Dark Navy Sidebar | 65% Main Content)
    # -------------------------------------------------------------
    master_table = Table([[left_elements, right_elements]], colWidths=[185, 390])
    master_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#0F172A")),  # प्रीमियम डार्क स्लेट साइडबार
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 14),
        ('RIGHTPADDING', (0, 0), (0, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (1, 0), (1, -1), 18),
        ('RIGHTPADDING', (1, 0), (1, -1), 10),
    ]))
    
    story.append(master_table)
    doc.build(story)
    return pdf_buffer.getvalue()
# ==========================================
# 9. टेक्स्ट व मैसेज हैंडलर
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

    elif txt == "📄 प्रोफेशनल रिज्यूम बनाएँ":
        session['mode'] = 'resume'
        session['step'] = 'res_name'
        session['resume_data'] = {}
        bot.send_message(chat_id, "💼 **रिज्यूम मेकर शुरू!**\n\nअपना **पूरा नाम (Full Name)** लिखकर भेजें:")
        return

    # बातचीत आधारित इनपुट्स (Step-by-Step Inputs)
    mode = session.get('mode')
    step = session.get('step')

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
                session.clear()
            else:
                bot.send_message(chat_id, "फोटो नहीं मिली, कृपया प्रक्रिया पुनः शुरू करें।")

    elif mode == 'resume':
        rdata = session.get('resume_data', {})
        if step == 'res_name':
            rdata['name'] = txt
            session['step'] = 'res_phone'
            bot.send_message(chat_id, "📱 अपना **मोबाइल नंबर** भेजें:")
        elif step == 'res_phone':
            rdata['phone'] = txt
            session['step'] = 'res_email'
            bot.send_message(chat_id, "✉️ अपनी **ईमेल आईडी (Email)** भेजें:")
        elif step == 'res_email':
            rdata['email'] = txt
            session['step'] = 'res_father'
            bot.send_message(chat_id, "👨‍👦 **पिता का नाम** भेजें:")
        elif step == 'res_father':
            rdata['father'] = txt
            session['step'] = 'res_10th'
            bot.send_message(chat_id, "📚 **10वीं का विवरण** भेजें (बोर्ड और प्रतिशत, उदा: `MP Board, 78%`):")
        elif step == 'res_10th':
            rdata['edu_10th_board'] = txt
            rdata['edu_10th_marks'] = "Passed"
            session['step'] = 'res_12th'
            bot.send_message(chat_id, "🎓 **12वीं का विवरण** भेजें (बोर्ड और प्रतिशत, उदा: `CBSE, 75%`):")
        elif step == 'res_12th':
            rdata['edu_12th_board'] = txt
            rdata['edu_12th_marks'] = "Passed"
            session['step'] = 'res_grad'
            bot.send_message(chat_id, "🏛️ **ग्रेजुएशन / डिप्लोमा** (या टाइप करें `N/A` अगर नहीं है):")
        elif step == 'res_grad':
            rdata['edu_grad_board'] = txt
            rdata['edu_grad_marks'] = "Passed"
            session['step'] = 'res_skills'
            bot.send_message(chat_id, "⚡ अपनी **स्किल्स** भेजें (उदा: `MS Office, Hindi Typing 35 WPM, GST/Tally, Internet`):")
        elif step == 'res_skills':
            rdata['skills'] = txt
            session['step'] = 'res_photo'
            bot.send_message(chat_id, "📷 अंतिम चरण: रिज्यूम पर लगाने के लिए अपनी **पासपोर्ट फोटो** भेजें:")

# ==========================================
# 10. फोटो व डॉक्यूमेंट हैंडलर
# ==========================================
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

    elif mode == 'resume' and step == 'res_photo':
        rdata = session.get('resume_data', {})
        rdata['photo'] = downloaded
        msg = bot.send_message(chat_id, "⏳ **प्रोफेशनल PDF रिज्यूम तैयार किया जा रहा है...**")
        
        try:
            pdf_bytes = generate_resume_pdf(rdata)
            out_pdf = io.BytesIO(pdf_bytes)
            out_pdf.name = f"{rdata.get('name', 'Student')}_Resume.pdf"
            bot.send_document(chat_id, out_pdf, caption="🎉 **आपका प्रोफेशनल रिज्यूम PDF तैयार है!**")
            bot.delete_message(chat_id, msg.message_id)
            session.clear()
        except Exception as e:
            bot.edit_message_text(f"❌ रिज्यूम जनरेशन में त्रुटि: {e}", chat_id, msg.message_id)

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
    print(f"🚀 All-in-One Super Bot Active at {WEBHOOK_URL}")

    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)
