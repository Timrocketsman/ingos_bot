import os, time, logging
from telebot import TeleBot, types

TOKEN = os.environ.get("TOKEN", "7373....")  # лучше через переменные окружения Railway
WHATSAPP = "+79898325577"
MANAGER_ID = 6983437462

logging.basicConfig(level=logging.INFO)
bot = TeleBot(TOKEN)

sessions = {}
profiles = {}

def ensure_session(cid):
    if cid not in sessions:
        sessions[cid] = {"step": "profile", "idx": 0, "answers": {}, "last": None}

def safe_send(cid, txt, **kw):
    try:
        return bot.send_message(cid, txt, **kw)
    except Exception as e:
        logging.error(e)

def ask_profile(cid):
    ensure_session(cid)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Новый профиль", callback_data="PF|new"))
    safe_send(cid, "👤 Профиль клиента:", reply_markup=kb)

@bot.message_handler(commands=["start", "help"])
def start_handler(m):
    ask_profile(m.chat.id)

@bot.callback_query_handler(func=lambda c: True)
def handle_cb(c):
    if c.data == "PF|new":
        profiles[c.message.chat.id] = {"name": "Иван Иванов"}
        safe_send(c.message.chat.id, f"✅ Профиль сохранён.\nWhatsApp: {WHATSAPP}")

if __name__ == "__main__":
    logging.info("🚀 Бот запущен")
    bot.delete_webhook()
    time.sleep(3)
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            logging.error(f"Ошибка polling: {e}")
            time.sleep(10)
