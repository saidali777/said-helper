import logging
import os
import asyncio
import motor.motor_asyncio
from telegram import (
    Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import RetryAfter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ANNOUNCEMENT_TEXT = "📢 This is a recurring announcement."

# --- MongoDB Setup ---
mongo_client = None
chat_collection = None

async def init_mongo_client():
    global mongo_client, chat_collection
    mongodb_url = os.getenv("MONGODB_URL")
    if not mongodb_url:
        raise RuntimeError("MONGODB_URL not set.")
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
    db = mongo_client.get_database("telegram_bot_db")
    chat_collection = db.get_collection("chat_ids")
    await chat_collection.create_index("chat_id", unique=True)

async def get_all_chat_ids_from_mongo():
    chat_ids = set()
    async for doc in chat_collection.find({}, {"chat_id": 1}):
        if 'chat_id' in doc:
            chat_ids.add(doc['chat_id'])
    return chat_ids

async def add_chat_id_to_mongo(chat_id: int):
    await chat_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id}},
        upsert=True
    )

async def remove_chat_id_from_mongo(chat_id: int):
    await chat_collection.delete_one({"chat_id": chat_id})

# --- Bot Handlers ---

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
        "@mygroupmanagement_bot helps manage your groups easily and safely!\n\n"
        "👉🏻 Add me to a supergroup and promote me as admin.\n\n"
        "❓ /help for commands\n"
        "📃 <a href='https://www.grouphelp.top/privacy'>Privacy policy</a>"
    )

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                text=msg, reply_markup=reply_markup,
                disable_web_page_preview=True, parse_mode="HTML"
            )
        except:
            await update.callback_query.message.reply_text(msg, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/help - Show this message\n"
        "/rules - Show group rules\n"
        "/kick - Kick a user (reply only)\n"
        "/ban - Ban a user (reply only)\n"
        "/mute - Mute a user (reply only)\n"
        "/promote - Promote user (reply only)\n"
        "/demote - Demote user (reply only)"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(help_text)
    else:
        await update.message.reply_text(help_text)

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Group Rules:\n1. Be respectful\n2. No spam\n3. Follow Telegram TOS"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

async def show_support_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")]]
    await update.callback_query.edit_message_text(
        "⚠️ For bans/mutes, contact group admins directly.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    keyboard = [
        [InlineKeyboardButton("Bot Support", url="https://t.me/colonel_support")],
        [InlineKeyboardButton("Bot commands", callback_data="show_bot_commands")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")]
    ]
    msg = (
        "<b>Features:</b>\n"
        "• Ban/mute/kick\n"
        "• Admin controls\n"
        "• Welcome messages\n"
        "• Periodic announcements\n"
    )
    await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        if new_user.id == context.bot.id:
            await add_chat_id_to_mongo(update.effective_chat.id)
            await update.message.reply_text("Thanks for adding me! Please promote me to admin.")
        else:
            await update.message.reply_text(f"Welcome {new_user.full_name}! Please read /rules.")

async def require_reply(update, context, action_name):
    if not update.message.reply_to_message:
        await update.message.reply_text(f"Reply to a user's message to use /{action_name}.")
        return None
    if not await is_admin(update, update.message.from_user.id):
        await update.message.reply_text("Only admins can use this command.")
        return None
    return update.message.reply_to_message.from_user

async def is_admin(update: Update, user_id: int) -> bool:
    try:
        admins = await update.effective_chat.get_administrators()
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False

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
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions=ChatPermissions(can_send_messages=False))
        await update.message.reply_text(f"Muted {user.full_name}")

async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "promote")
    if user:
        await context.bot.promote_chat_member(update.effective_chat.id, user.id,
            can_change_info=True, can_delete_messages=True, can_invite_users=True,
            can_restrict_members=True, can_pin_messages=True, can_promote_members=False)
        await update.message.reply_text(f"Promoted {user.full_name} to admin.")

async def demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_reply(update, context, "demote")
    if user:
        await context.bot.promote_chat_member(update.effective_chat.id, user.id,
            can_change_info=False, can_delete_messages=False, can_invite_users=False,
            can_restrict_members=False, can_pin_messages=False, can_promote_members=False)
        await update.message.reply_text(f"Demoted {user.full_name}.")

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_chat_id_to_mongo(update.effective_chat.id)

async def lang_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    keyboard = [[InlineKeyboardButton("🇬🇧 English", callback_data="set_lang:en")]]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")])
    await update.callback_query.edit_message_text("Choose your language:", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    lang = update.callback_query.data.split(":")[1]
    await update.callback_query.edit_message_text(f"Language set to {lang.upper()}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_main_menu")]]))

# === Periodic Announcements ===

async def periodic_announcement(app):
    first_run = True
    while True:
        if not first_run:
            await asyncio.sleep(3600)
        first_run = False
        chat_ids = list(await get_all_chat_ids_from_mongo())
        for chat_id in chat_ids:
            try:
                member = await app.bot.get_chat_member(chat_id, app.bot.id)
                if member.status in ["member", "administrator", "creator"]:
                    msg = await app.bot.send_message(chat_id, ANNOUNCEMENT_TEXT)
                    try:
                        await msg.pin()
                    except: pass
                    await asyncio.sleep(300)
                    try:
                        await msg.unpin()
                        await msg.delete()
                    except: pass
                else:
                    await remove_chat_id_from_mongo(chat_id)
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except:
                await remove_chat_id_from_mongo(chat_id)
            await asyncio.sleep(2)

# === Startup/Shutdown ===

async def on_startup(app):
    await init_mongo_client()
    app.create_task(periodic_announcement(app))

async def on_shutdown(app):
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set.")
    port = int(os.environ.get("PORT", 8000))
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("WEBHOOK_URL not set.")
    
    app = ApplicationBuilder().token(token).post_init(on_startup).post_shutdown(on_shutdown).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
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
        webhook_url=f"{webhook_url}/{token}"
    )

if __name__ == "__main__":
    main()
