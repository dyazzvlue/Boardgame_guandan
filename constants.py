"""
GuanDan/constants.py
掼蛋核心常量、枚举、牌面排序。
"""
from __future__ import annotations
from enum import Enum, IntEnum


class Suit(str, Enum):
    SPADES   = "♠"
    HEARTS   = "♥"
    DIAMONDS = "♦"
    CLUBS    = "♣"


class Rank(IntEnum):
    TWO   = 2
    THREE = 3
    FOUR  = 4
    FIVE  = 5
    SIX   = 6
    SEVEN = 7
    EIGHT = 8
    NINE  = 9
    TEN   = 10
    JACK  = 11
    QUEEN = 12
    KING  = 13
    ACE   = 14
    JOKER_SMALL = 15
    JOKER_BIG   = 16


RANK_NAMES: dict[int, str] = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8",
    9: "9", 10: "10", 11: "J", 12: "Q", 13: "K", 14: "A",
    15: "小王", 16: "大王",
}


class HandType(str, Enum):
    SINGLE             = "single"
    PAIR               = "pair"
    TRIPLE             = "triple"
    TRIPLE_WITH_PAIR   = "triple_with_pair"
    STRAIGHT           = "straight"
    CONSECUTIVE_PAIRS  = "consecutive_pairs"
    CONSECUTIVE_TRIPLES = "consecutive_triples"
    BOMB_4             = "bomb_4"
    BOMB_5             = "bomb_5"
    BOMB_6             = "bomb_6"
    BOMB_7             = "bomb_7"
    BOMB_8             = "bomb_8"
    FLUSH_STRAIGHT     = "flush_straight"
    ROCKET             = "rocket"


class Team(IntEnum):
    A = 0
    B = 1


def player_team(seat: int) -> Team:
    return Team.A if seat % 2 == 0 else Team.B


def teammate(seat: int) -> int:
    return (seat + 2) % 4


BOMB_POWER: dict[HandType, int] = {
    HandType.BOMB_4:         1,
    HandType.BOMB_5:         2,
    HandType.FLUSH_STRAIGHT: 3,
    HandType.BOMB_6:         4,
    HandType.BOMB_7:         5,
    HandType.BOMB_8:         6,
    HandType.ROCKET:         7,
}

BOMB_TYPES = frozenset(BOMB_POWER.keys())

LEVEL_SEQUENCE = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]


def next_level(current: int, steps: int) -> tuple[int, bool]:
    idx = LEVEL_SEQUENCE.index(current)
    new_idx = idx + steps
    if new_idx >= len(LEVEL_SEQUENCE) - 1:
        return Rank.ACE, True
    return LEVEL_SEQUENCE[new_idx], False


def rank_order(rank: int, level_rank: int) -> int:
    if rank == Rank.JOKER_BIG:
        return 100
    if rank == Rank.JOKER_SMALL:
        return 99
    if rank == level_rank and rank <= Rank.ACE:
        return 50
    return rank
