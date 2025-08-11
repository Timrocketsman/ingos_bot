#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import time
from datetime import datetime
from urllib.parse import quote

from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

# === УКАЖИТЕ ПОЛНЫЙ ТОКЕН ЗДЕСЬ ===
TOKEN = "7373585495:AAETFfffmmyzUOCklPeMSRht7LueleUn9h0"

WHATSAPP   = "+79898325577"
MANAGER_ID = 6983437462

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = TeleBot(TOKEN)

@bot.message_handler(commands=["start","help"])
def start_handler(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🚗 Автострахование", callback_data="auto"))
    kb.add(types.InlineKeyboardButton("👤 Страхование жизни", callback_data="life"))
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в бот СПАО «Ингосстрах»!\n\nВыберите тип страхования:",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: True)
def callback_handler(c):
    if c.data == "auto":
        text = f"🚗 Автострахование\n\n📞 WhatsApp: https://wa.me/{WHATSAPP.lstrip('+')}"
    elif c.data == "life":
        text = f"👤 Страхование жизни\n\n📞 WhatsApp: https://wa.me/{WHATSAPP.lstrip('+')}"
    else:
        text = "Неизвестный выбор"
    bot.edit_message_text(text, c.message.chat.id, c.message.message_id)
    bot.answer_callback_query(c.id)
    bot.send_message(MANAGER_ID, f"Новый запрос: {c.data} от {c.message.chat.id}")

if __name__ == "__main__":
    logger.info("🚀 Бот запущен")
    bot.delete_webhook()
    time.sleep(2)
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
