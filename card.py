"""
GuanDan/card.py
Card 与 Deck 数据结构（2 副牌，108 张）。
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Optional

from .constants import Suit, Rank, rank_order, RANK_NAMES


@dataclass(frozen=True)
class Card:
    rank: int
    suit: Optional[Suit]
    uid: int

    @property
    def is_joker(self) -> bool:
        return self.rank >= Rank.JOKER_SMALL

    def is_wild(self, level_rank: int) -> bool:
        return self.rank == level_rank and self.suit == Suit.HEARTS

    def sort_key(self, level_rank: int) -> tuple:
        suit_order = {Suit.SPADES: 0, Suit.HEARTS: 1, Suit.DIAMONDS: 2, Suit.CLUBS: 3}
        return (rank_order(self.rank, level_rank), suit_order.get(self.suit, 9))

    def display(self, level_rank: int = 0) -> str:
        if self.rank == Rank.JOKER_BIG:
            return "大王"
        if self.rank == Rank.JOKER_SMALL:
            return "小王"
        name = RANK_NAMES.get(self.rank, str(self.rank))
        wild = "*" if level_rank and self.is_wild(level_rank) else ""
        return f"{self.suit.value}{name}{wild}"

    def __repr__(self) -> str:
        if self.is_joker:
            return RANK_NAMES[self.rank]
        return f"{self.suit.value}{RANK_NAMES[self.rank]}"


class Deck:
    def __init__(self) -> None:
        self._cards: list[Card] = []
        uid = 0
        for _copy in range(2):
            for suit in Suit:
                for rank_val in range(2, 15):
                    self._cards.append(Card(rank_val, suit, uid))
                    uid += 1
            self._cards.append(Card(Rank.JOKER_SMALL, None, uid)); uid += 1
            self._cards.append(Card(Rank.JOKER_BIG, None, uid)); uid += 1

    def shuffle(self) -> None:
        random.shuffle(self._cards)

    def deal(self, n: int = 27) -> list[Card]:
        hand = self._cards[:n]
        self._cards = self._cards[n:]
        return hand

    def __len__(self) -> int:
        return len(self._cards)
