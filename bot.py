import logging
import os
import json
import asyncio
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANNOUNCEMENT_TEXT = "📢 This is a recurring announcement."
DATA_FILE = "chat_ids.json"

# === Load/Save Chat IDs ===

def load_chat_ids():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_chat_ids(chat_ids):
    with open(DATA_FILE, "w") as f:
        json.dump(list(chat_ids), f)

# === Handler functions ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Add me to a Group ➕", url="https://t.me/YourBotUsername?startgroup=true")],
        [
            InlineKeyboardButton("📣 Group", url="https://t.me/ghelp"),
            InlineKeyboardButton("📢 Channel", url="https://t.me/ghelp")
        ],
        [
            InlineKeyboardButton("🛠️ Support", url="https://t.me/YourSupportLink"),
            InlineKeyboardButton("ℹ️ Information", url="https://t.me/YourInfoLink")
        ],
        [InlineKeyboardButton("🇬🇧 Languages 🇬🇧", callback_data="lang_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        "👋🏻 Hi ❔!\n"
        "@GroupHelpBot is the most complete Bot to help you manage your groups easily and safely!\n\n"
        "👉🏻 Add me in a Supergroup and promote me as Admin to let me get in action!\n\n"
        "❓ WHICH ARE THE COMMANDS? ❓\n"
        "Press /help to see all the commands and how they work!\n"
        "📃 [Privacy policy](https://www.grouphelp.top/privacy)"
    )

    await update.message.reply_text(msg, reply_markup=reply_markup, disable_web_page_preview=True, parse_mode="Markdown")

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
    try:
        chat_admins = await update.effective_chat.get_administrators()
        return any(admin.user.id == user_id for admin in chat_admins)
    except Exception as e:
        logger.warning(f"Admin check failed: {e}")
        return False

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

# === Chat tracking ===

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    chat_id = update.effective_chat.id
    if chat_id not in app.chat_ids:
        app.chat_ids.add(chat_id)
        save_chat_ids(app.chat_ids)

# === Periodic Announcement ===

async def periodic_announcement(app):
    while True:
        for chat_id in list(app.chat_ids):
            try:
                msg = await app.bot.send_message(chat_id=chat_id, text=ANNOUNCEMENT_TEXT)
                await msg.pin()
                await asyncio.sleep(300)  # Pinned for 5 mins
                await msg.unpin()
                await msg.delete()
            except Exception as e:
                logger.warning(f"Error in chat {chat_id}: {e}")
        await asyncio.sleep(10)  # 10 seconds before next round

# === On startup ===

async def on_startup(app):
    app.chat_ids = load_chat_ids()
    app.create_task(periodic_announcement(app))

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set")

    port = int(os.environ.get("PORT", 8000))
    app = ApplicationBuilder().token(token).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
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
        port=port,
        url_path=token,
        webhook_url=f"https://cooperative-blondelle-saidali-0379e40c.koyeb.app/{token}"
    )

if __name__ == "__main__":
    main()



