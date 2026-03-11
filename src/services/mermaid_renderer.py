"""Mermaid diagram rendering using mermaid.ink API (no local install needed)."""

from __future__ import annotations

import logging
import base64
import zlib
from pathlib import Path
from urllib.parse import quote

import aiohttp

from src.config import DIAGRAMS_DIR

logger = logging.getLogger(__name__)

MERMAID_INK_URL = "https://mermaid.ink/img/"


def _encode_mermaid(source: str) -> str:
    """Encode Mermaid source for mermaid.ink URL using pako deflate."""
    json_str = '{"code":"' + source.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '","mermaid":{"theme":"default"}}'
    compressed = zlib.compress(json_str.encode("utf-8"), level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return "pako:" + encoded


async def render_mermaid_to_image(
    mermaid_source: str, output_name: str
) -> str | None:
    """Render Mermaid source to a PNG image file. Returns the file path or None on failure."""
    if not mermaid_source or not mermaid_source.strip():
        return None

    source = mermaid_source.strip()
    output_path = DIAGRAMS_DIR / f"{output_name}.png"

    try:
        encoded = _encode_mermaid(source)
        url = MERMAID_INK_URL + encoded

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    output_path.write_bytes(content)
                    logger.info("Rendered diagram: %s (%d bytes)", output_name, len(content))
                    return str(output_path)
                else:
                    body = await resp.text()
                    logger.warning(
                        "Mermaid.ink returned %d for %s: %s",
                        resp.status, output_name, body[:200]
                    )
                    return None
    except Exception:
        logger.exception("Failed to render Mermaid diagram: %s", output_name)
        return None


async def render_all_diagrams(analysis) -> None:
    """Render all Mermaid diagrams in a ProcessAnalysis object and update image_path fields."""
    job_prefix = analysis.process_title.replace(" ", "_")[:30].lower()

    diagram_tasks = [
        (analysis.asis, "mermaid_source", f"{job_prefix}_asis"),
        (analysis.tobe, "mermaid_source", f"{job_prefix}_tobe"),
        (analysis.human_role, "mermaid_source", f"{job_prefix}_human_role"),
        (analysis.agent, "skill_graph_mermaid_source", f"{job_prefix}_agent_skills"),
        (analysis.architecture, "mermaid_source", f"{job_prefix}_architecture"),
    ]

    for obj, attr, name in diagram_tasks:
        source = getattr(obj, attr, "")
        if source:
            path = await render_mermaid_to_image(source, name)
            if path:
                obj.image_path = path

    # Render feature user flow diagrams
    for i, feature in enumerate(analysis.prd.features):
        if feature.user_flow and feature.user_flow.mermaid_source:
            fname = f"{job_prefix}_feature_{i}"
            path = await render_mermaid_to_image(
                feature.user_flow.mermaid_source, fname
            )
            if path:
                feature.user_flow.image_path = path
