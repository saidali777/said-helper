def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment variables.")
    
    app = ApplicationBuilder().token(token).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(CommandHandler("demote", demote))

    # Run webhook instead of polling
    app.run_webhook(
        listen="0.0.0.0",      # Listen on all interfaces
        port=8443,             # Your chosen port (make sure it's open)
        url_path=token,        # Secret path to receive webhook (using your token)
        webhook_url=f"https://yourdomain.com/{token}"  # Your HTTPS URL + path
    )

