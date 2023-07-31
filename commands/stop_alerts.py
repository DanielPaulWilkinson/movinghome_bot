from telegram import Update
from telegram.ext import ContextTypes

async def stop_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id, text="Stopping automatic messages!")
    job = context.job_queue.get_jobs_by_name(str(chat_id))
    job[0].schedule_removal()
