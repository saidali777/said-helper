import logging
import os
import asyncio
from fastapi import FastAPI, Request, Response
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import (
    Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import RetryAfter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

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
    mongo_client = AsyncIOMotorClient(mongodb_url)
    db = mongo_client.get_database("telegram_bot_db")
    chat_collection = db.get_collection("chat_ids")
    await chat_collection.create_index("chat_id", unique=True)
    logger.info("MongoDB initialized.")

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

# --- Bot Handlers (same as your code) ---

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


# === Periodic Announcements using APScheduler ===

async def periodic_announcement(app: Application):
    chat_ids = list(await get_all_chat_ids_from_mongo())
    for chat_id in chat_ids:
        try:
            member = await app.bot.get_chat_member(chat_id, app.bot.id)
            if member.status in ["member", "administrator", "creator"]:
                msg = await app.bot.send_message(chat_id, ANNOUNCEMENT_TEXT)
                try:
                    await msg.pin()
                except Exception:
                    pass
                await asyncio.sleep(300)  # Wait 5 minutes before unpinning
                try:
                    await msg.unpin()
                    await msg.delete()
                except Exception:
                    pass
            else:
                await remove_chat_id_from_mongo(chat_id)
        except RetryAfter as e:
            logger.warning(f"Rate limit hit, sleeping {e.retry_after} seconds.")
            await asyncio.sleep(e.retry_after + 1)
        except Exception as e:
            logger.error(f"Error sending announcement to {chat_id}: {e}")
            await remove_chat_id_from_mongo(chat_id)

# --- FastAPI app and Telegram webhook setup ---

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required.")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL environment variable is required.")

application = ApplicationBuilder().token(BOT_TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("rules", rules))
application.add_handler(CommandHandler("kick", kick))
application.add_handler(CommandHandler("ban", ban))
application.add_handler(CommandHandler("mute", mute))
application.add_handler(CommandHandler("promote", promote))
application.add_handler(CommandHandler("demote", demote))
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, track_chats))

application.add_handler(CallbackQueryHandler(show_support_info, pattern="^show_support_info$"))
application.add_handler(CallbackQueryHandler(show_info, pattern="^show_info$"))
application.add_handler(CallbackQueryHandler(help_command, pattern="^show_bot_commands$"))
application.add_handler(CallbackQueryHandler(start, pattern="^back_to_main_menu$"))
application.add_handler(CallbackQueryHandler(lang_menu, pattern="^lang_menu$"))
application.add_handler(CallbackQueryHandler(set_language, pattern="^set_lang:"))


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up...")
    await init_mongo_client()
    # Set webhook
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    logger.info("Webhook set.")
    # Start APScheduler for announcements
    scheduler = AsyncIOScheduler()
    scheduler.add_job(periodic_announcement, IntervalTrigger(hours=1), args=[application])
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed.")
    # Remove webhook
    try:
        await application.bot.delete_webhook()
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
    # Shutdown scheduler
    scheduler = app.state.scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")

@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    try:
        json_data = await request.json()
    except Exception:
        return Response(status_code=400)
    update = Update.de_json(json_data, application.bot)
    await application.update_queue.put(update)
    return Response(status_code=200)

# Optional root endpoint for health check
@app.get("/")
async def root():
    return {"status": "ok"}

# --- Main entrypoint ---

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port)

