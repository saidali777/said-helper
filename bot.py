import logging
import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANNOUNCEMENT_TEXT = "📢 This is an automated recurring announcement."

# === Track all group chat_ids ===

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    app.chat_ids.add(update.effective_chat.id)

# === Periodic Announcement Task ===

async def periodic_announcement(app):
    while True:
        for chat_id in list(app.chat_ids):
            try:
                msg = await app.bot.send_message(chat_id=chat_id, text=ANNOUNCEMENT_TEXT)
                asyncio.create_task(delete_after_delay(app.bot, msg, 300))  # delete after 5 mins
            except Exception as e:
                logger.warning(f"Failed to send message to {chat_id}: {e}")
        await asyncio.sleep(60)  # wait 1 minute before sending again

async def delete_after_delay(bot, message, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
    except Exception as e:
        logger.warning(f"Failed to delete message: {e}")

# === Welcome handler for completeness ===

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        await update.message.reply_text(f"Welcome {new_user.full_name}!")

# === Startup logic ===

async def on_startup(app):
    app.chat_ids = set()
    asyncio.create_task(periodic_announcement(app))

# === Main function ===

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set")

    app = ApplicationBuilder().token(token).build()
    app.post_init = on_startup

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, track_chats))

    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=token,
        webhook_url=f"https://cooperative-blondelle-saidali-0379e40c.koyeb.app/{token}"
    )

if __name__ == "__main__":
    main()


