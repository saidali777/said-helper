import logging
import os
import asyncio
from aiohttp import web
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

active_groups = set()
ANNOUNCEMENT_TEXT = "📢 This is a scheduled announcement."

# === Handler functions ===

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        await update.message.reply_text(
            f"Welcome, {new_user.full_name}! Please read /rules before chatting."
        )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Group Rules:\n1. Be respectful\n2. No spam\n3. Follow Telegram TOS")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/help - Show this message\n"
        "/rules - Show group rules\n"
        "/kick - Kick a user (reply only)\n"
        "/ban - Ban a user (reply only)\n"
        "/mute - Mute a user (reply only)\n"
        "/promote - Promote to admin (reply only)\n"
        "/demote - Demote admin (reply only)"
    )
    await update.message.reply_text(help_text)

async def is_admin(update: Update, user_id: int) -> bool:
    admins = await update.effective_chat.get_administrators()
    return any(admin.user.id == user_id for admin in admins)

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
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await context.bot.unban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"Kicked {user.full_name}")
        except Exception as e:
            await update.message.reply_text(f"Failed to kick user: {e}")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "ban")
    if user:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"Banned {user.full_name}")
        except Exception as e:
            await update.message.reply_text(f"Failed to ban user: {e}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "mute")
    if user:
        try:
            await context.bot.restrict_chat_member(
                update.effective_chat.id,
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            await update.message.reply_text(f"Muted {user.full_name}")
        except Exception as e:
            await update.message.reply_text(f"Failed to mute user: {e}")

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "promote")
    if user:
        try:
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
            await update.message.reply_text(f"Promoted {user.full_name}")
        except Exception as e:
            await update.message.reply_text(f"Failed to promote user: {e}")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "demote")
    if user:
        try:
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
            await update.message.reply_text(f"Demoted {user.full_name}")
        except Exception as e:
            await update.message.reply_text(f"Failed to demote user: {e}")

# Track groups where bot is present
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_groups.add(update.effective_chat.id)

# Periodic announcement task with pin, delete, wait cycle
async def periodic_announcements(app):
    while True:
        for chat_id in list(active_groups):
            try:
                # Send announcement
                msg = await app.bot.send_message(chat_id=chat_id, text=ANNOUNCEMENT_TEXT)
                # Pin it (disable notification for pin)
                await app.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id, disable_notification=True)

                # Wait 5 minutes
                await asyncio.sleep(300)

                # Delete the pinned message
                await msg.delete()

                # Wait 3 minutes before next message in this chat
                await asyncio.sleep(180)

            except Exception as e:
                logger.error(f"Error in chat {chat_id}: {e}")

        # Short delay before next cycle (optional)
        await asyncio.sleep(5)


# Health check endpoint for Koyeb
async def health_check(request):
    return web.Response(text="OK")


async def start_bot():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment variables.")

    app = ApplicationBuilder().token(token).build()

    # Register handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, track_groups))

    # Start the periodic announcement task
    app.create_task(periodic_announcements(app))

    # Setup aiohttp web server for health check
    aio_app = web.Application()
    aio_app.add_routes([web.get("/", health_check)])

    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()

    # Start Telegram webhook
    await app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=token,
        webhook_url=f"https://cooperative-blondelle-saidali-0379e40c.koyeb.app/{token}",
    )


if __name__ == "__main__":
    asyncio.run(start_bot())



