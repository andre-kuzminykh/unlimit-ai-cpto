"""Entry point — starts the Telegram bot and HTTP report server."""

import asyncio
import logging
import sys

from src.config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
from src.models.database import Database
from src.config import DATABASE_PATH
from src.report_server import create_report_server
from src.services.telegram_bot import TelegramBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def main():
    # Validate configuration
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        sys.exit(1)
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not set")
        sys.exit(1)

    # Initialize database
    db = Database(DATABASE_PATH)
    await db.initialize()
    logger.info("Database initialized at %s", DATABASE_PATH)

    # Start report server
    report_runner = await create_report_server()
    logger.info("Report server running")

    # Start Telegram bot
    bot = TelegramBot(db)
    app = bot.build_application()

    logger.info("Starting Telegram bot...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("Bot is running. Press Ctrl+C to stop.")

    # Keep running until interrupted
    stop_event = asyncio.Event()

    def _signal_handler():
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        try:
            import signal
            loop.add_signal_handler(getattr(signal, sig_name), _signal_handler)
        except (NotImplementedError, AttributeError):
            pass

    await stop_event.wait()

    # Graceful shutdown
    logger.info("Shutting down...")
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    await report_runner.cleanup()
    logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
