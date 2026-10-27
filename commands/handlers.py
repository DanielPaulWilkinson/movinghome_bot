"""Telegram command handlers. Kept thin: the real logic lives in services/."""
import asyncio
import functools

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import Settings, load_criteria
from logger.logger import getMyLogger
from services import telegram_message_service as msg
from services.search_service import run_search
from services.seen_store import SeenStore

logger = getMyLogger(__name__)

# One search at a time, so /find and a scheduled check can't overlap.
_search_lock = asyncio.Lock()


def _settings(context) -> Settings:
    return context.application.bot_data["settings"]


def restricted(handler):
    """Only answer chats listed in ALLOWED_CHAT_IDS (if it is set)."""

    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        allowed = _settings(context).allowed_chat_ids
        chat_id = update.effective_chat.id
        if allowed and chat_id not in allowed:
            logger.warning("Ignoring command from unlisted chat %s", chat_id)
            return
        return await handler(update, context)

    return wrapper


async def _search_and_send(context, chat_id: int, announce_empty: bool):
    settings = _settings(context)
    if _search_lock.locked():
        if announce_empty:
            await context.bot.send_message(chat_id, "A search is already running, hang on.")
        return
    async with _search_lock:
        criteria = load_criteria(settings.criteria_file)
        store = SeenStore(settings.seen_file)
        # Network work is blocking, so run it off the event loop.
        result = await asyncio.to_thread(run_search, settings, criteria, store)

    for p, status, previous in result.alerts:
        await context.bot.send_message(
            chat_id, msg.property_message(p, criteria, status, previous), parse_mode=ParseMode.HTML
        )
    if result.errors and announce_empty:
        await context.bot.send_message(chat_id, "⚠️ " + "\n".join(result.errors))
    if not result.alerts and announce_empty:
        await context.bot.send_message(
            chat_id, f"Nothing new since last time ({result.scanned} listings checked)."
        )


@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    criteria = load_criteria(_settings(context).criteria_file)
    logger.info("/start from chat %s", update.effective_chat.id)
    await update.message.reply_text(
        msg.start_message(update.effective_user.first_name, criteria), parse_mode=ParseMode.HTML
    )


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        msg.help_message(_settings(context).alert_interval_minutes), parse_mode=ParseMode.HTML
    )


@restricted
async def criteria_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    criteria = load_criteria(_settings(context).criteria_file)
    await update.message.reply_text(msg.criteria_message(criteria), parse_mode=ParseMode.HTML)


@restricted
async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Searching...")
    await _search_and_send(context, update.effective_chat.id, announce_empty=True)


async def _alert_job(context: ContextTypes.DEFAULT_TYPE):
    # Scheduled runs stay quiet unless there's something new.
    await _search_and_send(context, context.job.chat_id, announce_empty=False)


@restricted
async def start_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()  # avoid stacking duplicate jobs
    minutes = _settings(context).alert_interval_minutes
    context.job_queue.run_repeating(
        _alert_job, interval=minutes * 60, first=5, chat_id=chat_id, name=str(chat_id)
    )
    await update.message.reply_text(f"⏰ I'll check every {minutes} minutes. /stop_alerts to stop.")


@restricted
async def stop_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jobs = context.job_queue.get_jobs_by_name(str(update.effective_chat.id))
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("Stopped the regular checks." if jobs else "Alerts weren't running.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error", exc_info=context.error)
