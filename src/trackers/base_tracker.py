"""
Abstract base class for all trackers.

Every tracker must implement ``fetch_new_items`` which accepts a set of
already-seen item IDs and returns a list of new items as dictionaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTracker(ABC):
    """
    Interface that every tracker must implement.

    Parameters
    ----------
    settings : Any
        The application ``Settings`` object (or a subset of it).
    """

    def __init__(self, settings: Any) -> None:
        self.settings = settings

    @abstractmethod
    def fetch_new_items(self, seen_ids: set[str]) -> list[dict]:
        """
        Query the upstream source and return items not yet seen.

        Parameters
        ----------
        seen_ids : set[str]
            IDs of previously reported items.

        Returns
        -------
        list[dict]
            Each dict must contain at minimum:
            ``id``, ``title``, ``url``, ``description``.
        """
        ...
