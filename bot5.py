import os
import asyncio
from datetime import datetime, timedelta

from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "-1003773746541"))

if not TOKEN:
    raise Exception("BOT_TOKEN is missing in Railway Variables!")

all_users = {}
photo_senders = set()
thanked_users = set()

# store last activity date
last_seen = {}  # user_id -> datetime

MANILA = timezone("Asia/Manila")

# =========================
# SAVE USERS
# =========================
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        all_users[user.id] = user.first_name
        last_seen[user.id] = datetime.now(MANILA)

# =========================
# PHOTO HANDLER
# =========================
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    all_users[user.id] = user.first_name
    photo_senders.add(user.id)
    last_seen[user.id] = datetime.now(MANILA)

    if user.id not in thanked_users:
        thanked_users.add(user.id)

        await update.message.reply_text(
            f"📸 Thanks for sharing, {user.first_name}!"
        )

# =========================
# WELCOME NEW MEMBERS
# =========================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        all_users[member.id] = member.first_name
        last_seen[member.id] = datetime.now(MANILA)

        await update.message.reply_text(
            f"🎉 Welcome {member.first_name}!\n"
            f"Please send your spender daily 😊"
        )

# =========================
# AUTO KICK FUNCTION
# =========================
async def auto_kick(app: Application):
    now = datetime.now(MANILA)

    for user_id, last_time in list(last_seen.items()):
        if now - last_time >= timedelta(days=2):

            try:
                await app.bot.ban_chat_member(
                    chat_id=GROUP_ID,
                    user_id=user_id
                )

                await app.bot.send_message(
                    chat_id=GROUP_ID,
                    text=f"🚫 User {all_users.get(user_id, 'Unknown')} removed for inactivity (2 days no photo)."
                )

                # remove from memory
                last_seen.pop(user_id, None)
                all_users.pop(user_id, None)
                photo_senders.discard(user_id)
                thanked_users.discard(user_id)

            except Exception as e:
                print("Kick error:", e)

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
            "Hindi pa nakakapag-send ng spender\n\n"
            + "\n".join(missing)
        )

        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode="Markdown"
        )

    photo_senders.clear()
    thanked_users.clear()

# =========================
# SCHEDULER
# =========================
def start_scheduler(app: Application):
    scheduler = AsyncIOScheduler(timezone=MANILA)

    # daily reminder at 12:00
    scheduler.add_job(
        lambda: asyncio.create_task(daily_report(app)),
        "cron",
        hour=12,
        minute=0
    )

    # auto kick check every hour
    scheduler.add_job(
        lambda: asyncio.create_task(auto_kick(app)),
        "interval",
        hours=1
    )

    scheduler.start()

# =========================
# START COMMAND
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is running ✅")

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_user))
    app.add_handler(CommandHandler("start", start))

    start_scheduler(app)

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()