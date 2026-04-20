"""
Abstract base class for all notifiers.

Every notifier must implement ``send`` which accepts a list of item
dictionaries and delivers the notification through its channel.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseNotifier(ABC):
    """
    Interface that every notifier must implement.

    Parameters
    ----------
    settings : Any
        The application ``Settings`` object (or a subset of it).
    """

    def __init__(self, settings: Any) -> None:
        self.settings = settings

    @abstractmethod
    def send(self, items: list[dict]) -> None:
        """
        Deliver one or more items through this notification channel.

        Parameters
        ----------
        items : list[dict]
            Each dict contains at minimum:
            ``id``, ``title``, ``url``, ``description``.
        """
        ...
