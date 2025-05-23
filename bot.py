import logging
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
announcement_interval = 3 * 60  # 3 minutes
repin_interval = 1 * 60  # 1 minute

def get_announcement_text():
    return "\u2728 *Reminder* \u2728\nPlease follow the group rules and be respectful!"

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(f"Welcome, {member.full_name}!")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please be respectful and follow the group rules.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I'm here to help! Use /rules to see the rules.")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        user_id = int(context.args[0])
        await context.bot.ban_chat_member(update.effective_chat.id, user_id)
        await context.bot.unban_chat_member(update.effective_chat.id, user_id)
        await update.message.reply_text(f"User {user_id} has been kicked.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        user_id = int(context.args[0])
        await context.bot.ban_chat_member(update.effective_chat.id, user_id)
        await update.message.reply_text(f"User {user_id} has been banned.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        user_id = int(context.args[0])
        until = datetime.utcnow() + timedelta(minutes=10)
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            user_id,
            ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await update.message.reply_text(f"User {user_id} has been muted for 10 minutes.")

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        user_id = int(context.args[0])
        await context.bot.promote_chat_member(
            update.effective_chat.id,
            user_id,
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=False,
        )
        await update.message.reply_text(f"User {user_id} has been promoted.")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        user_id = int(context.args[0])
        await context.bot.promote_chat_member(
            update.effective_chat.id,
            user_id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
        )
        await update.message.reply_text(f"User {user_id} has been demoted.")

async def periodic_announcement(app):
    pin_msg = None
    while True:
        for chat_id in app.chat_ids:
            text = get_announcement_text()
            if pin_msg:
                try:
                    await app.bot.unpin_chat_message(chat_id, pin_msg.message_id)
                    await app.bot.delete_message(chat_id, pin_msg.message_id)
                except:
                    pass
            pin_msg = await app.bot.send_message(chat_id, text, parse_mode="Markdown")
            await app.bot.pin_chat_message(chat_id, pin_msg.message_id, disable_notification=True)

            await asyncio.sleep(repin_interval)
            await app.bot.unpin_chat_message(chat_id, pin_msg.message_id)
            await app.bot.pin_chat_message(chat_id, pin_msg.message_id, disable_notification=True)

        await asyncio.sleep(announcement_interval)

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.application.chat_ids.add(chat_id)

async def on_startup(app):
    app.chat_ids = set()
    app.create_task(periodic_announcement(app))
    print("\u2705 Bot started and periodic announcements scheduled.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set")

    app = ApplicationBuilder().token(token).post_init(on_startup).build()

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

if __name__ == '__main__':
    main()

