from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from logger.logger import getMyLogger
from commands.start import start_command
from commands.help import help_command
from commands.start_alerts import start_alerts_command
from commands.stop_alerts import stop_alerts_command
from commands.find import find_properties_command
from services.json_service import get_application_config

logger = getMyLogger(__name__)


def handle_response(text: str) -> str:
    return text


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if message_type == "group":
        if text.lower().count(get_application_config()["name"]):
            new_text: str = text.replace(get_application_config()["name"], "").strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(new_text)

    print("Bot:", response)
    await update.message.reply_text(response)


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    app = Application.builder().token(get_application_config()["token"]).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["quick_search", "find"], find_properties_command))
    app.add_handler(CommandHandler("start_alerts", start_alerts_command))
    app.add_handler(CommandHandler("stop_alerts", stop_alerts_command))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_error_handler(error)

    logger.info(f"Application Started Polling...")
    app.run_polling(poll_interval=3, allowed_updates=Update.ALL_TYPES)
