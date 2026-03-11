"""Orchestration pipeline — coordinates the full process analysis workflow."""

import logging
import uuid
from pathlib import Path
from typing import Callable, Awaitable, Optional

from src.models.database import Database, JobState
from src.models.schemas import ProcessAnalysis
from src.services.transcription import transcribe_voice
from src.services.analysis import analyze_process
from src.services.mermaid_renderer import render_all_diagrams
from src.services.html_generator import generate_html_report

logger = logging.getLogger(__name__)

# Status callback type: async function that receives a status string
StatusCallback = Optional[Callable[[str], Awaitable[None]]]


class Orchestrator:
    def __init__(self, db: Database):
        self.db = db

    async def process_text(self, chat_id: int, message_id: int,
                           input_text: str,
                           on_status: StatusCallback = None) -> tuple[str, ProcessAnalysis]:
        """Run the full pipeline for a text input. Returns (job_id, analysis)."""
        job_id = uuid.uuid4().hex[:16]
        await self.db.create_job(job_id, chat_id, message_id, "text")
        return await self._run_pipeline(job_id, input_text, "text", on_status)

    async def process_voice(self, chat_id: int, message_id: int,
                            audio_path: Path,
                            on_status: StatusCallback = None) -> tuple[str, ProcessAnalysis]:
        """Run the full pipeline for a voice input. Returns (job_id, analysis)."""
        job_id = uuid.uuid4().hex[:16]
        await self.db.create_job(job_id, chat_id, message_id, "voice")

        # Step 1: Transcribe
        try:
            await self.db.update_state(job_id, JobState.TRANSCRIBING)
            if on_status:
                await on_status("Transcribing voice message...")
            input_text = await transcribe_voice(audio_path)
            if not input_text.strip():
                raise ValueError("Transcription returned empty text")
            await self.db.save_input_text(job_id, input_text)
            logger.info("Job %s: transcription complete", job_id)
        except Exception as e:
            await self.db.update_state(job_id, JobState.FAILED, str(e))
            raise

        return await self._run_pipeline(job_id, input_text, "voice", on_status)

    async def _run_pipeline(self, job_id: str, input_text: str,
                            input_type: str,
                            on_status: StatusCallback = None) -> tuple[str, ProcessAnalysis]:
        """Core pipeline: analyze -> render diagrams -> generate HTML."""

        # Step 2: Analyze
        try:
            await self.db.update_state(job_id, JobState.ANALYZING)
            if on_status:
                await on_status("Analyzing business process...")
            analysis = await analyze_process(input_text, input_type)
            logger.info("Job %s: analysis complete — %s", job_id, analysis.process_title)
        except Exception as e:
            await self.db.update_state(job_id, JobState.FAILED, str(e))
            raise

        # Step 3: Render diagrams
        try:
            await self.db.update_state(job_id, JobState.RENDERING_DIAGRAMS)
            if on_status:
                await on_status("Rendering diagrams...")
            await render_all_diagrams(analysis)
            logger.info("Job %s: diagrams rendered", job_id)
        except Exception as e:
            await self.db.update_state(job_id, JobState.FAILED, str(e))
            raise

        # Step 4: Generate HTML report
        try:
            await self.db.update_state(job_id, JobState.GENERATING_HTML)
            if on_status:
                await on_status("Generating HTML report...")
            filepath, url = generate_html_report(analysis)
            analysis.html_url = url
            logger.info("Job %s: HTML report at %s", job_id, url)
        except Exception as e:
            await self.db.update_state(job_id, JobState.FAILED, str(e))
            raise

        # Save analysis
        await self.db.save_analysis(
            job_id, analysis.model_dump_json(), url
        )
        await self.db.update_state(job_id, JobState.SENDING_FINAL_MESSAGE)
        if on_status:
            await on_status("Preparing final message...")

        return job_id, analysis
