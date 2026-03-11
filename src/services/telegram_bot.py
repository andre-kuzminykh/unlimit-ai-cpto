"""Telegram bot — accepts text/voice, runs pipeline, sends status updates, then final response."""

import asyncio
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

# Rotating sub-statuses shown during the long-running analysis phase
# Substeps shown during LLM analysis — aligned with what actually happens
_ANALYSIS_SUBSTEPS = [
    "Reading process description...",
    "Extracting key entities and actors...",
    "Mapping AS-IS process steps...",
    "Identifying roles and systems...",
    "Analyzing current metrics and KPIs...",
    "Spotting automation opportunities...",
    "Designing TO-BE process with AI Agent...",
    "Mapping human touchpoints in TO-BE...",
    "Assigning agent vs human responsibilities...",
    "Defining Agent skills and capabilities...",
    "Mapping skills to TO-BE operation points...",
    "Writing product requirements...",
    "Creating user stories and use cases...",
    "Generating feature acceptance criteria...",
    "Building AS-IS sequence diagram...",
    "Building TO-BE sequence diagram...",
    "Building agent skill graph...",
    "Designing system architecture...",
    "Building architecture diagram...",
    "Generating implementation workplan...",
    "Breaking down tasks into subtasks...",
    "Writing acceptance criteria for subtasks...",
    "Cross-checking requirements consistency...",
    "Validating diagrams and flows...",
    "Aligning workplan with features...",
    "Composing executive summary...",
    "Verifying traceability across sections...",
    "Finalizing structured output...",
    "Performing quality checks...",
    "Almost done — wrapping up...",
]

# How often (seconds) to rotate the sub-status during analysis
_SUBSTEP_INTERVAL = 3


class _StatusUpdater:
    """Manages animated status updates on a Telegram message."""

    def __init__(self, msg, is_voice: bool):
        self._msg = msg
        self._is_voice = is_voice
        self._phase = "idle"
        self._task: asyncio.Task | None = None
        self._total = 24 if is_voice else 22

    async def set_phase(self, phase: str):
        """Called by orchestrator events. Starts/stops the rotating animation."""
        self._phase = phase
        self._stop_animation()

        if phase == "transcribe_start":
            await self._edit("Transcribing voice message...", 1)
        elif phase == "transcribe_done":
            await self._edit("Voice transcribed successfully", 2)
        elif phase == "analyze_start":
            # Start rotating sub-statuses
            self._task = asyncio.create_task(self._animate_analysis())
        elif phase == "analyze_done":
            await self._edit("Analysis complete", self._total - 4)
        elif phase == "parsing":
            await self._edit("Parsing structured data...", self._total - 3)
        elif phase == "validating":
            await self._edit("Validating analysis schema...", self._total - 2)
        elif phase == "html_start":
            await self._edit("Building HTML report...", self._total - 1)
        elif phase == "html_done":
            await self._edit("Report ready, sending...", self._total)
        elif phase == "finalizing":
            await self._edit("Done!", self._total)

    async def _animate_analysis(self):
        """Rotate through analysis sub-steps every few seconds."""
        base = 3 if self._is_voice else 1
        max_progress = self._total - 5
        try:
            for i, label in enumerate(_ANALYSIS_SUBSTEPS):
                progress = base + i
                if progress > max_progress:
                    progress = max_progress
                await self._edit(label, progress)
                await asyncio.sleep(_SUBSTEP_INTERVAL)
            # If still running, keep last message visible
            while True:
                await asyncio.sleep(_SUBSTEP_INTERVAL)
        except asyncio.CancelledError:
            pass

    def _stop_animation(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    async def _edit(self, label: str, step: int):
        filled = ">" * step
        empty = "." * (self._total - step)
        text = f"[{filled}{empty}] {label}"
        try:
            await self._msg.edit_text(text)
        except Exception:
            logger.debug("Could not update status message")

    def stop(self):
        self._stop_animation()


def _format_telegram_response(analysis) -> str:
    """Format the final Telegram response with a plain URL (not hyperlink)."""
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
        return f"{body}\n\nFull Report:\n{url}"
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
            "[>.........] Reading process description..."
        )
        updater = _StatusUpdater(status_msg, is_voice=False)

        try:
            job_id, analysis = await self.orchestrator.process_text(
                chat_id, message_id, text,
                on_status=updater.set_phase,
            )
            updater.stop()

            # Delete the status message and send the final response
            try:
                await status_msg.delete()
            except Exception:
                logger.debug("Could not delete status message")

            response = _format_telegram_response(analysis)
            await update.message.reply_text(response)
            await self.db.update_state(job_id, JobState.COMPLETED)
            logger.info("Job %s: completed and sent to chat %d", job_id, chat_id)

        except Exception:
            updater.stop()
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
            "[>..........] Downloading voice file..."
        )
        updater = _StatusUpdater(status_msg, is_voice=True)

        try:
            # Download voice file
            voice_file = await context.bot.get_file(voice.file_id)
            tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
            tmp_path = Path(tmp.name)
            tmp.close()
            await voice_file.download_to_drive(str(tmp_path))

            job_id, analysis = await self.orchestrator.process_voice(
                chat_id, message_id, tmp_path,
                on_status=updater.set_phase,
            )
            updater.stop()

            # Delete the status message and send the final response
            try:
                await status_msg.delete()
            except Exception:
                logger.debug("Could not delete status message")

            response = _format_telegram_response(analysis)
            await update.message.reply_text(response)
            await self.db.update_state(job_id, JobState.COMPLETED)
            logger.info("Job %s: completed (voice) for chat %d", job_id, chat_id)

        except Exception:
            updater.stop()
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
