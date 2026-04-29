"""
GuanDan/ai.py
掼蛋中等 AI。
"""
from __future__ import annotations
import random
from typing import Optional

from .card import Card
from .constants import (
    HandType, Rank, Team, BOMB_TYPES,
    player_team, teammate, rank_order,
)
from .rules import Play, find_valid_plays, classify_hand


class GuandanAI:
    def __init__(self, player_idx: int) -> None:
        self.idx = player_idx
        self.team = player_team(player_idx)

    def decide_play(self, hand, last_play, last_player_idx, finish_order, level_rank):
        valid = find_valid_plays(hand, last_play, level_rank)
        if last_play is None:
            return self._lead(hand, valid, finish_order, level_rank)
        if last_player_idx >= 0 and player_team(last_player_idx) == self.team:
            if len(hand) > 5:
                return None
        if not valid:
            return None
        return self._follow(hand, valid, finish_order, level_rank)

    def _lead(self, hand, valid, finish_order, lr):
        if not valid:
            return [hand[0]] if hand else None
        bombs = [p for p in valid if p.hand_type in BOMB_TYPES]
        normals = [p for p in valid if p.hand_type not in BOMB_TYPES]
        if not normals:
            bombs.sort(key=lambda p: p.key_rank)
            return bombs[0].cards
        combos = [p for p in normals if p.hand_type in (
            HandType.STRAIGHT, HandType.CONSECUTIVE_PAIRS,
            HandType.CONSECUTIVE_TRIPLES, HandType.TRIPLE_WITH_PAIR,
            HandType.FLUSH_STRAIGHT)]
        if combos:
            combos.sort(key=lambda p: p.key_rank)
            return combos[0].cards
        singles = [p for p in normals if p.hand_type in (
            HandType.SINGLE, HandType.PAIR, HandType.TRIPLE)]
        if singles:
            singles.sort(key=lambda p: (p.num_cards, p.key_rank))
            return singles[0].cards
        normals.sort(key=lambda p: p.key_rank)
        return normals[0].cards

    def _follow(self, hand, valid, finish_order, lr):
        bombs = [p for p in valid if p.hand_type in BOMB_TYPES]
        normals = [p for p in valid if p.hand_type not in BOMB_TYPES]
        if normals:
            normals.sort(key=lambda p: p.key_rank)
            return normals[0].cards
        if len(hand) <= 8 and bombs:
            bombs.sort(key=lambda p: p.key_rank)
            return bombs[0].cards
        return None

    def decide_tribute(self, hand, is_giving, level_rank, constraint):
        if is_giving:
            best = None; best_o = -1
            for c in hand:
                if c.is_wild(level_rank): continue
                o = rank_order(c.rank, level_rank)
                if o > best_o: best_o = o; best = c
            return best or hand[0]
        else:
            cands = [c for c in hand if c.rank <= 10 and not c.is_wild(level_rank)]
            if cands:
                cands.sort(key=lambda c: rank_order(c.rank, level_rank))
                return cands[0]
            return hand[0]
