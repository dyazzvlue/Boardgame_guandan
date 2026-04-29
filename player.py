"""
GuanDan/player.py
玩家状态。
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from .constants import Team, player_team

if TYPE_CHECKING:
    from .card import Card


class Player:
    __slots__ = ("name", "idx", "team", "hand", "is_human")

    def __init__(self, name: str, idx: int, is_human: bool = True) -> None:
        self.name = name
        self.idx = idx
        self.team: Team = player_team(idx)
        self.hand: list[Card] = []
        self.is_human = is_human

    def sort_hand(self, level_rank: int) -> None:
        self.hand.sort(key=lambda c: c.sort_key(level_rank))

    def remove_cards(self, cards: list[Card]) -> None:
        uids = {c.uid for c in cards}
        self.hand = [c for c in self.hand if c.uid not in uids]

    def add_cards(self, cards: list[Card]) -> None:
        self.hand.extend(cards)

    @property
    def hand_count(self) -> int:
        return len(self.hand)

    def __repr__(self) -> str:
        return f"Player({self.name!r}, idx={self.idx}, team={self.team.name}, cards={self.hand_count})"
