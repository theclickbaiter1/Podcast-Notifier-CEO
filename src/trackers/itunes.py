"""
iTunes Search tracker.

Searches the Apple iTunes Search API for podcast episodes featuring
notable tech / AI CEOs ("Whale CEOs").  This API is completely free
and requires no authentication.

API docs: https://developer.apple.com/library/archive/documentation/
           AudioVideo/Conceptual/iTuneSearchAPI/Searching.html
"""

from __future__ import annotations

import logging
import time

import requests

from src.trackers.base_tracker import BaseTracker

logger = logging.getLogger(__name__)

# ── Target names to search for ───────────────────────────────────────────────
# Add or remove names here to change who is tracked.
WHALE_CEOS: list[str] = [
    "Elon Musk",
    "Jensen Huang",
    "Sam Altman",
    "Satya Nadella",
    "Sundar Pichai",
    "Mark Zuckerberg",
    "Tim Cook",
    "Alexandr Wang",
    "Dario Amodei",
    "Demis Hassabis",
    "Lisa Su",
]

# Minimum episode duration in seconds (25 minutes).
MIN_DURATION_SECONDS = 1500

# iTunes Search API returns duration in milliseconds.
MIN_DURATION_MS = MIN_DURATION_SECONDS * 1000

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"

# Max results per search term (iTunes caps at 200).
RESULTS_LIMIT = 50


class ITunesTracker(BaseTracker):
    """
    Queries the iTunes Search API ``/search`` endpoint for podcast episodes
    matching each CEO name, filters out short clips, and deduplicates
    against previously seen IDs.
    """

    # No API keys needed — settings param kept for interface consistency.

    # ── Public interface ──────────────────────────────────────────────────
    def fetch_new_items(self, seen_ids: set[str]) -> list[dict]:
        """
        Search for each Whale CEO and return unseen, long-form episodes.
        """
        new_items: list[dict] = []

        for person in WHALE_CEOS:
            logger.info("Searching iTunes for: %s", person)
            try:
                episodes = self._search(person)
            except requests.RequestException as exc:
                logger.warning("API error searching '%s': %s", person, exc)
                continue

            for ep in episodes:
                ep_id = str(ep.get("trackId", ""))
                duration_ms = ep.get("trackTimeMillis") or 0

                # Skip already-seen episodes
                if ep_id in seen_ids:
                    continue

                # Skip short clips / teasers (< 25 minutes)
                if duration_ms < MIN_DURATION_MS:
                    logger.debug(
                        "Skipping short episode (%ds): %s",
                        duration_ms // 1000,
                        ep.get("trackName", ""),
                    )
                    continue

                new_items.append(
                    {
                        "id": ep_id,
                        "title": ep.get("trackName", "Untitled"),
                        "url": ep.get("trackViewUrl")
                        or ep.get("episodeUrl", ""),
                        "description": ep.get("description")
                        or ep.get("shortDescription", ""),
                        "duration": duration_ms // 1000,  # store as seconds
                        "person": person,
                        "podcast": ep.get("collectionName", ""),
                    }
                )

            # Be kind to the API — stay well under rate limits.
            time.sleep(0.5)

        logger.info("Found %d new episode(s) across all CEOs.", len(new_items))
        return new_items

    # ── Private helpers ───────────────────────────────────────────────────
    @staticmethod
    def _search(term: str) -> list[dict]:
        """
        Call the iTunes Search API and return matching podcast episodes.
        """
        params = {
            "term": term,
            "media": "podcast",
            "entity": "podcastEpisode",
            "limit": RESULTS_LIMIT,
        }

        resp = requests.get(ITUNES_SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        return data.get("results", [])
