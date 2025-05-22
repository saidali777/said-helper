import os

# Telegram bot token (get this from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Optional: API_ID and API_HASH if you use Telethon or other APIs (not needed for python-telegram-bot)
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")

# Optional: Admin user IDs list (comma-separated in env, converted to int list)
ADMINS = [int(admin) for admin in os.getenv("ADMINS", "").split(",") if admin]

# Custom welcome message template (can use {user} placeholder)
WELCOME_MESSAGE = os.getenv(
    "WELCOME_MESSAGE",
    "Welcome, {user}! Please read the /rules before chatting."
)

# Group rules text
GROUP_RULES = os.getenv(
    "GROUP_RULES",
    "1. Be respectful\n2. No spam\n3. Follow Telegram TOS"
)
