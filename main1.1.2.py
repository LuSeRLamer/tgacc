import os
import telebot
import sqlite3
from telebot import types
from telebot import REPLY_MARKUP_TYPES
from datetime import datetime
import json
import requests
from tokens import *

bot = telebot.TeleBot(BOT_TOKEN)
ADMIN_ID = 1233743564
ADMIN_ID2 = 7374546254

CRYPTO_HEADERS = {
    "Crypto-Pay-API-Token": CRYPTO_TOKEN
}

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    first_start_date TEXT NOT NULL
)
""")
conn.commit()

cursor.execute("SELECT * FROM users")
print(cursor.fetchall())

cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    file_path TEXT,
    category TEXT,
    price REAL,
    upload_date TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    file_id INTEGER,
    invoice_id INTEGER,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()

def create_invoice(amount, description):

    response = requests.post(
        "https://pay.crypt.bot/api/createInvoice",
        headers=CRYPTO_HEADERS,
        json={
            "asset": "USDT",
            "amount": str(amount),
            "description": description
        }
    )

    data = response.json()

    if not data["ok"]:
        print(data)
        return None

    return data["result"]


def check_invoice(invoice_id):

    response = requests.get(
        "https://pay.crypt.bot/api/getInvoices",
        headers=CRYPTO_HEADERS,
        params={
            "invoice_ids": invoice_id
        }
    )

    data = response.json()

    if not data["ok"]:
        return False

    invoice = data["result"]["items"][0]

    return invoice["status"] == "paid"


def get_real_count(category):
    cursor.execute(
        "SELECT file_path FROM files WHERE category = ?",
        (category,)
    )

    count = 0
    for row in cursor.fetchall():
        if os.path.exists(row[0]):
            count += 1

    return count


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    full_name = (
        f"{message.from_user.first_name or ''} "
        f"{message.from_user.last_name or ''}"
    ).strip()

    # Клавиатура
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    abut = types.KeyboardButton("ℹ️ О нас")
    prof = types.KeyboardButton("Профиль")
    buy = types.KeyboardButton("Купить")
    otz = types.KeyboardButton ("Отзывы")
    markup.row(abut, prof)
    markup.row(buy, otz)

    cursor.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    if user is None:
        first_start_date = datetime.now().strftime("%d.%m.%Y")

        cursor.execute(
            "INSERT INTO users (user_id, full_name, first_start_date) VALUES (?, ?, ?)",
            (user_id, full_name, first_start_date)
        )
        conn.commit()

    with open("img/welcome.jpg", "rb") as photo:
        bot.send_photo(
            message.chat.id,
            photo,
            caption=f"Добро пожаловать, {message.from_user.first_name}!",
            reply_markup=markup
        )

@bot.message_handler(func=lambda m: m.text == "ℹ️ О нас")
def about(message):

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "lvlUP Market",
            url="https://t.me/lvlupmark3t"
        )
    )

    bot.send_message(
        message.chat.id,
        "Актуальная информация о разработке:",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.text == "Отзывы")
def otz(message):

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "lvlUP Отзывы",
            url="https://t.me/lvlupmark3t"
        )
    )
    bot.send_message(
        message.chat.id,
        "Отзывы о нас",
        reply_markup=markup
    )
@bot.message_handler(func=lambda m: m.text == "Профиль")
def profile(message):
    cursor.execute(
        "SELECT first_start_date FROM users WHERE user_id = ?",
        (message.from_user.id,)
    )

    result = cursor.fetchone()

    first_start_date = result[0] if result else "Неизвестно"
    cursor.execute("""
    SELECT COUNT(*)
    FROM orders
    WHERE user_id = ?
    AND status = 'paid'
    """,
    (message.from_user.id,)
)

    purchases = cursor.fetchone()[0]
    bot.send_message(
        message.chat.id,
          f" Имя: {message.from_user.first_name}\nВаш id: {message.from_user.id}\nВы с нами с: {first_start_date}\nКол-во ваших покупок: {purchases}"
        )

@bot.message_handler(func=lambda m: m.text == "Купить")
def buy(message):

    proxy_count = get_real_count("Прокси")
    samoreg_count = get_real_count("ТГ аккаунт (саморег)")
    autoreg_count = get_real_count("ТГ аккаунт (авторег)")

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            f"🌐 Прокси ({proxy_count})",
            callback_data="proxy"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            f"📱 Самореги ({samoreg_count})",
            callback_data="samoreg"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            f"📲 Автореги ({autoreg_count})",
            callback_data="autoreg"
        )
    )

    bot.send_message(
        message.chat.id,
        "Выберите товар:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    categories = {
        "proxy": "Прокси",
        "samoreg": "ТГ аккаунт (саморег)",
        "autoreg": "ТГ аккаунт (авторег)"
    }

    if call.data in categories:

        category = categories[call.data]

        cursor.execute("""
        SELECT id, file_name, file_path, price
        FROM files
        WHERE category = ?
        """, (category,))

        items = cursor.fetchall()

        item = None
        for row in items:
            if os.path.exists(row[2]):
                item = row
                break

        if not item:
            bot.send_message(call.message.chat.id, "❌ Товар закончился.")
            return

        file_id, file_name, file_path, price = item

        invoice = create_invoice(price, f"Покупка {file_name}")

        if not invoice:
            bot.send_message(call.message.chat.id, "Ошибка создания счёта.")
            return

        invoice_id = invoice["invoice_id"]
        pay_url = invoice["bot_invoice_url"]

        cursor.execute("""
        INSERT INTO orders
        (user_id, file_id, invoice_id, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            call.from_user.id,
            file_id,
            invoice_id,
            "waiting",
            datetime.now().strftime("%d.%m.%Y %H:%M")
        ))
        conn.commit()

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"💳 Оплатить ${price}", url=pay_url))
        markup.add(types.InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_{invoice_id}"))

        bot.send_message(
            call.message.chat.id,
            f"📦 Товар: {file_name}\n💰 Цена: ${price}",
            reply_markup=markup
        )

    elif call.data.startswith("check_"):

        invoice_id = int(call.data.replace("check_", ""))

        if not check_invoice(invoice_id):
            bot.answer_callback_query(call.id, "Оплата пока не найдена.")
            return

        cursor.execute("""
        SELECT file_id
        FROM orders
        WHERE invoice_id = ?
        """, (invoice_id,))

        order = cursor.fetchone()

        if not order:
            bot.answer_callback_query(call.id, "Товар уже выдан.")
            return

        file_id_db = order[0]

        cursor.execute("""
        SELECT file_path
        FROM files
        WHERE id = ?
        """, (file_id_db,))

        result = cursor.fetchone()

        if not result:
            return

        file_path = result[0]

        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, "Файл отсутствует на сервере.")
            return

        with open(file_path, "rb") as f:
            bot.send_document(call.message.chat.id, f)

        os.remove(file_path)

        cursor.execute("""
        UPDATE orders
        SET status = 'paid'
        WHERE invoice_id = ?
        """, (invoice_id,))

        cursor.execute("""
        DELETE FROM files
        WHERE id = ?
        """, (file_id_db,))

        conn.commit()

        bot.send_message(
            call.message.chat.id,
            "✅ Оплата подтверждена.\nТовар успешно выдан."
        )

        bot.answer_callback_query(call.id)

@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id not in (ADMIN_ID, ADMIN_ID2):
        bot.send_message(message.chat.id, "Нет доступа.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📢 Рассылка"))
    markup.add(types.KeyboardButton("📁 Загрузить файл"))
    markup.add(types.KeyboardButton("📦 Остатки"))
    markup.add(types.KeyboardButton("📋 Товары"))
    markup.add(types.KeyboardButton("🗑 Удалить товар"))

    bot.send_message(
        message.chat.id,
        "Админ-панель",
        reply_markup=markup
    )

waiting_broadcast = set()
waiting_file = set()
waiting_category = {}
selected_category = {}
selected_price = {}
waiting_price = set()

@bot.message_handler(func=lambda m: m.text == "📁 Загрузить файл")
def upload_file_button(message):

    if message.from_user.id not in (ADMIN_ID, ADMIN_ID2):
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.add(types.KeyboardButton("ТГ аккаунт (саморег)"))
    markup.add(types.KeyboardButton("ТГ аккаунт (авторег)"))
    markup.add(types.KeyboardButton("Прокси"))

    bot.send_message(
        message.chat.id,
        "Выберите категорию:",
        reply_markup=markup
    )

    waiting_category[message.from_user.id] = True

@bot.message_handler(
    func=lambda m:
    m.from_user.id in waiting_category
    and m.text in [
        "ТГ аккаунт (саморег)",
        "ТГ аккаунт (авторег)",
        "Прокси"
    ]
)
def choose_category(message):

    selected_category[message.from_user.id] = message.text

    waiting_price.add(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "Введите цену товара:"
    )
    waiting_category.pop(message.from_user.id, None)
@bot.message_handler(func=lambda m: m.text == "📢 Рассылка")
def broadcast_button(message):
    if message.from_user.id not in (ADMIN_ID, ADMIN_ID2):
        return
    
    waiting_broadcast.add(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "Отправьте текст, фото, GIF или видео для рассылки:"
    )

@bot.message_handler(
    func=lambda m: m.from_user.id in waiting_broadcast,
    content_types=['text', 'photo', 'video', 'animation', 'document']
)
def process_broadcast(message):
    waiting_broadcast.remove(message.from_user.id)

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    success = 0
    failed = 0

    for user in users:
        try:
            bot.copy_message(
                chat_id=user[0],
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success += 1
        except Exception as e:
            print(e)
            failed += 1

    report = (
        f"✅ Рассылка завершена\n\n"
        f"Успешно: {success}\n"
        f"Ошибок: {failed}"
    )

    bot.send_message(message.chat.id, report)

os.makedirs("uploads", exist_ok=True)

@bot.message_handler(func=lambda m: m.from_user.id in waiting_price)
def choose_price(message):

    try:
        price = float(message.text.replace(",", "."))

    except ValueError:
        bot.send_message(
            message.chat.id,
            "Введите число. Например: 150 или 99.99"
        )
        return

    waiting_price.remove(message.from_user.id)

    selected_price[message.from_user.id] = price

    waiting_file.add(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "Теперь отправьте файл."
    )

@bot.message_handler(
    content_types=['document'],
    func=lambda m: m.from_user.id in waiting_file
)
def receive_file(message):

    waiting_file.remove(message.from_user.id)

    category = selected_category.get(
        message.from_user.id,
        "Без категории"
    )

    price = selected_price.get(
        message.from_user.id,
        0
    )

    file_id = message.document.file_id
    file_name = message.document.file_name

    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    save_path = (
    f"uploads/"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
    )

    with open(save_path, "wb") as f:
        f.write(downloaded_file)

    cursor.execute("""
        INSERT INTO files
        (file_name, file_path, category, price, upload_date)
        VALUES (?, ?, ?, ?, ?)
    """,
    (
        file_name,
        save_path,
        category,
        price,
        datetime.now().strftime("%d.%m.%Y %H:%M")
    ))

    conn.commit()

    bot.send_message(
        message.chat.id,
        f"✅ Файл {file_name} успешно загружен.\n"
        f"📂 Категория: {category}\n"
        f"💰 Цена: {price}"
    )

    selected_category.pop(message.from_user.id, None)
    selected_price.pop(message.from_user.id, None)

def cleanup_missing_files():

    cursor.execute(
        "SELECT id, file_path FROM files"
    )

    for row in cursor.fetchall():

        if not os.path.exists(row[1]):

            cursor.execute(
                "DELETE FROM files WHERE id = ?",
                (row[0],)
            )

    conn.commit()


cleanup_missing_files()

cursor.execute("PRAGMA table_info(files)")
print(cursor.fetchall())
cleanup_missing_files()


# =========================
# ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ АДМИНКИ
# =========================

@bot.message_handler(func=lambda m: m.text == "📦 Остатки")
def stock_info(message):

    if message.from_user.id not in (ADMIN_ID, ADMIN_ID2):
        return

    proxy_count = get_real_count("Прокси")
    samoreg_count = get_real_count("ТГ аккаунт (саморег)")
    autoreg_count = get_real_count("ТГ аккаунт (авторег)")

    bot.send_message(
        message.chat.id,
        f"📦 Остатки:\n\n"
        f"🌐 Прокси: {proxy_count}\n"
        f"📱 Самореги: {samoreg_count}\n"
        f"📲 Автореги: {autoreg_count}"
    )



# =====================================================
# ДОБАВИТЬ В АДМИН-ПАНЕЛЬ:
#
# markup.add(types.KeyboardButton("📦 Остатки"))
# markup.add(types.KeyboardButton("📋 Товары"))
# markup.add(types.KeyboardButton("🗑 Удалить товар"))
#
# =====================================================

delete_waiting = set()

@bot.message_handler(func=lambda m: m.text == "📋 Товары")
def list_products(message):

    if message.from_user.id not in (ADMIN_ID, ADMIN_ID2):
        return

    cursor.execute(
        "SELECT id, file_name, category, price FROM files ORDER BY id"
    )

    items = cursor.fetchall()

    if not items:
        bot.send_message(message.chat.id, "Товаров нет.")
        return

    text = "📋 Список товаров:\n\n"

    for item in items:
        text += (
            f"ID: {item[0]}\n"
            f"Файл: {item[1]}\n"
            f"Категория: {item[2]}\n"
            f"Цена: ${item[3]}\n\n"
        )

    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "🗑 Удалить товар")
def delete_product(message):

    if message.from_user.id not in (ADMIN_ID, ADMIN_ID2):
        return

    delete_waiting.add(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "Введите ID товара для удаления:"
    )


@bot.message_handler(func=lambda m: m.from_user.id in delete_waiting)
def process_delete(message):

    try:
        product_id = int(message.text)
    except:
        bot.send_message(message.chat.id, "Введите числовой ID.")
        return

    cursor.execute(
        "SELECT file_path FROM files WHERE id = ?",
        (product_id,)
    )

    item = cursor.fetchone()

    if not item:
        bot.send_message(message.chat.id, "Товар не найден.")
        delete_waiting.discard(message.from_user.id)
        return

    file_path = item[0]

    if os.path.exists(file_path):
        os.remove(file_path)

    cursor.execute(
        "DELETE FROM files WHERE id = ?",
        (product_id,)
    )

    conn.commit()

    delete_waiting.discard(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "✅ Товар удалён."
    )


def cleanup_missing_files():

    cursor.execute(
        "SELECT id, file_path FROM files"
    )

    for row in cursor.fetchall():

        if not os.path.exists(row[1]):

            cursor.execute(
                "DELETE FROM files WHERE id = ?",
                (row[0],)
            )

    conn.commit()

print("Bot started")
bot.infinity_polling()