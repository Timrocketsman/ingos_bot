#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ингосстрах: Telegram-бот для менеджера (Termux/Android)
v1.0: Устойчивый polling, прокси, автоперезапуск, копия заявок
"""

import logging
import time
from datetime import datetime
from urllib.parse import quote

from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
import telebot.apihelper as apihelper  # Для прокси

# ====================== КОНФИГУРАЦИЯ ======================
TOKEN      = "7373585495:AAETFfffmmyzUOCklPeMSRht7LueleUn9h0"
WHATSAPP   = "+79898325577"       # WhatsApp менеджера
MANAGER_ID = 6983437462           # Telegram ID менеджера для копий

# Прокси (раскомментируйте и настройте, если нужно обходить блокировки)
# apihelper.proxy = {'https': 'socks5://user:pass@ip:port'}  # SOCKS5 пример

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

bot = TeleBot(TOKEN)

# Хранилище
sessions = {}  # chat_id -> dict
profiles = {}  # chat_id -> dict

# ====================== КАТАЛОГ УСЛУГ ======================
SERVICES = {
    "auto": {
        "title": "Автострахование (КАСКО/ОСАГО) 🚗",
        "fields": [
            {"key":"brand","text":"Марка автомобиля","opts":['LADA', 'Hyundai', 'Toyota', 'Kia', 'Volkswagen', 'Renault', 'Skoda', 'BMW', 'Mercedes', 'Audi', 'Ford', 'Nissan', 'Другая']},
            {"key":"model","text":"Модель","dynamic": True},  # Динамически по бренду
            {"key":"year","text":"Год выпуска","opts":["2025","2024","2023","2022","2021","2020","2019","2018","2017","2016","2015","2014","2013","2012","2011","2010","Другой"]},
            {"key":"body","text":"Тип кузова","opts":["Седан","Хэтчбек","Универсал","Кроссовер","Внедорожник","Другое"]},
            {"key":"engine","text":"Тип двигателя","opts":["Бензин","Дизель","Электро","Гибрид"]},
            {"key":"power","text":"Мощность (л.с.)","opts":["<100","100–150","151–200","201–300",">300"]},
            {"key":"experience","text":"Стаж водителя (лет)","opts":["0–3","4–10","11–20",">20"]},
            {"key":"city","text":"Город регистрации","opts":["Москва","СПб","Екатеринбург","Новосибирск","Другой"]}
        ]
    },
    # Добавьте другие категории из истории, если нужно (ДМС, имущество и т.д.)
}

CAR_MODELS = {
    'LADA': ['Vesta', 'Granta', 'Niva', 'Другая'],
    # ... (остальные модели из истории)
    'Другая': ['Другая']
}

# ====================== ФУНКЦИИ ======================
def safe_send(cid, *a, **kw):
    for _ in range(3):
        try:
            return bot.send_message(cid, *a, **kw)
        except ApiTelegramException:
            time.sleep(1)
    return None

def delete_last(cid):
    s = sessions.get(cid)
    if s and s.get("last"):
        try: bot.delete_message(cid, s["last"])
        except: pass
        s["last"] = None

# Шаги (из истории, оптимизированные)
def ask_profile(cid):
    ensure_session(cid)
    delete_last(cid)
    prof = profiles.get(cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if prof:
        kb.add(types.InlineKeyboardButton(f"Использовать: {prof['name']}", callback_data="PF|use"))
    kb.add(types.InlineKeyboardButton("Новый профиль", callback_data="PF|new"))
    msg = safe_send(cid, "👤 Профиль клиента:", reply_markup=kb)
    if msg:
        sessions[cid]["last"] = msg.message_id

# (Остальные функции: ask_category, ask_subservice, ask_field, show_summary — аналогично истории)

# Запуск с автоперезапуском
if __name__ == "__main__":
    logger.info("Бот запущен")
    bot.delete_webhook()
    retries = 0
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Ошибка: {e}. Перезапуск через 15с")
            time.sleep(15)
            retries += 1
            if retries > 5:
                logger.error("Много ошибок. Проверьте интернет/прокси")
                time.sleep(60)  # Длинная пауза
                retries = 0
