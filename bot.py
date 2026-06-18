# -*- coding: utf-8 -*-
"""
ardenthr_bot — birinchi murojaat uchun HR bot (N'MEDOV ishlab chiqarish sexi).
 
Ish mantiqi:
1. Nomzod botga yozadi (/start yoki har qanday xabar) -> bot ish haqida ma'lumot
   va manzilni (location + Google Maps link) yuboradi.
2. Bot bitta xabarda 3 ta savol beradi: F.I.O, qayerda yashaydi, necha yoshda.
3. Nomzod javob yozadi (bitta xabar bilan, har qanday formatda).
4. Bot bog'lanish uchun telefon raqamini va ishga kelish vaqtini yuboradi.
 
Ishga tushirish:
    export BOT_TOKEN="..."          # token shu yerda environment variable orqali beriladi
    python3 bot.py
"""
 
import logging
import os
import re
import json
import urllib.request
import urllib.error
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
 
# ----------------------------------------------------------------------
# SOZLAMALAR (kerak bo'lsa shu joydan o'zgartiring)
# ----------------------------------------------------------------------
 
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PASTE_YOUR_TOKEN_HERE")
 
COMPANY_NAME = "N'MEDOV"
VACANCY_NAME = "Qadoqlovchi / Oddiy ishchi"
LOCATION_TEXT = "N'MEDOV ishlab chiqarish sexi"
LOCATION_LAT = 41.35638
LOCATION_LON = 69.265077
MAPS_LINK = "https://www.google.com/maps/place/41%C2%B021'23.0%22N+69%C2%B015'54.3%22E/@41.35638,69.265077,16z"
 
CONTACT_NAME = "Ruxshona"
CONTACT_PHONE = "+998 94 286 07 05"
WORK_START_TEXT = "Ish ertalab soat 8:00 dan boshlanadi"
 
# Google Apps Script Web App URL — javoblar shu manzilga yuboriladi
# (Google Sheets jadvaliga yozib qo'yiladi)
GOOGLE_SHEETS_URL = os.environ.get(
    "GOOGLE_SHEETS_URL",
    "https://script.google.com/macros/s/AKfycbyP4Cz0Z1N0xfj_LNytb-EyMNX1osNAxWJuZAFs42V0CISG-hZ8Di0pRnKDk-BFVy--8Q/exec",
)
 
# ----------------------------------------------------------------------
# XABAR MATNLARI (o'zbek tilida)
# ----------------------------------------------------------------------
 
WELCOME_MESSAGE = (
    f"Assalomu alaykum! 👋\n\n"
    f"Siz *{COMPANY_NAME}* kompaniyasidagi *{VACANCY_NAME}* vakansiyasi bo'yicha "
    f"murojaat qildingiz.\n\n"
    f"🏭 Ish joyi: {LOCATION_TEXT}\n"
    f"📍 Manzil (xarita): {MAPS_LINK}\n\n"
    f"Quyida ish joyining joylashuvini ham yuboramiz."
)
 
QUESTIONS_MESSAGE = (
    "Iltimos, quyidagi ma'lumotlarni *bitta xabar* qilib yuboring:\n\n"
    "1️⃣ F.I.O (Familiya Ism Otasining ismi)\n"
    "2️⃣ Qayerda yashaysiz (manzil)\n"
    "3️⃣ Necha yoshdasiz\n\n"
    "Misol uchun:\n"
    "_Aliyev Vali Aliyevich, Toshkent sh., Chilonzor tumani, 25 yosh_"
)
 
FINAL_MESSAGE = (
    "Rahmat! Ma'lumotlaringiz qabul qilindi. ✅\n\n"
    f"📞 Bog'lanish uchun: {CONTACT_NAME} — {CONTACT_PHONE}\n"
    f"🕗 {WORK_START_TEXT}\n\n"
    "Ishga kelishingizni so'raymiz! Savollaringiz bo'lsa, yuqoridagi raqamga murojaat qiling."
)
 
# Bu yerda har bir foydalanuvchi qaysi bosqichda turganini saqlaymiz
# (oddiy yechim: xotirada, jiddiy foydalanish uchun keyinroq DB qo'shsa bo'ladi)
user_state = {}
 
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
 
 
# ----------------------------------------------------------------------
# MATNNI QISMLARGA AJRATISH (oddiy qoidalar asosida, AI siz)
# ----------------------------------------------------------------------
 
ADDRESS_MARKERS = [
    "shahar", "shaxar", "sh.", "tuman", "viloyat", "mahalla", "ko'cha",
    "kocha", "uy", "qishloq", "qishlog'i", "посёлок", "город", "район",
    "область", "ko'chasi", "mavze", "massiv", "kvartal",
]
 
 
def extract_age(text: str):
    """Matndan yoshni (raqamni) topadi. Topilmasa None qaytaradi."""
    # "25 yosh", "25 ёш", "25 лет", "25 года" kabi naqshlarni qidiramiz
    match = re.search(r"(\d{1,2})\s*(yosh|ёш|лет|года|лет\.)", text, re.IGNORECASE)
    if match:
        return match.group(1)
 
    # Aks holda, matndagi 14-80 oralig'idagi har qanday alohida raqamni olamiz
    numbers = re.findall(r"\b\d{1,2}\b", text)
    for num in numbers:
        if 14 <= int(num) <= 80:
            return num
    return None
 
 
def extract_address(text: str, age_str: str):
    """Matndan manzilga oid qismni topadi (marker so'zlar asosida)."""
    # Yoshni matndan vaqtincha olib tashlaymiz, aralashmasin
    clean_text = text
    if age_str:
        clean_text = re.sub(
            r"\b" + re.escape(age_str) + r"\s*(yosh|ёш|лет|года)?\b",
            "",
            clean_text,
            flags=re.IGNORECASE,
        )
 
    if "," in clean_text:
        parts = re.split(r"[,;\n]", clean_text)
        address_parts = []
        for part in parts:
            part_lower = part.lower()
            if any(marker in part_lower for marker in ADDRESS_MARKERS):
                address_parts.append(part.strip())
        if address_parts:
            return ", ".join(address_parts)
        return ""
 
    # Vergulsiz holat: birinchi marker so'zdan boshlab oxirigacha olamiz
    words = clean_text.split()
    for i, word in enumerate(words):
        word_clean = word.strip(".,;").lower()
        if any(word_clean.startswith(marker) for marker in ADDRESS_MARKERS):
            # markerdan oldingi bir so'zni ham olamiz (masalan "Namangan shahar")
            start = max(0, i - 1)
            return " ".join(words[start:]).strip(" .,;")
 
    return ""
 
 
def extract_full_name(text: str, address_str: str, age_str: str):
    """Qolgan matnni (manzil va yoshdan tashqari) F.I.O sifatida oladi."""
    # Avval vergul bilan ajratilgan holatni tekshiramiz (eng aniq holat)
    if "," in text:
        first_part = text.split(",")[0].strip()
        if first_part:
            return first_part
 
    # Vergulsiz holat: matn boshidagi katta harf bilan boshlangan so'zlarni
    # (odatda 2-3 ta) ism-familiya deb olamiz, manzil-marker so'zigacha
    words = text.split()
    name_words = []
    for word in words:
        word_clean = word.strip(".,;")
        if not word_clean:
            continue
        if any(word_clean.lower().startswith(marker) for marker in ADDRESS_MARKERS):
            break
        if re.match(r"^\d", word_clean):
            break
        if word_clean[0].isupper():
            name_words.append(word_clean)
        else:
            break
 
    if name_words:
        return " ".join(name_words)
 
    return "(aniqlanmadi)"
 
 
def parse_candidate_answer(text: str):
    """
    Nomzodning bitta xabarini F.I.O / manzil / yosh ga ajratadi.
    Hech narsa yo'qolmasligi uchun, asl matn alohida saqlanadi (raw_text).
    """
    age = extract_age(text) or ""
    address = extract_address(text, age)
    full_name = extract_full_name(text, address, age)
 
    return {
        "full_name": full_name,
        "address": address if address else "(aniqlanmadi)",
        "age": age if age else "(aniqlanmadi)",
        "raw_text": text,
    }
 
 
def send_to_google_sheets(parsed_data: dict):
    """Ma'lumotlarni Google Apps Script orqali Google Sheets jadvaliga yuboradi."""
    if not GOOGLE_SHEETS_URL or "PASTE" in GOOGLE_SHEETS_URL:
        logger.warning("GOOGLE_SHEETS_URL sozlanmagan, jadvalga yozilmadi.")
        return False
 
    try:
        payload = json.dumps(parsed_data).encode("utf-8")
        req = urllib.request.Request(
            GOOGLE_SHEETS_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
        logger.info("Google Sheets-ga muvaffaqiyatli yozildi.")
        return True
    except urllib.error.URLError as e:
        logger.error(f"Google Sheets-ga yozishda xatolik: {e}")
        return False
 
 
async def send_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ish haqida ma'lumot + lokatsiya + savollarni yuboradi."""
    chat_id = update.effective_chat.id
 
    await context.bot.send_message(
        chat_id=chat_id, text=WELCOME_MESSAGE, parse_mode="Markdown"
    )
 
    await context.bot.send_location(
        chat_id=chat_id, latitude=LOCATION_LAT, longitude=LOCATION_LON
    )
 
    await context.bot.send_message(
        chat_id=chat_id, text=QUESTIONS_MESSAGE, parse_mode="Markdown"
    )
 
    user_state[chat_id] = "waiting_for_answer"
 
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komandasi uchun."""
    await send_intro(update, context)
 
 
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchidan kelgan har qanday matnli xabarni qayta ishlaydi."""
    chat_id = update.effective_chat.id
    state = user_state.get(chat_id)
 
    if state == "waiting_for_answer":
        # Nomzod javobini qabul qildik -> matnni qismlarga ajratamiz
        user_text = update.message.text
        parsed = parse_candidate_answer(user_text)
 
        # Google Sheets jadvaliga yozamiz (xatolik bo'lsa ham botning javobiga
        # ta'sir qilmaydi — nomzod baribir yakuniy ma'lumotlarni oladi)
        send_to_google_sheets(parsed)
 
        user_state[chat_id] = "done"
        await context.bot.send_message(
            chat_id=chat_id, text=FINAL_MESSAGE, parse_mode="Markdown"
        )
    else:
        # Birinchi marta yozgan bo'lsa (yoki /start dan tashqari yozgan bo'lsa)
        await send_intro(update, context)
 
 
def main():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN topilmadi. Uni environment variable orqali bering: "
            "export BOT_TOKEN='...'"
        )
 
    app = ApplicationBuilder().token(BOT_TOKEN).build()
 
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
 
    logger.info("Bot ishga tushdi...")
    app.run_polling()
 
 
if __name__ == "__main__":
    main()
 
