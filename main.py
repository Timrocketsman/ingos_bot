#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ингосстрах: Telegram-бот для менеджера
v1.1: Устойчивый polling, анкета, WhatsApp, копия менеджеру
"""

import logging
import time
from datetime import datetime
from urllib.parse import quote
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

# ====================== КОНФИГ ======================
TOKEN      = "7373585495:AAETFfffmmyzUOCklPeMSRht7LueleUn9h0"
WHATSAPP   = "+79898325577"
MANAGER_ID = 6983437462

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

bot = TeleBot(TOKEN)

# ====================== ДАННЫЕ ======================
sessions = {}   # chat_id -> dict
profiles = {}   # chat_id -> dict

SERVICES = {
    "auto": {
        "title": "Автострахование (КАСКО/ОСАГО) 🚗",
        "fields": [
            {"key":"brand","text":"Марка автомобиля","opts":['LADA','Hyundai','Toyota','Kia','Volkswagen','Renault','BMW','Mercedes','Audi','Ford','Nissan','Другая']},
            {"key":"model","text":"Модель","opts":["Модель A","Модель B","Другая"]},
            {"key":"year","text":"Год выпуска","opts":["2025","2024","2023","2022","2021","Другое"]},
            {"key":"power","text":"Мощность (л.с.)","opts":["<100","100–150","151–200","201–300",">300"]}
        ]
    },
    "life": {
        "title": "Страхование жизни 👤",
        "fields": [
            {"key":"sum","text":"Сумма","opts":["500k","1M","2M"]},
            {"key":"age","text":"Возраст","opts":["18–30","31–50","51+"]}
        ]
    }
}

# ====================== УТИЛИТЫ ======================
def ensure_session(cid):
    if cid not in sessions:
        sessions[cid] = {"step":"profile","cat":None,"idx":0,"answers":{},"last":None}

def safe_send(cid, *a, **kw):
    for _ in range(3):
        try:
            return bot.send_message(cid, *a, **kw)
        except ApiTelegramException as e:
            logger.warning(e)
            time.sleep(1)
    return None

def delete_last(cid):
    s = sessions.get(cid)
    if s and s.get("last"):
        try:
            bot.delete_message(cid, s["last"])
        except:
            pass
        s["last"] = None

# ====================== ШАГИ ======================
def ask_profile(cid):
    ensure_session(cid)
    delete_last(cid)
    prof = profiles.get(cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if prof:
        kb.add(types.InlineKeyboardButton(f"Использовать: {prof['name']}", callback_data="PF|use"))
    kb.add(types.InlineKeyboardButton("Новый профиль", callback_data="PF|new"))
    msg = safe_send(cid, "👤 Профиль клиента:", reply_markup=kb)
    if msg: sessions[cid]["last"] = msg.message_id

def ask_category(cid):
    delete_last(cid)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Авто 🚗", callback_data="CAT|auto"))
    kb.add(types.InlineKeyboardButton("Жизнь 👤", callback_data="CAT|life"))
    msg = safe_send(cid, "🏛️ Выберите категорию:", reply_markup=kb)
    if msg: sessions[cid]["last"] = msg.message_id

def ask_field(cid):
    s = sessions[cid]
    cat = s["cat"]
    idx = s["idx"]
    fields = SERVICES[cat]["fields"]
    if idx >= len(fields):
        return show_summary(cid)

    fld = fields[idx]
    kb = types.InlineKeyboardMarkup(row_width=2)
    for opt in fld["opts"]:
        kb.add(types.InlineKeyboardButton(opt, callback_data=f"F|{opt}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="BACK"))
    msg = safe_send(cid, f"Шаг {idx+1}/{len(fields)} — {fld['text']}:", reply_markup=kb)
    if msg: s["last"] = msg.message_id

def show_summary(cid):
    delete_last(cid)
    s = sessions[cid]
    lines = [
        f"📝 Заявка от {datetime.now():%Y-%m-%d %H:%M}",
        f"Категория: {SERVICES[s['cat']]['title']}"
    ]
    for k,v in s["answers"].items():
        lines.append(f"- {k}: {v}")
    text = "\n".join(lines)

    wa_text = quote(text)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📩 WhatsApp менеджеру", url=f"https://wa.me/{WHATSAPP.lstrip('+')}?text={wa_text}"))
    safe_send(cid, text, reply_markup=kb)
    safe_send(MANAGER_ID, f"Новая заявка:\n{text}")

# ====================== ХЕНДЛЕРЫ ======================
@bot.message_handler(commands=["start","help"])
def handle_start(m):
    ensure_session(m.chat.id)
    ask_profile(m.chat.id)

@bot.callback_query_handler(func=lambda c: True)
def handle_cb(c):
    cid = c.message.chat.id
    ensure_session(cid)
    s = sessions[cid]
    cmd, val = c.data.split("|",1) if "|" in c.data else (c.data,None)

    if cmd=="PF":
        if val=="use":
            ask_category(cid)
        else:
            profiles[cid] = {"name":"Иван Иванов","phone":"+7XXXXXXXXXX"}
            ask_category(cid)

    elif cmd=="CAT":
        s["cat"] = val
        s["idx"] = 0
        s["answers"] = {}
        ask_field(cid)

    elif cmd=="F":
        fld = SERVICES[s["cat"]]["fields"][s["idx"]]
        s["answers"][fld["text"]] = val
        s["idx"] += 1
        ask_field(cid)

    elif cmd=="BACK":
        if s["idx"]>0:
            s["idx"] -= 1
            ask_field(cid)
        else:
            ask_category(cid)

    bot.answer_callback_query(c.id)

# ====================== ЗАПУСК ======================
if __name__=="__main__":
    logger.info("Бот запущен")
    bot.delete_webhook()
    retries = 0
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Ошибка polling: {e}. Перезапуск через 15с")
            time.sleep(15)
            retries += 1
            if retries > 5:
                retries = 0
                time.sleep(60)
