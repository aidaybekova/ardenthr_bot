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
        # Nomzod javobini qabul qildik -> yakuniy ma'lumotlarni yuboramiz
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
