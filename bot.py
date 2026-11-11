import telebot
from telebot import types
import schedule
import time
import threading
from datetime import datetime
import os
from flask import Flask, request

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Файл для хранения ID
ID_FILE = 'my_id.txt'

# --- ВРЕМЯ УРОКОВ (2 смена) ---
TIME_SLOTS = {
    1: ("11:00", "11:35"),
    2: ("11:45", "12:20"),
    3: ("12:30", "13:05"),
    4: ("13:15", "13:50"),
    5: ("13:55", "14:30"),
    6: ("14:35", "15:10"),
    7: ("15:15", "15:50"),
    8: ("15:55", "16:30")
}

# --- РАСПИСАНИЕ 9-А ---
SCHEDULE = {
    "Понеділок": [
        "Всесвітня історія", "Укр.мова 2 гр/Англ.мова 1 гр", "Фізика", 
        "Алгебра", "Укр.мова 1гр/Англ.мова 2 гр", "Укр.мова 1гр/Англ.мова 2 гр", "Геометрія"
    ],
    "Вівторок": [
        "Фіз-культ.", "Технології", "Англійська мова", 
        "Укр.мова 1гр/Англ.мова 2 гр", "Хімія", "Хімія"
    ],
    "Середа": [
        "Географія", "Фіз-культ.", "Інформатика 2 гр/Англ.мова 1 гр", 
        "Інформатика 2 гр/Англ.мова 1 гр", "Фінансова грамотність", "Історія України", "Громадянська освіта"
    ],
    "Четвер": [
        "Українська література", "Фіз-культ.", "Правознавство", 
        "Фізика", "Фізика", "Інформатика 1 гр/ Укр.мова 2 гр", "Інформатика 1 гр/ Укр.мова 2 гр"
    ],
    "П'ятниця": [
        "Зарубіжна література", "Мистецтво", "Українська література", 
        "Біологія", "Біологія", "Алгебра", "Геометрія"
    ],
    "Субота": [],
    "Неділя": []
}

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ID ---
def save_chat_id(chat_id):
    with open(ID_FILE, 'w') as f:
        f.write(str(chat_id))

def get_chat_id():
    # Сначала проверяем переменную окружения (чтобы бот не забывал ID после перезагрузки сервера)
    env_id = os.getenv('USER_CHAT_ID')
    if env_id:
        return env_id
    if os.path.exists(ID_FILE):
        with open(ID_FILE, 'r') as f:
            return f.read().strip()
    return None

def get_today_name():
    days_ru = {0: "Понеділок", 1: "Вівторок", 2: "Середа", 3: "Четвер", 4: "П'ятниця", 5: "Субота", 6: "Неділя"}
    return days_ru[datetime.now().weekday()]

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📚 Какой следующий урок?")
    markup.add(btn1)
    return markup

@bot.message_handler(func=lambda message: message.text == "📚 Какой следующий урок?")
def next_lesson_info(message):
    now = datetime.now()
    current_day = get_today_name()
    current_time = now.strftime("%H:%M")

    if current_day not in SCHEDULE or not SCHEDULE[current_day]:
        bot.reply_to(message, f"Сегодня ({current_day}) уроков нет! Отдыхай 🎉")
        return

    lessons_today = SCHEDULE[current_day]
    for i in range(1, len(lessons_today) + 1):
        start, end = TIME_SLOTS[i]
        if current_time < start:
            subject = lessons_today[i-1]
            bot.reply_to(message, f"🔔 Следующий урок ({i}-й):\n📖 {subject}\n⏰ Начало: {start}\n🏁 Конец: {end}")
            return
        elif start <= current_time <= end:
            subject = lessons_today[i-1]
            bot.reply_to(message, f"🏃‍♂️ У тебя СЕЙЧАС идет урок ({i}-й):\n📖 {subject}\n⏰ Закончится в {end}")
            return
    bot.reply_to(message, "На сегодня уроки уже закончились! Иди домой 🏠")

@bot.message_handler(commands=['start'])
def start_command(message):
    save_chat_id(message.chat.id)
    bot.reply_to(message, "Привет! Я твой школьный бот. Я запомнил тебя и буду присылать уведомления!", reply_markup=get_main_keyboard())

def check_schedule_and_notify():
    chat_id = get_chat_id()
    if not chat_id:
        return

    now = datetime.now()
    current_day = get_today_name()
    current_time = now.strftime("%H:%M")
    
    if current_day not in SCHEDULE or not SCHEDULE[current_day]:
        return

    lessons_today = SCHEDULE[current_day]

    for i in range(1, len(lessons_today) + 1):
        start_str, end_str = TIME_SLOTS[i]
        subject = lessons_today[i-1]
        start_dt = datetime.strptime(start_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        notify_dt = start_dt - datetime.timedelta(minutes=10)
        
        if now.strftime("%H:%M") == notify_dt.strftime("%H:%M"):
            msg = f"⚠️ Через 10 минут начнется {i}-й урок!\n📖 {subject}\n⏰ Время: {start_str} - {end_str}"
            try: bot.send_message(chat_id, msg)
            except: pass

        if current_time == end_str:
            msg = f"🔔 Урок закончился! ({subject})"
            try: bot.send_message(chat_id, msg)
            except: pass

def run_scheduler():
    schedule.every(1).minutes.do(check_schedule_and_notify)
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- ВЕБХУКИ ДЛЯ RENDER (Вместо polling) ---
@app.route('/')
def index():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403

if __name__ == '__main__':
    # 1. Запускаем таймер проверки расписания
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # 2. Устанавливаем вебхук для Telegram
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if render_url:
        webhook_url = f"{render_url}/webhook"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        print(f"Webhook установлен на {webhook_url}")

    # 3. Запускаем Flask сервер
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
