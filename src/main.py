"""
Entry point — orchestrates trackers and notifiers.

1. Load config & seen-state.
2. Run every registered tracker to collect new items.
3. Pass all new items to every registered notifier.
4. Persist the updated seen-state to ``seen.json``.

To add a new tracker or notifier, simply import it and append to the
corresponding list below.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from src.config import load_settings

# ── Tracker imports ───────────────────────────────────────────────────────────
from src.trackers.itunes import ITunesTracker

# ── Notifier imports ──────────────────────────────────────────────────────────
from src.notifiers.telegram import TelegramNotifier

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── State helpers ─────────────────────────────────────────────────────────────

def _load_seen(path: Path) -> set[str]:
    """Load previously seen IDs from a JSON file."""
    if not path.exists():
        logger.info("No seen.json found — starting fresh.")
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded %d seen IDs from %s.", len(data), path)
        return set(data)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Corrupt seen.json — resetting.")
        return set()


def _save_seen(path: Path, seen_ids: set[str]) -> None:
    """Persist the seen IDs back to disk as a JSON array."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_ids), f, indent=2)
    logger.info("Saved %d seen IDs to %s.", len(seen_ids), path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """Run the full tracker → notifier pipeline."""

    # 1. Load configuration
    try:
        settings = load_settings()
    except EnvironmentError:
        sys.exit(1)

    # 2. Load deduplication state
    seen_ids = _load_seen(settings.seen_file)

    # ──────────────────────────────────────────────────────────────────────
    # REGISTRY — add new trackers / notifiers here
    # ──────────────────────────────────────────────────────────────────────
    trackers = [
        ITunesTracker(settings),
        # FutureTracker(settings),
    ]

    notifiers = [
        TelegramNotifier(settings),
        # DiscordNotifier(settings),
    ]
    # ──────────────────────────────────────────────────────────────────────

    # 3. Collect new items from all trackers
    all_new_items: list[dict] = []
    for tracker in trackers:
        tracker_name = type(tracker).__name__
        logger.info("Running tracker: %s", tracker_name)
        try:
            items = tracker.fetch_new_items(seen_ids)
            all_new_items.extend(items)
        except Exception:
            logger.exception("Tracker %s failed.", tracker_name)

    if not all_new_items:
        logger.info("No new items found. Nothing to notify.")
    else:
        logger.info("Collected %d new item(s). Sending notifications…", len(all_new_items))

    # 4. Notify through all channels
    for notifier in notifiers:
        notifier_name = type(notifier).__name__
        logger.info("Running notifier: %s", notifier_name)
        try:
            notifier.send(all_new_items)
        except Exception:
            logger.exception("Notifier %s failed.", notifier_name)

    # 5. Update seen state (even if sending failed — avoids retrying bad items forever)
    for item in all_new_items:
        seen_ids.add(item["id"])

    _save_seen(settings.seen_file, seen_ids)

    logger.info("Run complete.")


if __name__ == "__main__":
    main()
