#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ингосстрах: Telegram-бот для менеджера
v1.4 - анкета с вводом ФИО и телефона, user_id для идентификации
"""

import logging
import time
from datetime import datetime
from urllib.parse import quote

from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

# Конфигурация
TOKEN      = "73735893230:AAEK4Jwdbkffhzsdfj23123jlkfd"
WHATSAPP   = "+79876543210"
MANAGER_ID = 698343234

# --- Настройте прокси, если надо ---
# import telebot.apihelper as apihelper
# apihelper.proxy = {'https':'socks5://user:pass@ip:port'}

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

bot = TeleBot(TOKEN)

sessions = {}
profiles = {}

SERVICES = {
    # ... можно оставить прежний полный список из вашего варианта ...
    "auto": {
        "title": "Автострахование 🚗",
        "fields": [
            {"key": "brand", "text": "Марка автомобиля", "opts": ['LADA', 'Hyundai', 'Toyota', 'Kia', 'Volkswagen', 'Renault', 'Skoda', 'BMW', 'Mercedes', 'Audi', 'Ford', 'Nissan', 'Другая']},
            {"key": "model", "text": "Модель", "dynamic": True},
            {"key": "year", "text": "Год выпуска", "opts": ["2025", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "Другой"]},
            {"key": "body", "text": "Тип кузова", "opts": ["Седан", "Хэтбек", "Универсал", "Кроссовер", "Другое"]},
            {"key": "engine", "text": "Тип двигателя", "opts": ["Бензин", "Дизель", "Электро", "Гибрид"]},
            # ...
        ],
    },
    # Остальные сервисы как раньше
}

CAR_MODELS = {
    'LADA': ['Vesta', 'Granta', 'Niva', 'Другая'],
    'Hyundai': ['Solaris', 'Creta', 'Tucson', 'Другая'],
    # ...
    'Другая': ['Другая']
}

def ensure_session(cid):
    if cid not in sessions:
        sessions[cid] = {
            "step": "profile",
            "cat": None,
            "idx": 0,
            "answers": {},
            "last": None,
            "temp_brand": None,
            "pending_input": None  # для ввода текста (ФИО, телефон)
        }

def safe_send(cid, *a, **kw):
    for _ in range(3):
        try:
            return bot.send_message(cid, *a, **kw)
        except ApiTelegramException as e:
            logger.warning(f"send_message error: {e}")
            time.sleep(1)
    return None

def delete_last(cid):
    s = sessions.get(cid)
    if s and s.get("last"):
        try:
            bot.delete_message(cid, s['last'])
        except Exception:
            pass
        s['last'] = None

def ask_profile(cid):
    ensure_session(cid)
    delete_last(cid)
    prof = profiles.get(cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if prof:
        kb.add(types.InlineKeyboardButton(f"Использовать профиль: {prof.get('fio', prof.get('name', 'Неизвестно'))}", callback_data="PF|use"))
    kb.add(types.InlineKeyboardButton("Создать новый профиль", callback_data="PF|new"))
    msg = safe_send(cid, "👤 Профиль клиента:\nВыберите действие", reply_markup=kb)
    if msg:
        sessions[cid]['last'] = msg.message_id

def ask_category(cid):
    ensure_session(cid)
    delete_last(cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    for key, val in SERVICES.items():
        kb.add(types.InlineKeyboardButton(val["title"], callback_data=f"CAT|{key}"))
    msg = safe_send(cid, "🏛️ Выберите категорию страхования:", reply_markup=kb)
    if msg:
        sessions[cid]['last'] = msg.message_id

def ask_field(cid):
    s = sessions[cid]
    cat = s['cat']
    idx = s['idx']
    fields = SERVICES[cat]['fields']
    if idx >= len(fields):
        return show_summary(cid)

    fld = fields[idx]
    kb = types.InlineKeyboardMarkup(row_width=3)

    if fld.get('dynamic') and fld['key'] == 'model':
        brand = s.get('temp_brand')
        opts = CAR_MODELS.get(brand, CAR_MODELS['Другая'])
    else:
        opts = fld['opts']

    for opt in opts:
        kb.add(types.InlineKeyboardButton(opt, callback_data=f"F|{opt}"))

    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="BACK"))

    msg = safe_send(cid, f"Шаг {idx + 1} из {len(fields)}: {fld['text']}", reply_markup=kb)
    if msg:
        s['last'] = msg.message_id

def show_summary(cid):
    s = sessions[cid]
    delete_last(cid)

    profile = profiles.get(cid, {})
    text_lines = [
        f"🕵️ ID пользователя: {cid}",
        f"👤 Клиент: {profile.get('fio', 'Не указано')}",
        f"📞 Телефон: {profile.get('phone', 'Не указано')}",
        "",
        f"🏷 Категория: {SERVICES[s['cat']]['title']}",
        "",
        "📋 Заполненные данные:"
    ]
    for k, v in s['answers'].items():
        text_lines.append(f"- {k}: {v}")

    full_text = "\n".join(text_lines)
    wa_text = quote(full_text)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📲 Отправить заявку в WhatsApp", url=f"https://wa.me/{WHATSAPP.lstrip('+')}?text={wa_text}"))

    safe_send(cid, full_text, reply_markup=kb)
    safe_send(MANAGER_ID, f"📩 Новая заявка от пользователя {cid}:\n\n{full_text}")

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    cid = message.chat.id
    ensure_session(cid)
    s = sessions[cid]

    prof = profiles.get(cid)
    if prof:
        ask_profile(cid)
    else:
        # Если нет профиля, сразу запросим ФИО
        s['pending_input'] = 'fio'
        safe_send(cid, "Пожалуйста, введите ФИО клиента.")

@bot.message_handler(func=lambda m: sessions.get(m.chat.id, {}).get('pending_input') is not None)
def handle_text_input(message):
    cid = message.chat.id
    s = sessions.get(cid)
    if not s:
        ensure_session(cid)
        s = sessions[cid]

    field = s['pending_input']
    text = message.text.strip()

    if field == 'fio':
        if len(text.split()) < 2:
            safe_send(cid, "Пожалуйста, введите полное ФИО (как минимум имя и фамилию).")
            return
        profiles[cid] = profiles.get(cid, {})
        profiles[cid]['fio'] = text
        s['pending_input'] = 'phone'
        safe_send(cid, "Введите номер телефона (например, +7XXXXXXXXXX):")
    elif field == 'phone':
        if not (text.startswith('+7') and len(text) >= 12 and text[2:].isdigit()):
            safe_send(cid, "Неверный формат номера. Введите телефон в формате +7XXXXXXXXXX:")
            return
        profiles[cid]['phone'] = text
        s['pending_input'] = None
        s['step'] = 'profile'
        safe_send(cid, f"Профиль сохранён: {profiles[cid]['fio']} / {profiles[cid]['phone']}")
        ask_profile(cid)
    else:
        safe_send(cid, "Неизвестная команда. Пожалуйста, используйте меню.")
    s['last'] = message.message_id

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    cid = call.message.chat.id
    s = sessions.get(cid)
    if s is None:
        ensure_session(cid)
        s = sessions[cid]

    data = call.data
    parts = data.split('|')
    cmd = parts[0]
    val = parts[1] if len(parts) > 1 else None

    if cmd == 'PF':
        if val == 'use':
            if cid in profiles:
                s['step'] = 'category'
                ask_category(cid)
            else:
                s['pending_input'] = 'fio'
                safe_send(cid, "Профиль не найден, введите ФИО клиента:")
        elif val == 'new':
            s['pending_input'] = 'fio'
            safe_send(cid, "Пожалуйста, введите ФИО клиента:")
        else:
            ask_profile(cid)
    elif cmd == 'CAT':
        s['cat'] = val
        s['idx'] = 0
        s['answers'] = {}
        s['temp_brand'] = None
        s['step'] = 'fields'
        ask_field(cid)
    elif cmd == 'F':
        if s['step'] != 'fields' or s['cat'] is None:
            ask_category(cid)
            return
        field = SERVICES[s['cat']]['fields'][s['idx']]
        s['answers'][field['text']] = val
        if field['key'] == 'brand':
            s['temp_brand'] = val
        s['idx'] += 1
        ask_field(cid)
    elif cmd == 'BACK':
        if s['idx'] > 0:
            s['idx'] -= 1
            # Удаляем ответ при возврате назад
            field = SERVICES[s['cat']]['fields'][s['idx']]
            s['answers'].pop(field['text'], None)
            ask_field(cid)
        else:
            s['step'] = 'category'
            ask_category(cid)
    else:
        safe_send(cid, "Непонятное действие")
    bot.answer_callback_query(call.id)

if __name__ == '__main__':
    logger.info("Бот запущен")
    bot.delete_webhook()
    retries = 0
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Ошибка в polling: {e}. Перезапуск через 15 секунд")
            time.sleep(15)
            retries += 1
            if retries > 5:
                logger.error("Много ошибок, проверьте соединение и токен")
                time.sleep(60)
                retries = 0
