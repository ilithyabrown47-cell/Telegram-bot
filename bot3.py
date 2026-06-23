from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio

TOKEN="7481985048:AAHMP7jLXSNYSqxS-k-S1DfG7QZCP03OWI4"
GROUP_ID = -1003867246471

all_users = {}
photo_senders = set()
thanked_users = set()

async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_users[user.id] = user.first_name

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    all_users[user.id] = user.first_name
    photo_senders.add(user.id)

    if user.id not in thanked_users:
        thanked_users.add(user.id)

        await update.message.reply_text(
            f"📸 Salamat sa picture, {user.first_name}!"
        )

async def noon_reminder(app):
    missing = []

    for uid, name in all_users.items():
        if uid not in photo_senders:
            missing.append(f"[{name}](tg://user?id={uid})")

    if missing:
        text = (
            "📢 Reminder!\n\n"
            "Hindi pa nakakapag-send ng picture:\n\n"
            + "\n".join(missing)
        )

        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode="Markdown"
        )

    # Reset for next day
    photo_senders.clear()
    thanked_users.clear()

def start_scheduler(app):
    scheduler = BackgroundScheduler(timezone="Asia/Manila")

    scheduler.add_job(
        lambda: asyncio.run(noon_reminder(app)),
        "cron",
        hour=12,
        minute=0
    )

    scheduler.start()

app = Application.builder().token(TOKEN).build()

app.add_handler(
    MessageHandler(filters.ALL, save_user)
)

app.add_handler(
    MessageHandler(filters.PHOTO, photo_handler)
)

start_scheduler(app)

print("Bot is running...")
app.run_polling()