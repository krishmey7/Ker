"""Rétrocompatibilité — consumer déplacé vers apps.game.consumers."""
from apps.game.consumers import GameRoomConsumer as CoupleRoomConsumer

__all__ = ["CoupleRoomConsumer"]
