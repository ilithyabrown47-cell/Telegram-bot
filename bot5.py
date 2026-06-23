import os
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG (FIXED)
# =========================

TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "-1003773746541"))

if not TOKEN:
    raise Exception("BOT_TOKEN is missing in Railway Variables!")

all_users = {}
photo_senders = set()
thanked_users = set()

# =========================
# SAVE USERS
# =========================
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        all_users[user.id] = user.first_name

# =========================
# PHOTO HANDLER
# =========================
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    all_users[user.id] = user.first_name
    photo_senders.add(user.id)

    if user.id not in thanked_users:
        thanked_users.add(user.id)

        await update.message.reply_text(
            f"📸 Salamat sa picture, {user.first_name}!"
        )

# =========================
# WELCOME NEW MEMBERS
# =========================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        all_users[member.id] = member.first_name

        await update.message.reply_text(
            f"🎉 Welcome {member.first_name}!\n"
            f"Please send your picture today 😊"
        )

# =========================
# DAILY REPORT
# =========================
async def daily_report(app: Application):
    missing = []

    for uid, name in all_users.items():
        if uid not in photo_senders:
            missing.append(f"[{name}](tg://user?id={uid})")

    if missing:
        text = (
            "📢 Daily Reminder\n\n"
            "