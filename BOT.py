import json
import time
import hmac
import hashlib

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import os
TOKEN = os.getenv("TOKEN")

MAIN_ADMIN = 6160632777

ADMINS_FILE = "admins.json"
DATA_FILE = "data.json"


# ---------- LOAD/SAVE ----------
def load(file, default):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default


def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f)


admins = load(ADMINS_FILE, [MAIN_ADMIN])
data = load(DATA_FILE, {})


def is_admin(user_id):
    return user_id in admins


# ---------- TOTP ----------
def generate_code(secret: str):
    step = int(time.time() // 10)
    msg = str(step).encode()

    h = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return str(int(h[:8], 16))[-6:]


# ---------- KEYBOARD ----------
menu_kb = ReplyKeyboardMarkup(
    [["➕ Добавить", "🔑 Получить"], ["🗑 Удалить", "📋 Список"]],
    resize_keyboard=True
)


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Нет доступа")
        return

    context.user_data.clear()
    await update.message.reply_text("Меню:", reply_markup=menu_kb)


# ---------- ADD ADMIN ----------
async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != MAIN_ADMIN:
        await update.message.reply_text("⛔ Только главный админ")
        return

    try:
        new_id = int(context.args[0])
        if new_id not in admins:
            admins.append(new_id)
            save(ADMINS_FILE, admins)
            await update.message.reply_text(f"✅ Админ добавлен: {new_id}")
        else:
            await update.message.reply_text("ℹ️ Уже админ")
    except:
        await update.message.reply_text("Использование: /addadmin <id>")


# ---------- TEXT HANDLER ----------
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if not is_admin(user_id):
        return

    state = context.user_data.get("state")

    # -------- MENU BUTTONS --------
    if text == "➕ Добавить":
        context.user_data["state"] = "add_name"
        await update.message.reply_text("Введи имя:")
        return

    if text == "🔑 Получить":
        context.user_data["state"] = "get_code"
        await update.message.reply_text("Введи имя:")
        return

    if text == "🗑 Удалить":
        context.user_data["state"] = "delete"
        await update.message.reply_text("Введи имя для удаления:")
        return

    if text == "📋 Список":
        if not data:
            await update.message.reply_text("Пусто")
        else:
            await update.message.reply_text("\n".join(data.keys()))
        return


    # -------- ADD FLOW --------
    if state == "add_name":
        context.user_data["temp_name"] = text
        context.user_data["state"] = "add_secret"
        await update.message.reply_text("Теперь введи secret:")
        return

    if state == "add_secret":
        name = context.user_data["temp_name"]
        data[name] = text
        save(DATA_FILE, data)

        context.user_data.clear()
        await update.message.reply_text(f"✅ Добавлено: {name}")
        return


    # -------- GET CODE --------
    if state == "get_code":
        secret = data.get(text)

        if not secret:
            await update.message.reply_text("❌ Не найдено")
        else:
            code = generate_code(secret)
            await update.message.reply_text(f"🔐 Код: {code}\n⏱ ~10 сек")

        context.user_data.clear()
        return


    # -------- DELETE --------
    if state == "delete":
        if text in data:
            del data[text]
            save(DATA_FILE, data)
            await update.message.reply_text("🗑 Удалено")
        else:
            await update.message.reply_text("❌ Не найдено")

        context.user_data.clear()
        return


# ---------- APP ----------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addadmin", addadmin))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("Bot running...")
app.run_polling()
