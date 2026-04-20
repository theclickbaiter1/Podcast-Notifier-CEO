"""
Centralized configuration loader.

Reads environment variables (from .env locally, or injected by GitHub Actions)
and validates that all required secrets are present.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# ── Load .env for local development ──────────────────────────────────────────
# In GitHub Actions the variables are injected directly, so this is a no-op.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


_REQUIRED_VARS = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


@dataclass(frozen=True)
class Settings:
    """Immutable container for all application settings."""

    telegram_bot_token: str
    telegram_chat_id: str

    # Path to the deduplication state file (relative to repo root)
    seen_file: Path = Path(__file__).resolve().parent.parent / "seen.json"


def load_settings() -> Settings:
    """
    Build a ``Settings`` instance from environment variables.

    Raises
    ------
    EnvironmentError
        If one or more required variables are missing.
    """
    missing = [v for v in _REQUIRED_VARS if not os.getenv(v)]
    if missing:
        print(
            f"[CONFIG] ❌ Missing required environment variables: {', '.join(missing)}",
            file=sys.stderr,
        )
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return Settings(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )
