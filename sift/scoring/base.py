"""Abstract base class for pluggable quality scorers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sift.extract import Chunk


class Scorer(ABC):
    """Interface for a single quality signal that scores a code chunk.

    Implementations should be independent and side-effect free so they can be
    composed by :func:`sift.scoring.aggregate.aggregate_scores`. Higher scores
    indicate higher quality; implementations SHOULD normalize to ``0–100``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier for this signal (e.g. ``\"complexity\"``)."""

    @abstractmethod
    def score(self, chunk: Chunk) -> float:
        """Return a quality score for *chunk*.

        Args:
            chunk: Extracted function or method to evaluate.

        Returns:
            A float score, ideally in the inclusive range ``[0, 100]``.
        """
