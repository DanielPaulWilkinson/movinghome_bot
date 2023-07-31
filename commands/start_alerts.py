from telegram import Update
from telegram.ext import ContextTypes
from commands import find


async def start_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey there, we will update you every 30 minutes!")

    context.job_queue.run_repeating(
        find.find_callback, (60 * 30), chat_id=update.message.chat_id, name=str(update.message.chat_id)
    )
