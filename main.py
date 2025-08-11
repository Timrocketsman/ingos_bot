#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ингосстрах: Telegram-бот для менеджера
v1.3: Устойчивый polling, автоперезапуск, расширенный перечень услуг
"""

import logging
import time
from datetime import datetime
from urllib.parse import quote

from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
import telebot.apihelper as apihelper  # Для прокси, расскомментируйте и заполните если нужно

# ====================== Конфигурация ======================
TOKEN      = "7373585495:AAETFfffmmyzUOCklPeMSRht7LueleUn9h0"
WHATSAPP   = "+79898325577"       # WhatsApp менеджера
MANAGER_ID = 6983437462           # Telegram ID менеджера для копий

# apihelper.proxy = {'https': 'socks5://user:pass@ip:port'}  # Если нужна прокси

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

bot = TeleBot(TOKEN)

# ====================== Хранилище ======================
sessions = {}   # chat_id -> session dict
profiles = {}   # chat_id -> profile dict

# ====================== Расширенный каталог услуг ======================
SERVICES = {
    "auto": {
        "title": "Автострахование 🚗",
        "fields": [
            {"key":"brand","text":"Марка автомобиля","opts":['LADA', 'Hyundai', 'Toyota', 'Kia', 'Volkswagen', 'Renault', 'Skoda', 'BMW', 'Mercedes', 'Audi', 'Ford', 'Nissan', 'Другая']},
            {"key":"model","text":"Модель","dynamic": True},  # динамические варианты из CAR_MODELS
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
            {"key":"sum","text":"Сумма","opts":["500k","1M","2M"]},
            {"key":"age","text":"Возраст","opts":["18–30","31–50","51+"]}
        ]
    },
    "health": {
        "title": "Медицинское страхование (ДМС) 🏥",
        "fields": [
            {"key":"program","text":"Программа","opts":["Базовая","Расширенная","VIP"]},
            {"key":"age","text":"Возраст","opts":["18–30","31–50","51+"]},
            {"key":"region","text":"Регион","opts":["Москва","СПб","Другой"]}
        ]
    },
    "property": {
        "title": "Страхование имущества 🏠",
        "fields": [
            {"key":"type","text":"Тип имущества","opts":["Квартира","Дом","Дача","Другое"]},
            {"key":"value","text":"Стоимость","opts":["<1M","1M–5M",">5M"]},
            {"key":"address","text":"Адрес","opts":["Городской","Загородный"]}
        ]
    },
    "travel": {
        "title": "Страхование путешествий ✈️",
        "fields": [
            {"key":"destination","text":"Направление","opts":["Европа","Азия","Россия","Другое"]},
            {"key":"duration","text":"Срок","opts":["<7 дней","7–14 дней",">14 дней"]},
            {"key":"type","text":"Тип поездки","opts":["Отдых","Бизнес","Спорт"]}
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
        sessions[cid] = {"step": "profile", "cat": None, "idx": 0, "answers": {}, "last": None, "temp_brand": None}

# ... (safe_send и delete_last остаются без изменений, как в вашем коде)

# ====================== Основные шаги ======================
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

def ask_category(cid):
    ensure_session(cid)
    delete_last(cid)
    kb = types.InlineKeyboardMarkup(row_width=2)
    for key, data in SERVICES.items():
        kb.add(types.InlineKeyboardButton(data["title"], callback_data=f"CAT|{key}"))
    msg = safe_send(cid, "🏛️ Выберите категорию страхования:", reply_markup=kb)
    if msg:
        sessions[cid]["last"] = msg.message_id

def ask_field(cid):
    s = sessions[cid]
    cat, idx = s["cat"], s["idx"]
    fields = SERVICES[cat]["fields"]

    if idx >= len(fields):
        return show_summary(cid)

    field = fields[idx]
    kb = types.InlineKeyboardMarkup(row_width=3)

    # Если поле динамическое "model" — подгружаем варианты по выбранной марке авто
    if field.get("dynamic") and field["key"] == "model":
        brand = s.get("temp_brand")
        opts = CAR_MODELS.get(brand, CAR_MODELS['Другая'])
    else:
        opts = field["opts"]

    for opt in opts:
        kb.add(types.InlineKeyboardButton(opt, callback_data=f"F|{opt}"))

    # Кнопка назад
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="BACK"))
    msg = safe_send(cid, f"Шаг {idx+1}/{len(fields)} — {field['text']}:", reply_markup=kb)
    if msg:
        s["last"] = msg.message_id

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
    kb.add(types.InlineKeyboardButton("📩 Отправить в WhatsApp менеджеру", url=f"https://wa.me/{WHATSAPP.lstrip('+')}?text={wa_text}"))
    safe_send(cid, text, reply_markup=kb)
    safe_send(MANAGER_ID, f"Новая заявка:\n{text}")

# ====================== Хендлеры ======================
@bot.message_handler(commands=["start","help"])
def handle_start(m):
    ensure_session(m.chat.id)
    ask_profile(m.chat.id)

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
            # Можно расширить до полноценного ввода профиля
            profiles[cid] = {"name": "Иван Иванов", "phone": "+7XXXXXXXXXX"}
            s["step"] = "category"
            ask_category(cid)
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

        # Сохраняем выбор
        s["answers"][field["text"]] = val

        # Если поле марка авто — сохраняем бренд для динамической подгрузки моделей
        if field["key"] == "brand":
            s["temp_brand"] = val

        s["idx"] += 1
        ask_field(cid)

    elif cmd == "BACK":
        if s["idx"] > 0:
            s["idx"] -= 1
            # При возврате назад удаляем ответ, если нужно
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
            retries +=1
        else:
            retries=0
            time.sleep(1)
    logger.critical("Превышено число попыток перезапуска, проверьте сеть и токен.")
