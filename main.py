#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ингосстрах: Telegram-бот для менеджера
v1.4: Добавлен ввод реальных данных профиля (ФИО, телефон) с валидацией
"""

import logging
import time
import re  # Для валидации телефона
from datetime import datetime
from urllib.parse import quote

from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

# ====================== Конфигурация ======================
TOKEN      = "7373585495:AAEK4JwHdbHzfQwfr2zNNknZDwpObCnPXZ0"
WHATSAPP   = "+79898325577"       # WhatsApp менеджера
MANAGER_ID = 6983437462           # Telegram ID менеджера для копий

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

bot = TeleBot(TOKEN)

# ====================== Хранилище ======================
sessions = {}   # chat_id -> session dict
profiles = {}   # chat_id -> profile dict

# ====================== Каталог услуг ======================
SERVICES = {
    "auto": {
        "title": "Автострахование 🚗",
        "fields": [
            {"key":"brand","text":"Марка автомобиля","opts":['LADA', 'Hyundai', 'Toyota', 'Kia', 'Volkswagen', 'Renault', 'Skoda', 'BMW', 'Mercedes', 'Audi', 'Ford', 'Nissan', 'Другая']},
            {"key":"model","text":"Модель","dynamic": True},
            {"key":"year","text":"Год выпуска","opts":["2025","2024","2023","2022","2021","2020","2019","2018","2017","2016","2015","2014","2013","2012","2011","2010","Другой"]},
            {"key":"body","text":"Тип кузова","opts":["Седан","Хэтчбек","Универсал","Кроссовер","Внедорожник","Другое"]},
            {"key":"engine","text":"Тип двигателя","opts":["Бензин","Дизель","Электро","Гибрид"]},
            {"key":"power","text":"Мощность (л.с.)","opts":["<100","100–150","151–200","201–300",">300"]},
            {"key":"experience","text":"Стаж водителя (лет)","opts":["0–3","4–10","11–20",">20"]},
            {"key":"city","text":"Город регистрации","opts":["Москва","СПб","Екатеринбург","Новосибирск","Другой"]}
        ]
    },
    "life": {
        "title": "Страхование жизни 👤",
        "fields": [
            {"key":"sum","text":"Сумма страхования","opts":["500k","1M","2M","5M","10M"]},
            {"key":"age","text":"Возраст","opts":["18–30","31–50","51+"]},
            {"key":"period","text":"Срок","opts":["5 лет","10 лет","15 лет","до 65 лет"]}
        ]
    },
    "health": {
        "title": "Медицинское страхование (ДМС) 🏥",
        "fields": [
            {"key":"program","text":"Программа","opts":["Базовая","Расширенная","VIP"]},
            {"key":"age","text":"Возраст","opts":["18–30","31–50","51+"]},
            {"key":"region","text":"Регион обслуживания","opts":["Москва","СПб","Другой"]},
            {"key":"dentistry","text":"Стоматология","opts":["Не нужна","Базовая","Расширенная","VIP"]}
        ]
    },
    "property": {
        "title": "Страхование имущества 🏠",
        "fields": [
            {"key":"type","text":"Тип имущества","opts":["Квартира","Дом","Дача","Коммерческая"]},
            {"key":"value","text":"Страховая стоимость","opts":["<1M","1M–5M","5M–10M",">10M"]},
            {"key":"address","text":"Локация","opts":["Город","Загород","Другое"]},
            {"key":"risks","text":"Риски","opts":["Базовые","+Затопление","+Кража","Полное покрытие"]}
        ]
    },
    "travel": {
        "title": "Страхование путешествий ✈️",
        "fields": [
            {"key":"destination","text":"Направление","opts":["Европа","Азия","Россия","Америка","Другое"]},
            {"key":"duration","text":"Срок поездки","opts":["<7 дней","7–14 дней","15–30 дней",">30 дней"]},
            {"key":"purpose","text":"Цель","opts":["Отдых","Бизнес","Спорт","Учёба"]},
            {"key":"coverage","text":"Покрытие","opts":["35k EUR","50k EUR","100k EUR","Без ограничений"]}
        ]
    }
}

CAR_MODELS = {
    'LADA': ['Vesta', 'Granta', 'Niva', 'Другая'],
    'Hyundai': ['Solaris', 'Creta', 'Tucson', 'Другая'],
    'Toyota': ['Camry', 'Corolla', 'RAV4', 'Другая'],
    'Kia': ['Rio', 'Sportage', 'Ceed', 'Другая'],
    'Volkswagen': ['Polo', 'Tiguan', 'Golf', 'Другая'],
    'Renault': ['Logan', 'Duster', 'Arkana', 'Другая'],
    'Skoda': ['Rapid', 'Octavia', 'Kodiaq', 'Другая'],
    'BMW': ['3 Series', '5 Series', 'X5', 'Другая'],
    'Mercedes': ['C-Class', 'E-Class', 'GLC', 'Другая'],
    'Audi': ['A4', 'A6', 'Q5', 'Другая'],
    'Ford': ['Focus', 'Fiesta', 'Kuga', 'Другая'],
    'Nissan': ['Qashqai', 'X-Trail', 'Juke', 'Другая'],
    'Другая': ['Другая']
}

# ====================== Вспомогательные функции ======================
def ensure_session(cid):
    if cid not in sessions:
        sessions[cid] = {"step": "profile", "cat": None, "idx": 0, "answers": {}, "last": None, "temp_brand": None, "input_state": None}

def safe_send(cid, *a, **kw):
    for _ in range(3):
        try:
            return bot.send_message(cid, *a, **kw)
        except ApiTelegramException as e:
            logger.warning(f"send_message API error: {e}")
            time.sleep(1)
        except Exception as e:
            logger.error(f"send_message unexpected: {e}")
            time.sleep(1)
    return None

def delete_last(cid):
    s = sessions.get(cid)
    if s and s.get("last"):
        try:
            bot.delete_message(cid, s["last"])
        except Exception:
            pass
        s["last"] = None

# ====================== Основные шаги ======================
def ask_profile(cid):
    ensure_session(cid)
    delete_last(cid)
    s = sessions[cid]
    s["input_state"] = None  # Сброс состояния ввода
    prof = profiles.get(cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    if prof:
        kb.add(types.InlineKeyboardButton(f"Использовать: {prof['name']}", callback_data="PF|use"))
    kb.add(types.InlineKeyboardButton("Новый профиль", callback_data="PF|new"))
    msg = safe_send(cid, "👤 Профиль клиента:", reply_markup=kb)
    if msg:
        s["last"] = msg.message_id

def ask_category(cid):
    ensure_session(cid)
    delete_last(cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    for key, data in SERVICES.items():
        kb.add(types.InlineKeyboardButton(data["title"], callback_data=f"CAT|{key}"))
    msg = safe_send(cid, "🏛️ Выберите категорию страхования:", reply_markup=kb)
    if msg:
        sessions[cid]["last"] = msg.message_id

def ask_name(cid):
    delete_last(cid)
    msg = safe_send(cid, "Введите ФИО клиента:")
    if msg:
        sessions[cid]["last"] = msg.message_id
        sessions[cid]["input_state"] = "waiting_for_name"

def ask_phone(cid):
    delete_last(cid)
    msg = safe_send(cid, "Введите номер телефона клиента (формат: +7XXXXXXXXXX):")
    if msg:
        sessions[cid]["last"] = msg.message_id
        sessions[cid]["input_state"] = "waiting_for_phone"

def ask_field(cid):
    s = sessions[cid]
    cat, idx = s["cat"], s["idx"]
    fields = SERVICES[cat]["fields"]

    if idx >= len(fields):
        return show_summary(cid)

    field = fields[idx]
    kb = types.InlineKeyboardMarkup(row_width=3)

    if field.get("dynamic") and field["key"] == "model":
        brand = s.get("temp_brand")
        opts = CAR_MODELS.get(brand, CAR_MODELS['Другая'])
    else:
        opts = field["opts"]

    for opt in opts:
        kb.add(types.InlineKeyboardButton(opt, callback_data=f"F|{opt}"))

    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="BACK"))
    msg = safe_send(cid, f"Шаг {idx+1}/{len(fields)} — {field['text']}:", reply_markup=kb)
    if msg:
        s["last"] = msg.message_id

def show_summary(cid):
    delete_last(cid)
    s = sessions[cid]
    prof = profiles.get(cid, {"name": "Не указан", "phone": "Не указан"})
    lines = [
        f"📝 Заявка от {datetime.now():%Y-%m-%d %H:%M}",
        f"Клиент: {prof['name']} ({prof['phone']})",
        f"Категория: {SERVICES[s['cat']]['title']}"
    ]
    for k, v in s["answers"].items():
        lines.append(f"- {k}: {v}")
    text = "\n".join(lines)

    wa_text = quote(text)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📩 Отправить в WhatsApp менеджеру", url=f"https://wa.me/{WHATSAPP.lstrip('+')}?text={wa_text}"))
    safe_send(cid, text, reply_markup=kb)
    safe_send(MANAGER_ID, f"Новая заявка:\n{text}")

# ====================== Хендлеры ======================
@bot.message_handler(commands=["start","help"])
def handle_start(m):
    ensure_session(m.chat.id)
    ask_profile(m.chat.id)

@bot.message_handler(func=lambda m: True)
def handle_text(m):
    cid = m.chat.id
    s = sessions.get(cid)
    if not s:
        return

    input_state = s.get("input_state")
    if input_state == "waiting_for_name":
        name = m.text.strip()
        if len(name) < 3:
            safe_send(cid, "ФИО должно быть не короче 3 символов. Попробуйте снова:")
            return
        profiles[cid] = {"name": name, "phone": None}
        ask_phone(cid)
    elif input_state == "waiting_for_phone":
        phone = m.text.strip()
        if not re.match(r'^\+7\d{10}$', phone):
            safe_send(cid, "Номер должен быть в формате +7XXXXXXXXXX. Попробуйте снова:")
            return
        profiles[cid]["phone"] = phone
        s["input_state"] = None
        s["step"] = "category"
        ask_category(cid)

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(c):
    cid = c.message.chat.id
    ensure_session(cid)
    s = sessions[cid]

    cmd_val = c.data.split("|", 1)
    cmd = cmd_val[0]
    val = cmd_val[1] if len(cmd_val) > 1 else None

    if cmd == "PF":
        if val == "use" and profiles.get(cid):
            s["step"] = "category"
            ask_category(cid)
        elif val == "new":
            s["step"] = "profile_new"
            ask_name(cid)
        else:
            ask_profile(cid)

    elif cmd == "CAT":
        s["cat"] = val
        s["idx"] = 0
        s["answers"] = {}
        s["temp_brand"] = None
        s["step"] = "fields"
        ask_field(cid)

    elif cmd == "F":
        field = SERVICES[s["cat"]]["fields"][s["idx"]]
        s["answers"][field["text"]] = val
        if field["key"] == "brand":
            s["temp_brand"] = val
        s["idx"] += 1
        ask_field(cid)

    elif cmd == "BACK":
        if s["idx"] > 0:
            s["idx"] -= 1
            field = SERVICES[s["cat"]]["fields"][s["idx"]]
            s["answers"].pop(field["text"], None)
            ask_field(cid)
        else:
            s["step"] = "category"
            ask_category(cid)

    bot.answer_callback_query(c.id)

# ====================== Запуск ======================
if __name__== "__main__":
    logger.info("Бот запущен")
    bot.delete_webhook()
    retries = 0
    max_retries = 20
    base_delay = 5
    while retries < max_retries:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            delay = min(base_delay * (2 ** retries), 300)
            logger.error(f"Ошибка polling: {e}, повтор через {delay} сек.")
            time.sleep(delay)
            retries += 1
        else:
            retries = 0
            time.sleep(1)
    logger.critical("Превышено число попыток перезапуска, проверьте сеть и токен.")
