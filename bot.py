import logging
import os
import json
import asyncio
import motor.motor_asyncio
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
from telegram.error import RetryAfter, Forbidden
import sys # Import sys module for exiting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANNOUNCEMENT_TEXT = "📢 This is a recurring announcement."

# --- MongoDB Client and Collection ---
mongo_client = None
chat_collection = None

async def init_mongo_client():
    global mongo_client, chat_collection
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise RuntimeError("MONGODB_URL environment variable not set.")
    
    logger.info("Attempting to connect to MongoDB...")
    try:
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        db = mongo_client.get_database("telegram_bot_db")
        chat_collection = db.get_collection("chat_ids")
        
        logger.info("MongoDB client and collection initialized.")
        await chat_collection.create_index("chat_id", unique=True)
        logger.info("MongoDB index on 'chat_id' created/ensured.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB or initialize collection: {e}")
        raise

# --- MongoDB Interaction Functions ---

async def get_all_chat_ids_from_mongo():
    chat_ids = set()
    try:
        async for doc in chat_collection.find({}, {"chat_id": 1}):
            if 'chat_id' in doc:
                chat_ids.add(doc['chat_id'])
        logger.debug(f"Fetched {len(chat_ids)} chat IDs from MongoDB.")
    except Exception as e:
        logger.error(f"Failed to fetch chat IDs from MongoDB: {e}")
    return chat_ids

async def add_chat_id_to_mongo(chat_id: int, chat_title: str = None):
    """Adds a chat ID and title to the MongoDB collection if it doesn't already exist or updates the title."""
    try:
        result = await chat_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"chat_id": chat_id, "chat_title": chat_title}}, # Store the chat_id and title
            upsert=True
        )
        if result.upserted_id:
            logger.info(f"Chat ID {chat_id} ('{chat_title}') added to MongoDB.")
        elif result.modified_count > 0:
            logger.info(f"Chat ID {chat_id} ('{chat_title}') title updated in MongoDB.")
        else:
            logger.debug(f"Chat ID {chat_id} already exists in MongoDB, no update needed.")
    except Exception as e:
        logger.error(f"Failed to add/update chat ID {chat_id} ('{chat_title}') to MongoDB: {e}")

async def remove_chat_id_from_mongo(chat_id: int):
    """Removes a chat ID from the MongoDB collection."""
    try:
        result = await chat_collection.delete_one({"chat_id": chat_id})
        if result.deleted_count > 0:
            logger.info(f"Chat ID {chat_id} removed from MongoDB.")
        else:
            logger.debug(f"Chat ID {chat_id} not found in MongoDB for deletion.")
    except Exception as e:
        logger.error(f"Failed to remove chat ID {chat_id} from MongoDB: {e}")

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
            disable_web_page_preview=True,
            parse_mode="HTML"
        )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        if new_user.id == context.bot.id:
            chat_id = update.effective_chat.id
            chat_title = update.effective_chat.title
            await add_chat_id_to_mongo(chat_id, chat_title)
            await update.message.reply_text(f"Hello everyone! Thanks for adding me to **{update.effective_chat.title}**. I'm here to help manage this group. Please make me an admin so I can function properly!", parse_mode="Markdown")
        else:
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
        "/settings - Manage group settings (private chat only)\n"
        "/reload - Restart the bot (admin only in groups)\n"
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
        # If update.effective_chat is None (e.g., in a private chat context where this function is called),
        # then we can't get administrators.
        if update.effective_chat is None:
            return False
        
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
    return update.message.reply_to_message.from_user

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "kick")
    if user:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
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
        "ko": "한국어", "fa": "فارسی", "te": "తెలుగు", "gu": "ગુજરાતી",
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

# --- /settings command and related functions ---

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if update.effective_chat.type != "private":
        # If /settings is sent in a group, offer to open in private chat
        keyboard = [[InlineKeyboardButton("Open in pvt", url=f"https://t.me/{context.bot.username}?start=settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Group Settings\n\nPress 'Open in pvt' to manage settings for groups you administer.", reply_markup=reply_markup)
        return

    # In private chat, list groups where the bot is an admin
    settings_message = (
        "<b>Group Settings</b>\n"
        "👉🏻 Select the group whose settings you want to change.\n\n"
        "If a group in which you are an administrator doesn't appear here:\n"
        " • Send /reload in the group and try again\n"
        " • Send /settings in the group and then press \"Open in pvt\""
    )

    keyboard = []
    # Fetch all chat IDs and titles from the database
    all_tracked_chats = await chat_collection.find().to_list(length=None)

    for chat_doc in all_tracked_chats:
        chat_id = chat_doc['chat_id']
        chat_title = chat_doc.get('chat_title', f"Unknown Chat ({chat_id})")

        try:
            # Check if the bot is still a member of the chat
            bot_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=context.bot.id)
            if bot_member.status in ["member", "administrator", "creator"]:
                # Check if the user is an admin in that group
                # When checking for admin in the settings command (private chat),
                # we don't have effective_chat directly from the update.
                # So we must use context.bot.get_chat_administrators(chat_id)
                chat_admins = await context.bot.get_chat_administrators(chat_id)
                if any(admin.user.id == user_id for admin in chat_admins):
                    keyboard.append([InlineKeyboardButton(chat_title, callback_data=f"group_settings:{chat_id}")])
            else:
                logger.info(f"Bot is no longer a member of chat {chat_id} ('{chat_title}'). Removing from MongoDB.")
                await remove_chat_id_from_mongo(chat_id)
        except Forbidden:
            logger.info(f"Bot was kicked/blocked from chat {chat_id} ('{chat_title}'). Removing from MongoDB.")
            await remove_chat_id_from_mongo(chat_id)
        except Exception as e:
            logger.warning(f"Could not retrieve chat info for {chat_id} ('{chat_title}'): {e}")
            # Optionally, remove chat if it consistently fails
            # await remove_chat_id_from_mongo(chat_id) # Consider removing if errors persist

    if not keyboard:
        settings_message += "\n\n<i>No groups found where you are an administrator and the bot is present.</i>"

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                text=settings_message,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                text=settings_message,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"Error sending settings message: {e}")
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text=settings_message,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                text=settings_message,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=True
            )


async def show_group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id_str = query.data.split(":")[1]
    chat_id = int(chat_id_str)

    # Fetch chat title from the database
    chat_doc = await chat_collection.find_one({"chat_id": chat_id})
    chat_title = chat_doc.get('chat_title', f"Unknown Chat ({chat_id})") if chat_doc else f"Unknown Chat ({chat_id})"

    # Construct the buttons for the selected group's settings
    keyboard = [
        [InlineKeyboardButton(f"Group: {chat_title}", callback_data="do_nothing")], # Current group name button
        [InlineKeyboardButton("Settings menu sent in private chat", callback_data="do_nothing")], # Placeholder
        [InlineKeyboardButton("Admin list updated", callback_data="do_nothing")], # Placeholder
        [InlineKeyboardButton("Go to the chat", url=f"https://t.me/c/{str(chat_id).replace('-100', '')}/1")], # Link to chat (requires public link or message ID for deep link)
        [InlineKeyboardButton("⬅️ Back to Group List", callback_data="back_to_settings_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    settings_text = f"⚙️ Group Settings for <b>{chat_title}</b>"
    
    try:
        await query.edit_message_text(
            text=settings_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error editing message for group settings: {e}")
        await query.message.reply_text(
            text=settings_text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

# --- New /reload command ---
async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if update.effective_chat.type in ["group", "supergroup"]:
        # Check if the user is an admin in the group
        if await is_admin(update, user_id):
            await update.message.reply_text("🔄 Bot is restarting... Please wait a moment.")
            logger.info(f"Bot restart requested by admin {user_id} in chat {chat_id}. Exiting for restart.")
            sys.exit(0) # Exit with a success code
        else:
            await update.message.reply_text("🚫 Only administrators can use the /reload command in groups.")
    else:
        await update.message.reply_text("This command can only be used in a group chat where I am an administrator.")


# === Chat tracking ===
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ["group", "supergroup"]:
        chat_id = update.effective_chat.id
        chat_title = update.effective_chat.title
        await add_chat_id_to_mongo(chat_id, chat_title)

# === Periodic Announcement ===

async def periodic_announcement(app):
    while True:
        chats_to_announce = await chat_collection.find().to_list(length=None)
        
        if not chats_to_announce:
            logger.info("No chats to announce to. Sleeping for 10 seconds before checking again.")
            await asyncio.sleep(10)
            continue

        for chat_doc in chats_to_announce:
            chat_id = chat_doc['chat_id']
            chat_title = chat_doc.get('chat_title', f"Unknown Chat ({chat_id})")
            try:
                chat_member = await app.bot.get_chat_member(chat_id=chat_id, user_id=app.bot.id)
                if chat_member.status in ["member", "administrator", "creator"]:
                    msg = await app.bot.send_message(chat_id=chat_id, text=ANNOUNCEMENT_TEXT)
                    logger.info(f"Sent announcement to chat {chat_id} ('{chat_title}').")
                    
                    try:
                        await msg.pin()
                        logger.info(f"Pinned message in chat {chat_id} ('{chat_title}').")
                    except Exception as e:
                        logger.warning(f"Failed to pin message in chat {chat_id} ('{chat_title}'): {e}")
                    
                    await asyncio.sleep(300) # Wait for 5 minutes
                    
                    try:
                        await msg.unpin()
                        await msg.delete()
                        logger.info(f"Unpinned and deleted message in chat {chat_id} ('{chat_title}').")
                    except Exception as e:
                        logger.warning(f"Failed to unpin/delete message in chat {chat_id} ('{chat_title}'): {e}")
                else:
                    logger.info(f"Bot no longer a member of chat {chat_id} ('{chat_title}'). Removing from MongoDB tracking.")
                    await remove_chat_id_from_mongo(chat_id)
            except RetryAfter as e:
                logger.warning(f"Flood control for chat {chat_id} ('{chat_title}'): Retry in {e.retry_after} seconds. Sleeping.")
                await asyncio.sleep(e.retry_after + 1)
            except Forbidden:
                logger.info(f"Bot was kicked/blocked from chat {chat_id} ('{chat_title}'). Removing from MongoDB tracking.")
                await remove_chat_id_from_mongo(chat_id)
            except Exception as e:
                logger.warning(f"Error in chat {chat_id} ('{chat_title}'): {e}")
                if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower() or "not a member of the chat" in str(e).lower():
                    logger.info(f"Removing chat {chat_id} ('{chat_title}') due to persistent error (chat not found/blocked/not member).")
                    await remove_chat_id_from_mongo(chat_id)
            
            await asyncio.sleep(0.5)
            
        logger.info("Finished one cycle of announcements. Sleeping for 30 seconds.")
        await asyncio.sleep(30)

# === On startup / On shutdown ===

async def on_startup(app):
    await init_mongo_client()
    app.create_task(periodic_announcement(app))

async def on_shutdown(app):
    if mongo_client:
        mongo_client.close()
    logger.info("MongoDB client closed.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set")

    port = int(os.environ.get("PORT", 8000))
    
    app = ApplicationBuilder().token(token)\
        .post_init(on_startup)\
        .post_shutdown(on_shutdown)\
        .connect_timeout(10)\
        .read_timeout(20)\
        .write_timeout(20)\
        .build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))    
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("reload", reload_command))
    
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, track_chats))    

    app.add_handler(CallbackQueryHandler(show_support_info, pattern="^show_support_info$"))
    app.add_handler(CallbackQueryHandler(show_info, pattern="^show_info$"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^show_bot_commands$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^back_to_main_menu$"))
    
    app.add_handler(CallbackQueryHandler(lang_menu, pattern="^lang_menu$"))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^set_lang:"))
    
    app.add_handler(CallbackQueryHandler(show_group_settings, pattern="^group_settings:"))
    app.add_handler(CallbackQueryHandler(settings_command, pattern="^back_to_settings_list$"))

    webhook_url_from_env = os.getenv("WEBHOOK_URL")    
    logger.info(f"WEBHOOK_URL read from environment: {webhook_url_from_env}")    
    
    if not webhook_url_from_env:
        raise RuntimeError("WEBHOOK_URL environment variable not set or invalid.")

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=token,
        webhook_url=webhook_url_from_env    
    )

if __name__ == "__main__":
    main()
