"""
Podcast Index tracker.

Searches the Podcast Index API for podcast feeds matching notable
tech / AI CEOs, then fetches their recent episodes and filters by
duration to find long-form appearances.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

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

# Only look at episodes published in the last N days.
MAX_AGE_DAYS = 7

API_BASE_URL = "https://api.podcastindex.org/api/1.0"

# How many feeds to inspect per CEO (the most relevant ones).
MAX_FEEDS_PER_CEO = 5


class PodcastIndexTracker(BaseTracker):
    """
    Two-step search:
      1. ``/search/byterm`` → find podcast **feeds** mentioning the CEO.
      2. ``/episodes/byfeedid``  → fetch recent **episodes** from each feed.
    Then filter by duration and deduplicate.
    """

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self.api_key: str = settings.podcast_index_api_key
        self.api_secret: str = settings.podcast_index_api_secret

    # ── Authentication ────────────────────────────────────────────────────
    def _auth_headers(self) -> dict[str, str]:
        epoch = str(int(time.time()))
        data_to_hash = self.api_key + self.api_secret + epoch
        sha1_hash = hashlib.sha1(data_to_hash.encode("utf-8")).hexdigest()
        return {
            "X-Auth-Date": epoch,
            "X-Auth-Key": self.api_key,
            "Authorization": sha1_hash,
            "User-Agent": "OnlineNotifier/1.0",
        }

    # ── Public interface ──────────────────────────────────────────────────
    def fetch_new_items(self, seen_ids: set[str]) -> list[dict]:
        new_items: list[dict] = []
        since = int(time.time()) - (MAX_AGE_DAYS * 86400)

        for person in WHALE_CEOS:
            logger.info("Searching Podcast Index for: %s", person)

            # Step 1 — find feeds mentioning this CEO
            try:
                feeds = self._search_feeds(person)
            except requests.RequestException as exc:
                logger.warning("Feed search error for '%s': %s", person, exc)
                continue

            # Step 2 — for each feed, get recent episodes
            for feed in feeds[:MAX_FEEDS_PER_CEO]:
                feed_id = feed.get("id")
                if not feed_id:
                    continue

                try:
                    episodes = self._get_episodes(feed_id, since)
                except requests.RequestException as exc:
                    logger.warning("Episode fetch error (feed %s): %s", feed_id, exc)
                    continue

                for ep in episodes:
                    ep_id = str(ep.get("id", ""))
                    duration = ep.get("duration", 0) or 0

                    if ep_id in seen_ids:
                        continue

                    if duration < MIN_DURATION_SECONDS:
                        logger.debug(
                            "Skipping short episode (%ds): %s",
                            duration,
                            ep.get("title", ""),
                        )
                        continue

                    new_items.append(
                        {
                            "id": ep_id,
                            "title": ep.get("title", "Untitled"),
                            "url": ep.get("link")
                            or ep.get("enclosureUrl", ""),
                            "description": ep.get("description", ""),
                            "duration": duration,
                            "person": person,
                            "podcast": feed.get("title", ""),
                        }
                    )

                time.sleep(0.3)  # rate-limit between episode fetches

            time.sleep(0.5)  # rate-limit between CEO searches

        logger.info("Found %d new episode(s) across all CEOs.", len(new_items))
        return new_items

    # ── Private helpers ───────────────────────────────────────────────────
    def _search_feeds(self, term: str) -> list[dict]:
        """``/search/byterm`` → list of podcast feeds."""
        resp = requests.get(
            f"{API_BASE_URL}/search/byterm",
            params={"q": term},
            headers=self._auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("feeds", [])

    def _get_episodes(self, feed_id: int, since: int) -> list[dict]:
        """``/episodes/byfeedid`` → recent episodes for a feed."""
        resp = requests.get(
            f"{API_BASE_URL}/episodes/byfeedid",
            params={"id": feed_id, "since": since, "max": 20},
            headers=self._auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])
