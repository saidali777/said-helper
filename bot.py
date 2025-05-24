import logging
import os
import json
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
from telegram.error import RetryAfter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANNOUNCEMENT_TEXT = "📢 This is a recurring announcement."
# DATA_FILE = "chat_ids.json" # No longer needed

# --- Database Connection Pool ---
# Global variable to hold the connection pool
db_pool = None

async def init_db_pool():
    global db_pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set.")

    logger.info("Attempting to connect to PostgreSQL...")
    db_pool = await asyncpg.create_pool(database_url)
    logger.info("PostgreSQL connection pool created.")

    # Create table if it doesn't exist
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                chat_id BIGINT PRIMARY KEY
            );
        ''')
    logger.info("Chats table checked/created.")


# --- Modified Chat ID Management Functions ---

# No longer load all chat IDs at once; fetch as needed or manage on insert/delete
# def load_chat_ids(): # This function is removed
#    ...

# No longer save all chat IDs; individual operations will handle persistence
# def save_chat_ids(chat_ids): # This function is removed
#    ...

async def get_all_chat_ids_from_db():
    """Fetches all chat IDs from the database."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT chat_id FROM chats;")
        return {row['chat_id'] for row in rows}

async def add_chat_id_to_db(chat_id: int):
    """Adds a chat ID to the database if it doesn't already exist."""
    async with db_pool.acquire() as conn:
        try:
            await conn.execute("INSERT INTO chats (chat_id) VALUES ($1) ON CONFLICT (chat_id) DO NOTHING;", chat_id)
            logger.info(f"Chat ID {chat_id} added/ensured in DB.")
        except Exception as e:
            logger.error(f"Failed to add chat ID {chat_id} to DB: {e}")

async def remove_chat_id_from_db(chat_id: int):
    """Removes a chat ID from the database."""
    async with db_pool.acquire() as conn:
        try:
            await conn.execute("DELETE FROM chats WHERE chat_id = $1;", chat_id)
            logger.info(f"Chat ID {chat_id} removed from DB.")
        except Exception as e:
            logger.error(f"Failed to remove chat ID {chat_id} from DB: {e}")

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
            # Bot itself was added to the group
            chat_id = update.effective_chat.id
            await add_chat_id_to_db(chat_id) # Add group to DB when bot joins
            await update.message.reply_text(f"Hello everyone! Thanks for adding me to {update.effective_chat.title}. I'm here to help manage this group. Please make me an admin so I can function properly!")
        else:
            # A regular user joined
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
# This handler now directly interacts with the database
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # When any message comes from a group, ensure it's tracked
    await add_chat_id_to_db(chat_id)


# === Periodic Announcement ===

async def periodic_announcement(app):
    first_run = True
    while True:
        if not first_run:
            await asyncio.sleep(60 * 60) # Wait for 1 hour after the first run
        first_run = False

        # Fetch chats from the database directly
        chats_to_announce = list(await get_all_chat_ids_from_db())

        if not chats_to_announce:
            logger.info("No chats to announce to. Sleeping for 60 seconds.")
            await asyncio.sleep(60)
            continue

        for chat_id in chats_to_announce:
            try:
                chat_member = await app.bot.get_chat_member(chat_id=chat_id, user_id=app.bot.id)
                if chat_member.status in ["member", "administrator", "creator"]:
                    msg = await app.bot.send_message(chat_id=chat_id, text=ANNOUNCEMENT_TEXT)
                    logger.info(f"Sent announcement to chat {chat_id}.")

                    try:
                        await msg.pin()
                        logger.info(f"Pinned message in chat {chat_id}.")
                    except Exception as e:
                        logger.warning(f"Failed to pin message in chat {chat_id}: {e}")

                    await asyncio.sleep(300)

                    try:
                        await msg.unpin()
                        await msg.delete()
                        logger.info(f"Unpinned and deleted message in chat {chat_id}.")
                    except Exception as e:
                        logger.warning(f"Failed to unpin/delete message in chat {chat_id}: {e}")
                else:
                    logger.info(f"Bot no longer a member of chat {chat_id}. Removing from DB tracking.")
                    await remove_chat_id_from_db(chat_id) # Remove from DB
            except RetryAfter as e:
                logger.warning(f"Flood control for chat {chat_id}: Retry in {e.retry_after} seconds. Sleeping.")
                await asyncio.sleep(e.retry_after + 1)
            except Exception as e:
                logger.warning(f"Error in chat {chat_id}: {e}")
                if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower():
                    logger.info(f"Removing chat {chat_id} due to persistent error (chat not found/blocked).")
                    await remove_chat_id_from_db(chat_id) # Remove from DB

            await asyncio.sleep(2)

# === On startup / On shutdown ===

async def on_startup(app):
    await init_db_pool() # Initialize database connection pool
    # app.chat_ids is no longer needed as a global set
    app.create_task(periodic_announcement(app))

async def on_shutdown(app):
    if db_pool:
        await db_pool.close()
        logger.info("PostgreSQL connection pool closed.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set")

    port = int(os.environ.get("PORT", 8000))
    app = ApplicationBuilder().token(token).post_init(on_startup).post_shutdown(on_shutdown).build() # Add post_shutdown

    app.add_handler(CommandHandler("start", start))
    # Updated welcome handler logic to add bot-joined groups
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome)) 
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))

    # The track_chats handler will now just ensure the chat is in the DB
    # It's better to add the group ID when the bot *joins* a group,
    # rather than on every message, to avoid unnecessary DB writes.
    # However, for robustness, you could keep it or make it smarter.
    # For this setup, I've integrated group addition into the 'welcome' handler
    # when the bot itself joins, and removed the generic filters.ChatType.GROUPS handler
    # You might want to re-evaluate how groups get into the DB if you want *every* group
    # the bot interacts with to be tracked.
    # app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, track_chats)) # Removed/Replaced

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
        webhook_url=os.getenv("https://cooperative-blondelle-saidali-0379e40c.koyeb.app/") # Use an environment variable for webhook URL
    )

if __name__ == "__main__":
    main()
