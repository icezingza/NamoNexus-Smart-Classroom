from abc import ABC, abstractmethod


class BaseEngine(ABC):
    name: str = "base-engine"

    @abstractmethod
    def process(self, payload: dict) -> dict:
        """Return a transformed payload."""
