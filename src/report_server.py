"""Simple HTTP server to serve HTML reports and static files."""

import logging
from aiohttp import web
from src.config import STATIC_DIR, REPORT_SERVER_PORT

logger = logging.getLogger(__name__)


async def create_report_server() -> web.AppRunner:
    """Create and start the static file server for HTML reports."""
    app = web.Application()
    app.router.add_static("/reports/", path=str(STATIC_DIR / "reports"), name="reports")
    app.router.add_static("/diagrams/", path=str(STATIC_DIR / "diagrams"), name="diagrams")

    async def health(request):
        return web.Response(text="ok")

    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", REPORT_SERVER_PORT)
    await site.start()
    logger.info("Report server started on port %d", REPORT_SERVER_PORT)
    return runner
