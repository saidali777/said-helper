import logging
import os
import asyncio
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANNOUNCEMENT_TEXT = "📢 This is a recurring announcement."

# === Handler functions ===

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        await update.message.reply_text(
            f"Welcome, {new_user.full_name}! Please read /rules before chatting."
        )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Group Rules:\n1. Be respectful\n2. No spam\n3. Follow Telegram TOS")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/help - Show this message\n"
        "/rules - Show group rules\n"
        "/kick - Kick a user (reply only)\n"
        "/ban - Ban a user (reply only)\n"
        "/mute - Mute a user (reply only)\n"
        "/promote - Promote user to admin (reply only)\n"
        "/demote - Demote admin (reply only)"
    )

async def is_admin(update: Update, user_id: int) -> bool:
    chat_admins = await update.effective_chat.get_administrators()
    return any(admin.user.id == user_id for admin in chat_admins)

async def require_reply(update, context, action_name):
    if not update.message.reply_to_message:
        await update.message.reply_text(f"Reply to a user's message to use /{action_name}.")
        return None
    if not await is_admin(update, update.message.from_user.id):
        await update.message.reply_text("Only admins can use this command.")
        return None
    return update.message.reply_to_message.from_user

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "kick")
    if user:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"Kicked {user.full_name}")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "ban")
    if user:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"Banned {user.full_name}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "mute")
    if user:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            user.id,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await update.message.reply_text(f"Muted {user.full_name}")

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "promote")
    if user:
        await context.bot.promote_chat_member(
            update.effective_chat.id,
            user.id,
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=False,
        )
        await update.message.reply_text(f"Promoted {user.full_name} to admin.")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "demote")
    if user:
        await context.bot.promote_chat_member(
            update.effective_chat.id,
            user.id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
        )
        await update.message.reply_text(f"Demoted {user.full_name}.")

# === Track all group chat_ids ===

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    app.chat_ids.add(update.effective_chat.id)

# === Periodic Announcement Function ===

async def periodic_announcement(app):
    while True:
        for chat_id in list(app.chat_ids):
            try:
                msg = await app.bot.send_message(chat_id=chat_id, text=ANNOUNCEMENT_TEXT)
                await msg.pin()
                # Keep pinned for 5 minutes
                await asyncio.sleep(300)
                # Unpin and delete message
                await msg.unpin()
                await msg.delete()
            except Exception as e:
                logger.warning(f"Failed in group {chat_id}: {e}")

        # Wait 3 minutes before sending again
        await asyncio.sleep(180)

# === On startup ===

async def on_startup(app):
    app.chat_ids = set()
    app.create_task(periodic_announcement(app))

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set")

    app = ApplicationBuilder().token(token).build()

    app.post_init = on_startup

    # Register handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, track_chats))

    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=token,
        webhook_url=f"https://cooperative-blondelle-saidali-0379e40c.koyeb.app/{token}"
    )

if __name__ == "__main__":
    main()

