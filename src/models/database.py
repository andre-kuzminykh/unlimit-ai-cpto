"""SQLite database for job tracking with async support."""

from __future__ import annotations

import json
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum
from typing import Optional


class JobState(str, Enum):
    RECEIVED = "received"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    RENDERING_DIAGRAMS = "rendering_diagrams"
    GENERATING_HTML = "generating_html"
    SENDING_FINAL_MESSAGE = "sending_final_message"
    COMPLETED = "completed"
    FAILED = "failed"


_VALID_TRANSITIONS = {
    JobState.RECEIVED: {JobState.TRANSCRIBING, JobState.ANALYZING, JobState.FAILED},
    JobState.TRANSCRIBING: {JobState.ANALYZING, JobState.FAILED},
    JobState.ANALYZING: {JobState.RENDERING_DIAGRAMS, JobState.FAILED},
    JobState.RENDERING_DIAGRAMS: {JobState.GENERATING_HTML, JobState.FAILED},
    JobState.GENERATING_HTML: {JobState.SENDING_FINAL_MESSAGE, JobState.FAILED},
    JobState.SENDING_FINAL_MESSAGE: {JobState.COMPLETED, JobState.FAILED},
}


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER,
                    input_type TEXT NOT NULL DEFAULT 'text',
                    input_text TEXT,
                    state TEXT NOT NULL DEFAULT 'received',
                    analysis_json TEXT,
                    html_url TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.commit()

    async def create_job(self, job_id: str, chat_id: int, message_id: int,
                         input_type: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO jobs (id, chat_id, message_id, input_type, state,
                   created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (job_id, chat_id, message_id, input_type,
                 JobState.RECEIVED.value, now, now),
            )
            await db.commit()
        return {"id": job_id, "state": JobState.RECEIVED.value}

    async def update_state(self, job_id: str, new_state: JobState,
                           error: str | None = None):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT state FROM jobs WHERE id = ?", (job_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                raise ValueError(f"Job {job_id} not found")

            current = JobState(row["state"])
            if current in _VALID_TRANSITIONS:
                if new_state not in _VALID_TRANSITIONS[current]:
                    raise ValueError(
                        f"Invalid transition: {current} -> {new_state}"
                    )

            params = [new_state.value, now]
            sql = "UPDATE jobs SET state = ?, updated_at = ?"
            if error:
                sql += ", error = ?"
                params.append(error)
            sql += " WHERE id = ?"
            params.append(job_id)
            await db.execute(sql, params)
            await db.commit()

    async def save_analysis(self, job_id: str, analysis_json: str,
                            html_url: str):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE jobs SET analysis_json = ?, html_url = ?,
                   updated_at = ? WHERE id = ?""",
                (analysis_json, html_url, now, job_id),
            )
            await db.commit()

    async def save_input_text(self, job_id: str, input_text: str):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET input_text = ?, updated_at = ? WHERE id = ?",
                (input_text, now, job_id),
            )
            await db.commit()

    async def get_job(self, job_id: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
