import os
import asyncio
import sqlite3
from datetime import datetime, timedelta

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

# =========================
# TIME (NO PYTZ FIX)
# =========================

def manila_time():
    return datetime.utcnow() + timedelta(hours=8)

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    photo_count INTEGER DEFAULT 0,
    last_seen TEXT
)
""")
conn.commit()

# =========================
# DB FUNCTIONS
# =========================

def upsert_user(user_id, name):
    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, name, photo_count, last_seen)
    VALUES (?, ?, 0, ?)
    """, (user_id, name, str(manila_time())))

    cursor.execute("""
    UPDATE users
    SET name=?, last_seen=?
    WHERE user_id=?
    """, (name, str(manila_time()), user_id))

    conn.commit()

def add_photo(user_id, name):
    upsert_user(user_id, name)

    cursor.execute("""
    UPDATE users
    SET photo_count = photo_count + 1,
        last_seen = ?
    WHERE user_id = ?
    """, (str(manila_time()), user_id))

    conn.commit()

# =========================
# HANDLERS
# =========================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    add_photo(user.id, user.first_name)

    await update.message.reply_text(
        f"📸 Thanks for sharing  {user.first_name}! Photo recorded ✔"
    )

async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        upsert_user(user.id, user.first_name)

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        upsert_user(member.id, member.first_name)

        await update.message.reply_text(
            f"🎉 Welcome {member.first_name}!\nSend sp3nder daily 📸"
        )

# =========================
# AUTO KICK (2 DAYS INACTIVE)
# =========================

async def auto_kick(app: Application):
    now = manila_time()

    cursor.execute("SELECT user_id, name, last_seen FROM users")
    users = cursor.fetchall()

    for user_id, name, last_seen in users:
        try:
            last_time = datetime.fromisoformat(last_seen)
        except:
            continue

        if now - last_time >= timedelta(days=2):
            try:
                await app.bot.ban_chat_member(
                    chat_id=GROUP_ID,
                    user_id=user_id
                )

                await app.bot.send_message(
                    chat_id=GROUP_ID,
                    text=f"🚫 {name} removed (2 days inactive)"
                )

                cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
                conn.commit()

            except Exception as e:
                print("Kick error:", e)

# =========================
# DAILY CHECK (NO APSCHEDULER)
# =========================

async def scheduler(app: Application):
    while True:
        now = manila_time()

        # run daily at 12:00 PM
        if now.hour == 12 and now.minute == 0:
            await app.bot.send_message(
                chat_id=GROUP_ID,
                text="📢 Daily check running..."
            )

            await auto_kick(app)
            await asyncio.sleep(60)

        await asyncio.sleep(30)

# =========================
# START
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

    async def post_init(app):
        asyncio.create_task(scheduler(app))

    app.post_init = post_init

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()