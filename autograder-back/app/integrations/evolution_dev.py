"""
File-based message sink for dev/test.

Drop-in replacement for evolution.send_message — same signature, writes .txt
files to disk instead of calling Evolution API.  Files are grouped by send_id
so you can inspect what each campaign / lifecycle event would have sent.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Mirror the production normalisation (digits only, prepend 55 for BR)."""
    digits = "".join(c for c in phone if c.isdigit()).lstrip("0")
    if len(digits) in (10, 11):
        return "55" + digits
    return digits


def send_message(phone: str, text: str, send_id: str | None = None) -> bool:
    """
    Write a WhatsApp message to disk instead of sending it.

    Layout:
        {output_dir}/{send_id}/{phone}.txt          — when send_id provided
        {output_dir}/_ungrouped/{phone}_{ts}.txt     — when send_id is None
    """
    if not phone:
        logger.warning("dev send_message called with empty phone. Skipping.")
        return False

    phone = _normalize_phone(phone)
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H-%M-%S")

    output_dir = Path(settings.evolution_dev_output_dir)

    if send_id:
        folder = output_dir / send_id
        file_path = folder / f"{phone}.txt"
    else:
        folder = output_dir / "_ungrouped"
        file_path = folder / f"{phone}_{ts}.txt"

    folder.mkdir(parents=True, exist_ok=True)

    envelope = f"TO: {phone}\nAT: {now.isoformat()}\n---\n{text}\n"

    if file_path.exists():
        envelope = f"\n---\n{envelope}"

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(envelope)

    logger.info("dev send_message → %s", file_path)
    return True
