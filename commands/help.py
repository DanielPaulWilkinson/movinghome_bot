#!/usr/bin/env python3
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram import Update
from logger.logger import getMyLogger

from services.telegram_message_service import help
from html import escape

logger = getMyLogger(__name__)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat.id
    logger.info(
        "%s asked for help %d (%s)"
        % (
            escape(message.from_user.first_name),
            chat_id,
            escape(message.text),
        )
    )

    await update.message.reply_text(text=help(message), parse_mode=ParseMode.HTML)
