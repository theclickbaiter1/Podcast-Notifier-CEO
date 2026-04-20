"""
Telegram notifier.

Formats item dicts into rich HTML messages and sends them to a Telegram
chat via the Bot API.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.notifiers.base_notifier import BaseNotifier

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramNotifier(BaseNotifier):
    """
    Sends notification messages to Telegram using the Bot API.
    """

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self.bot_token: str = settings.telegram_bot_token
        self.chat_id: str = settings.telegram_chat_id

    # ── Public interface ──────────────────────────────────────────────────
    def send(self, items: list[dict]) -> None:
        """
        Send each item as an individual Telegram message.

        Sleeps briefly between messages to respect Telegram rate limits
        (~30 messages / second for bots, but we play it safe).
        """
        if not items:
            logger.info("No new items to send via Telegram.")
            return

        for item in items:
            message = self._format_message(item)
            self._send_message(message)
            time.sleep(0.35)  # ~3 messages/sec, well within limits

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _format_message(item: dict) -> str:
        """
        Build an HTML-formatted Telegram message.

        Example output::

            🎙️ <b>The Lex Fridman Podcast — Jensen Huang</b>
            👤 Matched: Jensen Huang
            ⏱️ Duration: 1h 23m
            🔗 <a href="https://...">Listen here</a>
        """
        duration_sec = item.get("duration", 0)
        hours, remainder = divmod(int(duration_sec), 3600)
        minutes = remainder // 60
        duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"

        title = item.get("title", "Untitled")
        url = item.get("url", "")
        person = item.get("person", "Unknown")

        podcast = item.get("podcast", "")

        lines = [
            f"🎙️ <b>{_escape_html(title)}</b>",
        ]
        if podcast:
            lines.append(f"📡 Podcast: {_escape_html(podcast)}")
        lines.extend([
            f"👤 Matched: {_escape_html(person)}",
            f"⏱️ Duration: {duration_str}",
        ])
        if url:
            lines.append(f'🔗 <a href="{url}">Listen here</a>')

        return "\n".join(lines)

    def _send_message(self, text: str) -> None:
        """
        POST a message to the Telegram Bot ``sendMessage`` endpoint.
        """
        url = f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            logger.info("Telegram message sent successfully.")
        except requests.RequestException as exc:
            logger.error("Failed to send Telegram message: %s", exc)


def _escape_html(text: str) -> str:
    """Escape characters that are special in Telegram HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
