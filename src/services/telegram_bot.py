"""Telegram bot — accepts text/voice, runs pipeline, sends status updates, then final response."""

import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from src.config import TELEGRAM_BOT_TOKEN
from src.models.database import Database, JobState
from src.services.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# Status indicators shown during processing
_STATUS_STEPS = {
    "Transcribing voice message...": (1, 5),
    "Analyzing business process...": (2, 5),
    "Rendering diagrams...": (3, 5),
    "Generating HTML report...": (4, 5),
    "Preparing final message...": (5, 5),
}

_STATUS_STEPS_TEXT = {
    "Analyzing business process...": (1, 4),
    "Rendering diagrams...": (2, 4),
    "Generating HTML report...": (3, 4),
    "Preparing final message...": (4, 4),
}


def _build_status_text(status: str, is_voice: bool = False) -> str:
    """Build a formatted status message with progress bar."""
    steps = _STATUS_STEPS if is_voice else _STATUS_STEPS_TEXT
    current, total = steps.get(status, (0, 4))
    filled = current
    empty = total - current
    bar = ">" * filled + "." * empty
    return f"[{bar}] {status}"


def _format_telegram_response(analysis) -> str:
    """Format the final Telegram response with hyperlink."""
    ts = analysis.telegram_summary
    url = analysis.html_url or ""

    body = (
        f"Process: {ts.process_title}\n\n"
        f"Description: {ts.description}\n\n"
        f"Automated by Agent: {ts.automated_by_agent}\n\n"
        f"Human Responsibilities: {ts.human_responsibilities}"
    )

    # Truncate body to 1000 chars if needed
    if len(body) > 1000:
        body = body[:997] + "..."

    if url:
        return f"{body}\n\n<a href=\"{url}\">Open Full Report</a>"
    return body


class TelegramBot:
    def __init__(self, db: Database):
        self.db = db
        self.orchestrator = Orchestrator(db)

    async def start_command(self, update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "Welcome to the Process-to-Agent Analyzer!\n\n"
            "Send me a text description of any business process, "
            "or send a voice message describing it.\n\n"
            "I will analyze it and return a concise summary plus "
            "a detailed HTML report with AS-IS, TO-BE, PRD, and Architecture."
        )

    async def help_command(self, update: Update,
                           context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await update.message.reply_text(
            "How to use this bot:\n\n"
            "1. Send a text message describing a business process\n"
            "2. Or send a voice message describing it\n\n"
            "The bot will analyze the process and return:\n"
            "- Process title and summary\n"
            "- What an AI agent can automate\n"
            "- What remains human responsibility\n"
            "- Link to a full HTML report"
        )

    async def handle_text(self, update: Update,
                          context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        text = update.message.text
        if not text or not text.strip():
            await update.message.reply_text(
                "Please send a non-empty process description."
            )
            return

        chat_id = update.effective_chat.id
        message_id = update.message.message_id

        logger.info("Received text input from chat %d: %d chars",
                     chat_id, len(text))

        # Send initial status message
        status_msg = await update.message.reply_text(
            _build_status_text("Analyzing business process...", is_voice=False)
        )

        async def on_status(status_text: str):
            try:
                await status_msg.edit_text(
                    _build_status_text(status_text, is_voice=False)
                )
            except Exception:
                logger.debug("Could not update status message")

        try:
            job_id, analysis = await self.orchestrator.process_text(
                chat_id, message_id, text, on_status=on_status
            )

            # Delete the status message and send the final response
            try:
                await status_msg.delete()
            except Exception:
                logger.debug("Could not delete status message")

            response = _format_telegram_response(analysis)
            await update.message.reply_text(
                response, parse_mode="HTML",
                disable_web_page_preview=False
            )
            await self.db.update_state(job_id, JobState.COMPLETED)
            logger.info("Job %s: completed and sent to chat %d", job_id, chat_id)

        except Exception:
            logger.exception("Failed to process text for chat %d", chat_id)
            try:
                await status_msg.delete()
            except Exception:
                pass
            await update.message.reply_text(
                "Sorry, an error occurred while analyzing your process. "
                "Please try again later."
            )

    async def handle_voice(self, update: Update,
                           context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming voice messages."""
        voice = update.message.voice
        if not voice:
            return

        chat_id = update.effective_chat.id
        message_id = update.message.message_id

        logger.info("Received voice input from chat %d: %d seconds",
                     chat_id, voice.duration)

        # Send initial status message
        status_msg = await update.message.reply_text(
            _build_status_text("Transcribing voice message...", is_voice=True)
        )

        async def on_status(status_text: str):
            try:
                await status_msg.edit_text(
                    _build_status_text(status_text, is_voice=True)
                )
            except Exception:
                logger.debug("Could not update status message")

        try:
            # Download voice file
            voice_file = await context.bot.get_file(voice.file_id)
            tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
            tmp_path = Path(tmp.name)
            tmp.close()
            await voice_file.download_to_drive(str(tmp_path))

            job_id, analysis = await self.orchestrator.process_voice(
                chat_id, message_id, tmp_path, on_status=on_status
            )

            # Delete the status message and send the final response
            try:
                await status_msg.delete()
            except Exception:
                logger.debug("Could not delete status message")

            response = _format_telegram_response(analysis)
            await update.message.reply_text(
                response, parse_mode="HTML",
                disable_web_page_preview=False
            )
            await self.db.update_state(job_id, JobState.COMPLETED)
            logger.info("Job %s: completed (voice) for chat %d", job_id, chat_id)

        except Exception:
            logger.exception("Failed to process voice for chat %d", chat_id)
            try:
                await status_msg.delete()
            except Exception:
                pass
            await update.message.reply_text(
                "Sorry, an error occurred while processing your voice message. "
                "Please try again later."
            )

    def build_application(self) -> Application:
        """Build and return the Telegram Application."""
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text)
        )
        app.add_handler(
            MessageHandler(filters.VOICE, self.handle_voice)
        )
        return app
