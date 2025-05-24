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
from telegram.error import RetryAfter # Import RetryAfter for flood control handling

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
        "📃 <a href='https://www.grouphelp.top/privacy'>Privacy policy</a>"
    )

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.edit_message_text(
                text=msg,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Failed to edit message in start: {e}. Sending new message instead.")
            await query.message.reply_text(
                text=msg,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, disable_web_page_preview=True, parse_mode="HTML")

async def show_support_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    support_message = (
        "⚠️ We do NOT provide support for ban, mute or other things "
        "related to groups managed by this bot: for this kind of requests "
        "contact the group administrators directly."
    )

    try:
        await query.edit_message_text(
            text=support_message,
            reply_markup=reply_markup,
            parse_mode="HTML",
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

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Bot Support", url="https://t.me/colonel_support")],
        [InlineKeyboardButton("Bot commands", callback_data="show_bot_commands")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

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
        if new_user.id == context.bot.id:
            continue
        await update.message.reply_text(
            f"Welcome, {new_user.full_name}! Please read /rules before chatting."
        )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Group Rules:\n1. Be respectful\n2. No spam\n3. Follow Telegram TOS"
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

# === Language Menu Functions ===

async def lang_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    languages = [
        ("🇬🇧 English", "en"), ("🇮🇹 Italiano", "it"),
        ("🇪🇸 Español", "es"), ("🇵🇹 Português", "pt"),
        ("🇩🇪 Deutsch", "de"), ("🇫🇷 Français", "fr"),
        ("🇷🇴 Română", "ro"), ("🇳🇱 Nederlands", "nl"),
        ("🇨🇳 简体中文", "zh-hans"), ("🇺🇦 Українська", "uk"),
        ("🇷🇺 Русский", "ru"), ("🇰🇿 Қазақ", "kk"),
        ("🇹🇷 Türkçe", "tr"), ("🇮🇩 Indonesia", "id"),
        ("🇦🇿 Azərbaycan", "az"), ("🇺🇿 O'zbekcha", "uz"),
        ("🇺🇦 Uyghurche", "ug"), ("🇲🇾 Melayu", "ms"),
        ("🇸🇴 Soomaali", "so"), ("🇦🇱 Shqipja", "sq"),
        ("🇷🇸 Srpski", "sr"), ("🇬🇷 Ελληνικά", "el"),
        ("🇪🇹 Amharic", "am"), ("🇵🇰 اردو", "ur"),
        ("🇰🇷 한국어", "ko"), ("🇮🇷 فارسی", "fa"),
        ("🇮🇳 తెలుగు", "te"), ("🇮🇳 ગુજરાતી", "gu"),
        ("🇮🇳 ਪੰਜਾਬੀ", "pa"), ("🇮🇳 ಕನ್ನಡ", "kn"),
        ("🇮🇳 മലയാളം", "ml"), ("🇮🇳 ଓଡ଼ିଆ", "or"),
        ("🇧🇩 বাংলা", "bn")
    ]

    keyboard = []
    for i in range(0, len(languages), 2):
        row = []
        row.append(InlineKeyboardButton(languages[i][0], callback_data=f"set_lang:{languages[i][1]}"))
        if i + 1 < len(languages):
            row.append(InlineKeyboardButton(languages[i+1][0], callback_data=f"set_lang:{languages[i+1][1]}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            text="Choose your language:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.warning(f"Failed to edit message in lang_menu: {e}. Sending new new message instead.")
        await query.message.reply_text(
            text="Choose your language:",
            reply_markup=reply_markup
        )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lang_code = query.data.split(":")[1]
    
    language_names = {
        "en": "English", "it": "Italiano", "es": "Español", "pt": "Português",
        "de": "Deutsch", "fr": "Français", "ro": "Română", "nl": "Nederlands",
        "zh-hans": "简体中文", "uk": "Українська", "ru": "Русский", "kk": "Қазақ",
        "tr": "Türkçe", "id": "Indonesia", "az": "Azərbaycan", "uz": "O'zbekcha",
        "ug": "Uyghurche", "ms": "Melayu", "so": "Soomaali", "sq": "Shqipja",
        "sr": "Srpski", "el": "Ελληνικά", "am": "Amharic", "ur": "اردو",
        "ko": "한국어", "fa": "فارसी", "te": "తెలుగు", "gu": "ગુજરાતી",
        "pa": "ਪੰਜਾਬੀ", "kn": "ಕನ್ನಡ", "ml": "മലയാളം", "or": "ଓଡ଼ିଆ",
        "bn": "বাংলা"
    }
    
    chosen_language_name = language_names.get(lang_code, "Unknown")
    
    confirmation_message = f"Language set to {chosen_language_name}."

    try:
        await query.edit_message_text(
            text=confirmation_message,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main_menu")]])
        )
    except Exception as e:
        logger.warning(f"Failed to edit message in set_language: {e}. Sending new message instead.")
        await query.message.reply_text(
            text=confirmation_message,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main_menu")]])
        )


# === Chat tracking ===

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    chat_id = update.effective_chat.id
    if chat_id not in app.chat_ids:
        app.chat_ids.add(chat_id)
        save_chat_ids(app.chat_ids)
        logger.info(f"New chat {chat_id} added and saved.") # Log when a new chat is added

# === Periodic Announcement ===

async def periodic_announcement(app):
    first_run = True # Flag to control the initial sleep
    while True:
        if not first_run:
            # Only sleep for the full interval AFTER the first run
            await asyncio.sleep(60 * 60) # Main loop sleep: Check every 1 hour (adjust as needed)
        first_run = False # After the first potential execution, set to False

        chats_to_announce = list(app.chat_ids) # Iterate over a copy
        if not chats_to_announce: # Avoid error if no chats
            logger.info("No chats to announce to. Sleeping for 60 seconds.")
            await asyncio.sleep(60) # Sleep shorter if no chats, then re-check
            continue # Continue to the next iteration (which will now wait for 1 hour if chats are added)

        for chat_id in chats_to_announce:
            try:
                chat_member = await app.bot.get_chat_member(chat_id=chat_id, user_id=app.bot.id)
                if chat_member.status in ["member", "administrator", "creator"]:
                    msg = await app.bot.send_message(chat_id=chat_id, text=ANNOUNCEMENT_TEXT)
                    logger.info(f"Sent announcement to chat {chat_id}.")
                    
                    # Try pinning, but don't crash if it fails due to permissions
                    try:
                        await msg.pin()
                        logger.info(f"Pinned message in chat {chat_id}.")
                    except Exception as e:
                        logger.warning(f"Failed to pin message in chat {chat_id}: {e}")
                    
                    await asyncio.sleep(300)  # Pinned for 5 mins
                    
                    # Try unpinning and deleting, but don't crash if it fails
                    try:
                        await msg.unpin()
                        await msg.delete()
                        logger.info(f"Unpinned and deleted message in chat {chat_id}.")
                    except Exception as e:
                        logger.warning(f"Failed to unpin/delete message in chat {chat_id}: {e}")
                else:
                    logger.info(f"Bot no longer a member of chat {chat_id}. Removing from tracking.")
                    app.chat_ids.discard(chat_id)
                    save_chat_ids(app.chat_ids)
            except RetryAfter as e: # Handle flood control specifically
                logger.warning(f"Flood control for chat {chat_id}: Retry in {e.retry_after} seconds. Sleeping.")
                await asyncio.sleep(e.retry_after + 1) # Sleep a bit longer than required
            except Exception as e:
                logger.warning(f"Error in chat {chat_id}: {e}")
                # Consider removing chat_id if error indicates bot was kicked/banned
                if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower():
                    logger.info(f"Removing chat {chat_id} due to persistent error.")
                    app.chat_ids.discard(chat_id)
                    save_chat_ids(app.chat_ids)
            
            # Crucial: Add a delay *between* messages to different chats
            await asyncio.sleep(2) # Delay of 2 seconds between each chat's announcement

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

    app.add_handler(CallbackQueryHandler(show_support_info, pattern="^show_support_info$"))
    app.add_handler(CallbackQueryHandler(show_info, pattern="^show_info$"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^show_bot_commands$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^back_to_main_menu$"))
    
    app.add_handler(CallbackQueryHandler(lang_menu, pattern="^lang_menu$"))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^set_lang:"))

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=f"https://cooperative-blondelle-saidali-0379e40c.koyeb.app/{token}"
    )

if __name__ == "__main__":
    main()
