"""Supported game variants."""

from enum import StrEnum


class GameType(StrEnum):
    """Installation variants supported by the game resource manifests."""

    FP = "fp"
    MD = "md"
    SE = "se"
