from telegram import Update
from telegram.ext import  ContextTypes
from commands import find
async def start_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    context.job_queue.run_repeating(find.find_callback, (60*30), chat_id=chat_id, name=str(chat_id))

