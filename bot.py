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
    CallbackQueryHandler,
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
        [InlineKeyboardButton("➕ Add me to a Group ➕", url="https://t.me/mygroupmanagement_bot?startgroup=true")],
        [
            InlineKeyboardButton("📣 Group", url="https://t.me/ghelp"),
            InlineKeyboardButton("📢 Channel", url="https://t.me/ghelp")
        ],
        [
            InlineKeyboardButton("🛠️ Support", callback_data="show_support_info"),
            InlineKeyboardButton("ℹ️ Information", callback_data="show_info")
        ],
        [InlineKeyboardButton("🇬🇧 Languages 🇬🇧", callback_data="lang_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        "👋🏻 Hi ❔!\n"
        "@mygroupmanagement_bot is the most complete Bot to help you manage your groups easily and safely!\n\n"
        "👉🏻 Add me in a Supergroup and promote me as Admin to let me get in action!\n\n"
        "❓ WHICH ARE THE COMMANDS? ❓\n"
        "Press /help to see all the commands and how they work!\n"
        "📃 [Privacy policy](https://www.grouphelp.top/privacy)"
    )

    # Check if it's a callback query or a direct /start command
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text=msg,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Failed to edit message in start: {e}. Sending new message instead.")
            await query.message.reply_text(
                text=msg,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, disable_web_page_preview=True, parse_mode="Markdown")

async def show_support_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")] # Only a Back button
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Updated support message content as per your new request
    support_message = (
        "⚠️ We do NOT provide support for ban, mute or other things "
        "related to groups managed by this bot: for this kind of requests "
        "contact the group administrators directly."
    )

    try:
        await query.edit_message_text(
            text=support_message,
            reply_markup=reply_markup,
            parse_mode="HTML", # Using HTML for the warning emoji if it were included
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.warning(f"Failed to edit message in show_support_info: {e}. Sending new message instead.")
        await query.message.reply_text(
            text=support_message,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

# New function for 'Information'
async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Bot Support", url="https://t.me/colonel_support")], # You can customize this link
        [InlineKeyboardButton("Bot commands", callback_data="show_bot_commands")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # You can customize this message if 'Information' should be different from 'Support'
    info_message = (
        "This bot helps you manage your Telegram groups with ease and security.\n\n"
        "<b>Key Features:</b>\n"
        "• User management (kick, ban, mute)\n"
        "• Admin promotion/demotion\n"
        "• Welcome messages for new members\n"
        "• Customizable rules\n"
        "• Periodic announcements to active groups\n\n"
        "For more details on commands, use the /help command or click 'Bot commands' below.\n\n"
    )

    try:
        await query.edit_message_text(
            text=info_message,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.warning(f"Failed to edit message in show_info: {e}. Sending new message instead.")
        await query.message.reply_text(
            text=info_message,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        # Avoid welcoming the bot itself when it's added to a group
        if new_user.id == context.bot.id:
            continue
        await update.message.reply_text(
            f"Welcome, {new_user.full_name}! Please read /rules before chatting."
        )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Group Rules:\n1. Be respectful\n2. No spam\n3. Follow Telegram TOS"
    # This function might be called by a command or a callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(text=text)
        except Exception as e:
            logger.warning(f"Failed to edit message in rules: {e}. Sending new message instead.")
            await query.message.reply_text(text)
    else:
        await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/help - Show this message\n"
        "/rules - Show group rules\n"
        "/kick - Kick a user (reply only)\n"
        "/ban - Ban a user (reply only)\n"
        "/mute - Mute a user (reply only)\n"
        "/promote - Promote user to admin (reply only)\n"
        "/demote - Demote admin (reply only)"
    )

    # This function might be called by a command or a callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(text=help_text)
        except Exception as e:
            logger.warning(f"Failed to edit message in help_command: {e}. Sending new message instead.")
            await query.message.reply_text(text=help_text)
    else:
        await update.message.reply_text(text=help_text)


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
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await context.bot.unban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"Kicked {user.full_name}")
        except Exception as e:
            await update.message.reply_text(f"Failed to kick {user.full_name}. Error: {e}")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "ban")
    if user:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            await update.message.reply_text(f"Banned {user.full_name}")
        except Exception as e:
            await update.message.reply_text(f"Failed to ban {user.full_name}. Error: {e}")

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
            await update.message.reply_text(f"Failed to mute {user.full_name}. Error: {e}")

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
            await update.message.reply_text(f"Promoted {user.full_name} to admin.")
        except Exception as e:
            await update.message.reply_text(f"Failed to promote {user.full_name}. Error: {e}")

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
            await update.message.reply_text(f"Demoted {user.full_name}.")
        except Exception as e:
            await update.message.reply_text(f"Failed to demote {user.full_name}. Error: {e}")

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
        # Make a copy of the set to avoid RuntimeError if chat_ids is modified during iteration
        for chat_id in list(app.chat_ids):
            try:
                # Check if the bot is still a member of the chat before sending
                chat_member = await app.bot.get_chat_member(chat_id=chat_id, user_id=app.bot.id)
                if chat_member.status in ["member", "administrator", "creator"]:
                    msg = await app.bot.send_message(chat_id=chat_id, text=ANNOUNCEMENT_TEXT)
                    await msg.pin()
                    await asyncio.sleep(300)  # Pinned for 5 mins
                    await msg.unpin()
                    await msg.delete()
                else:
                    logger.info(f"Bot no longer a member of chat {chat_id}. Removing from tracking.")
                    app.chat_ids.discard(chat_id)
                    save_chat_ids(app.chat_ids)
            except Exception as e:
                logger.warning(f"Error in chat {chat_id}: {e}")
                # Consider removing chat_id if error indicates bot was kicked/banned
                if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower():
                    logger.info(f"Removing chat {chat_id} due to persistent error.")
                    app.chat_ids.discard(chat_id)
                    save_chat_ids(app.chat_ids)
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

    # Callback Query Handlers
    app.add_handler(CallbackQueryHandler(show_support_info, pattern="^show_support_info$"))
    app.add_handler(CallbackQueryHandler(show_info, pattern="^show_info$"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^show_bot_commands$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^back_to_main_menu$")) # Handle the "Back" button to return to start menu
    # If you implement the lang_menu, you would add a handler here:
    # app.add_handler(CallbackQueryHandler(your_lang_menu_function, pattern="^lang_menu$"))

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=f"https://cooperative-blondelle-saidali-0379e40c.koyeb.app/{token}"
    )

if __name__ == "__main__":
    main()

