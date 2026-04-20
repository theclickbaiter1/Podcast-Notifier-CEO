"""
Podcast Index tracker.

Two modes of discovery:
  1. **CEO Search** — find feeds mentioning Whale CEOs, fetch recent episodes.
  2. **Curated AI Podcasts** — monitor a hand-picked list of top-tier tech/AI
     podcasts for any new episodes.

Both modes filter by recency (25 hours) and duration (25+ minutes), and apply
a quality filter to discard AI-generated slop and clip channels.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any

import requests

from src.trackers.base_tracker import BaseTracker

logger = logging.getLogger(__name__)

# ── Target CEO names ─────────────────────────────────────────────────────────
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

# ── Curated high-quality AI / tech podcasts (by feed title search) ───────────
# We search for these by name to get their feed IDs, then pull recent episodes.
CURATED_AI_PODCASTS: list[str] = [
    "Lex Fridman Podcast",
    "All-In Podcast",
    "Hard Fork",
    "The Logan Bartlett Show",
    "No Priors: Artificial Intelligence",
    "Dwarkesh Podcast",
    "Eye on AI",
    "Latent Space: The AI Engineer Podcast",
    "Gradient Dissent",
    "Practical AI",
    "The AI Podcast",              # NVIDIA's podcast
    "This Week in Machine Learning",
    "Machine Learning Street Talk",
    "The Twenty Minute VC",
    "Acquired",
    "BG2Pod with Brad Gerstner and Bill Gurley",
]

# ── Filtering constants ──────────────────────────────────────────────────────
MIN_DURATION_SECONDS = 1500      # 25 minutes
MAX_AGE_SECONDS = 25 * 3600     # 25 hours — one daily run + 1h buffer

# How many feeds to inspect per CEO search term.
MAX_FEEDS_PER_SEARCH = 5

# ── Slop / low-quality content patterns (case-insensitive) ───────────────────
_SLOP_PATTERNS = re.compile(
    r"|".join([
        r"\bai[\s-]*generated\b",
        r"\bai[\s-]*narrated\b",
        r"\bai[\s-]*voice\b",
        r"\btext[\s-]*to[\s-]*speech\b",
        r"\btts\b",
        r"\b(shorts?|clip|highlight|teaser|preview|trailer)\b",
        r"\breupload\b",
        r"\bre[\s-]*upload\b",
        r"\bfan[\s-]*made\b",
        r"\bunofficial\b",
        r"\bcompilation\b",
        r"\b#\d+\s*-?\s*#\d+\b",   # "Episode #1 - #50" compilation patterns
    ]),
    re.IGNORECASE,
)

API_BASE_URL = "https://api.podcastindex.org/api/1.0"


class PodcastIndexTracker(BaseTracker):
    """
    Discovers new podcast episodes via CEO name search and curated feed
    monitoring, then filters for quality and recency.
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
        since = int(time.time()) - MAX_AGE_SECONDS
        new_items: list[dict] = []
        seen_ep_ids: set[str] = set()  # local dedup within this run

        # ── Mode 1: CEO name search ──────────────────────────────────────
        for person in WHALE_CEOS:
            logger.info("Searching for CEO: %s", person)
            try:
                feeds = self._search_feeds(person)
            except requests.RequestException as exc:
                logger.warning("Feed search error for '%s': %s", person, exc)
                continue

            for feed in feeds[:MAX_FEEDS_PER_SEARCH]:
                self._collect_episodes(
                    feed, since, seen_ids, seen_ep_ids, new_items,
                    tag=person,
                )
                time.sleep(0.3)
            time.sleep(0.5)

        # ── Mode 2: Curated AI/tech podcasts ─────────────────────────────
        for podcast_name in CURATED_AI_PODCASTS:
            logger.info("Checking curated podcast: %s", podcast_name)
            try:
                feeds = self._search_feeds(podcast_name)
            except requests.RequestException as exc:
                logger.warning("Feed search error for '%s': %s", podcast_name, exc)
                continue

            # Take only the top match (most relevant)
            if feeds:
                self._collect_episodes(
                    feeds[0], since, seen_ids, seen_ep_ids, new_items,
                    tag="AI/Tech",
                )
            time.sleep(0.5)

        logger.info("Found %d new episode(s) total.", len(new_items))
        return new_items

    # ── Private helpers ───────────────────────────────────────────────────
    def _collect_episodes(
        self,
        feed: dict,
        since: int,
        seen_ids: set[str],
        seen_ep_ids: set[str],
        out: list[dict],
        tag: str,
    ) -> None:
        """Fetch recent episodes from a feed and append qualifying ones."""
        feed_id = feed.get("id")
        if not feed_id:
            return

        try:
            episodes = self._get_episodes(feed_id, since)
        except requests.RequestException as exc:
            logger.warning("Episode fetch error (feed %s): %s", feed_id, exc)
            return

        for ep in episodes:
            ep_id = str(ep.get("id", ""))
            duration = ep.get("duration", 0) or 0
            title = ep.get("title", "")

            # Skip dups (already notified, or already found this run)
            if ep_id in seen_ids or ep_id in seen_ep_ids:
                continue

            # Skip short clips
            if duration < MIN_DURATION_SECONDS:
                continue

            # Skip AI slop / low-quality content
            if _is_slop(title, ep.get("description", "")):
                logger.debug("Filtered slop: %s", title)
                continue

            seen_ep_ids.add(ep_id)
            out.append({
                "id": ep_id,
                "title": title or "Untitled",
                "url": ep.get("link") or ep.get("enclosureUrl", ""),
                "description": ep.get("description", ""),
                "duration": duration,
                "person": tag,
                "podcast": feed.get("title", ""),
            })

    def _search_feeds(self, term: str) -> list[dict]:
        resp = requests.get(
            f"{API_BASE_URL}/search/byterm",
            params={"q": term},
            headers=self._auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("feeds", [])

    def _get_episodes(self, feed_id: int, since: int) -> list[dict]:
        resp = requests.get(
            f"{API_BASE_URL}/episodes/byfeedid",
            params={"id": feed_id, "since": since, "max": 10},
            headers=self._auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])


def _is_slop(title: str, description: str) -> bool:
    """Return True if the episode looks like AI-generated or reused content."""
    text = f"{title} {description}"
    return bool(_SLOP_PATTERNS.search(text))
