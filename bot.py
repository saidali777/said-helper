import os
import logging
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Utility to check admin
async def is_admin(update: Update, user_id: int) -> bool:
    admins = await update.effective_chat.get_administrators()
    return any(admin.user.id == user_id for admin in admins)

# Commands and moderation handlers...
# (Paste your existing welcome, help, rules, kick, ban, mute, promote, demote functions here)

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment variables.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))

    # Start webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=8443,
        url_path=token,
       webhook_url=f"https://cooperative-blondelle-saidali-0379e40c.koyeb.app/{token}"  # 🔁 Replace with your real domain
    )

if __name__ == "__main__":
    main()
