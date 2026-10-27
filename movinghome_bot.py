from telegram import Update
from telegram.ext import Application, CommandHandler

from commands import handlers
from config import load_settings
from logger.logger import getMyLogger

logger = getMyLogger(__name__)


def build_app(settings) -> Application:
    app = Application.builder().token(settings.token).build()
    app.bot_data["settings"] = settings
    app.add_handler(CommandHandler("start", handlers.start_command))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("criteria", handlers.criteria_command))
    app.add_handler(CommandHandler(["find", "quick_search"], handlers.find_command))
    app.add_handler(CommandHandler("start_alerts", handlers.start_alerts_command))
    app.add_handler(CommandHandler("stop_alerts", handlers.stop_alerts_command))
    app.add_error_handler(handlers.error_handler)
    return app


def main():
    settings = load_settings()
    if not settings.allowed_chat_ids:
        logger.warning("ALLOWED_CHAT_IDS is empty: anyone who finds the bot can use it.")
    if not settings.scrape_enabled:
        logger.warning("RIGHTMOVE_SCRAPE_ENABLED is off: /find will not fetch listings.")
    logger.info("Bot starting")
    build_app(settings).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
