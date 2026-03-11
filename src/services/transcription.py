"""Speech-to-text transcription using OpenAI Whisper API."""

import logging
from pathlib import Path
from openai import AsyncOpenAI
from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


async def transcribe_voice(audio_path: Path) -> str:
    """Transcribe a voice file to text using OpenAI Whisper."""
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        with open(audio_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en",
            )
        transcript = response.text.strip()
        logger.info("Transcription completed: %d characters", len(transcript))
        return transcript
    except Exception:
        logger.exception("Transcription failed")
        raise
    finally:
        if audio_path.exists():
            audio_path.unlink()
