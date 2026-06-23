import os
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    CommandHandler,
    filters,
)

# =====================
# CONFIG
# =====================

TOKEN = os.getenv("7481985048:AAE_j_82JBJqAhph1ejo8CJdXcEC9AmgO3A")
GROUP_ID = int(os.getenv("GROUP_ID", "-1001234567890"))

all_users = {}
photo_senders = set()
thanked_users = set()

# =====================
# SAVE USERS
# =====================
async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        all_users[user.id] = user.first_name

# =====================
# PHOTO HANDLER
# =====================
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    all_users[user.id] = user.first_name
    photo_senders.add(user.id)

    if user.id not in thanked_users:
        thanked_users.add(user.id)

        await update.message.reply_text(
            f"📸 Salamat sa picture, {user.first_name}!"
        )

# =====================
# WELCOME NEW MEMBERS
# =====================
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        all_users[member.id] = member.first_name

        await update.message.reply_text(
            f"🎉 Welcome {member.first_name}!\n"
            f"Please send your photo today 😊"
        )

# =====================
# DAILY REPORT
# =====================
async def daily_report(app: Application):
    missing = []

    for uid, name in all_users.items():
        if uid not in photo_senders:
            missing.append(f"[{name}](tg://user?id={uid})")

    if missing:
        text = (
            "📢 Daily Reminder\n\n"
            "Hindi pa nakakapag-send ng picture:\n\n"
            + "\n".join(missing)
        )

        await app.bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode="Markdown"
        )

    # reset daily
    photo_senders.clear()
    thanked_users.clear()

# =====================
# SIMPLE LOOP (RAILWAY SAFE)
# =====================
async def scheduler(app):
    while True:
        now = datetime.now()

        # run at 12:00 (simple check)
        if now.hour == 12 and now.minute == 0:
            await daily_report(app)
            await asyncio.sleep(60)

        await asyncio.sleep(30)

# =====================
# START COMMAND
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is running ✅")

# =====================
# MAIN
# =====================
def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_user))
    app.add_handler(CommandHandler("start", start))

    async def post_init(app):
        asyncio.create_task(scheduler(app))

    app.post_init = post_init

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()