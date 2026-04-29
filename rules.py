"""
GuanDan/rules.py
掼蛋规则引擎 -- 牌型识别、大小比较、合法出牌枚举。
"""
from __future__ import annotations
from collections import Counter
from itertools import combinations
from typing import Optional

from .card import Card
from .constants import (
    HandType, Rank, Suit, BOMB_POWER, BOMB_TYPES,
    rank_order,
)


class Play:
    __slots__ = ("hand_type", "key_rank", "cards", "num_cards")

    def __init__(self, hand_type: HandType, key_rank: float, cards: list[Card]):
        self.hand_type = hand_type
        self.key_rank = key_rank
        self.cards = cards
        self.num_cards = len(cards)

    def __repr__(self) -> str:
        return f"Play({self.hand_type.value}, key={self.key_rank}, n={self.num_cards})"


# =====================================================================
#  1. classify_hand
# =====================================================================

def classify_hand(cards: list[Card], level_rank: int) -> Optional[Play]:
    n = len(cards)
    if n == 0:
        return None

    wilds = [c for c in cards if c.is_wild(level_rank)]
    normals = [c for c in cards if not c.is_wild(level_rank)]
    nw = len(wilds)

    # 4 王 = 火箭
    if n == 4 and all(c.is_joker for c in cards):
        return Play(HandType.ROCKET, 100, cards)

    if nw == 0:
        return _classify_no_wild(cards, level_rank)
    return _classify_with_wild(normals, wilds, cards, level_rank)


def _classify_no_wild(cards: list[Card], lr: int) -> Optional[Play]:
    n = len(cards)
    ranks = [c.rank for c in cards]
    cnt = Counter(ranks)
    unique_ranks = sorted(cnt.keys())

    if n == 1:
        return Play(HandType.SINGLE, rank_order(ranks[0], lr), cards)

    if n == 2 and len(cnt) == 1:
        return Play(HandType.PAIR, rank_order(ranks[0], lr), cards)

    if n == 3 and len(cnt) == 1:
        return Play(HandType.TRIPLE, rank_order(ranks[0], lr), cards)

    if len(cnt) == 1 and 4 <= n <= 8:
        bomb_map = {4: HandType.BOMB_4, 5: HandType.BOMB_5,
                    6: HandType.BOMB_6, 7: HandType.BOMB_7,
                    8: HandType.BOMB_8}
        return Play(bomb_map[n], rank_order(ranks[0], lr), cards)

    if n == 5 and sorted(cnt.values()) == [2, 3]:
        trio_rank = [r for r, c in cnt.items() if c == 3][0]
        return Play(HandType.TRIPLE_WITH_PAIR, rank_order(trio_rank, lr), cards)

    if n == 5 and _all_same_suit(cards) and _is_consecutive(unique_ranks, lr) and len(cnt) == 5:
        key = max(rank_order(r, lr) for r in unique_ranks)
        return Play(HandType.FLUSH_STRAIGHT, key, cards)

    if n == 5 and _is_consecutive(unique_ranks, lr) and len(cnt) == 5:
        key = max(rank_order(r, lr) for r in unique_ranks)
        return Play(HandType.STRAIGHT, key, cards)

    if n >= 6 and n % 2 == 0 and all(v == 2 for v in cnt.values()):
        if _is_consecutive(unique_ranks, lr):
            key = max(rank_order(r, lr) for r in unique_ranks)
            return Play(HandType.CONSECUTIVE_PAIRS, key, cards)

    if n >= 6 and n % 3 == 0 and all(v == 3 for v in cnt.values()):
        if _is_consecutive(unique_ranks, lr):
            key = max(rank_order(r, lr) for r in unique_ranks)
            return Play(HandType.CONSECUTIVE_TRIPLES, key, cards)

    return None


def _classify_with_wild(normals, wilds, all_cards, lr):
    n = len(all_cards)
    nw = len(wilds)
    normal_ranks = [c.rank for c in normals]
    cnt = Counter(normal_ranks)

    # 炸弹：所有普通牌同点 + wild
    if len(cnt) <= 1 and 4 <= n <= 8:
        base_rank = list(cnt.keys())[0] if cnt else lr
        bomb_map = {4: HandType.BOMB_4, 5: HandType.BOMB_5,
                    6: HandType.BOMB_6, 7: HandType.BOMB_7,
                    8: HandType.BOMB_8}
        bt = bomb_map.get(n)
        if bt:
            return Play(bt, rank_order(base_rank, lr), all_cards)

    # 同花顺 (5张)
    if n == 5:
        r = _try_flush_straight_wild(normals, nw, lr, all_cards)
        if r: return r

    # 单牌
    if n == 1:
        return Play(HandType.SINGLE, rank_order(lr, lr), all_cards)

    # 对子
    if n == 2:
        base = normal_ranks[0] if normal_ranks else lr
        return Play(HandType.PAIR, rank_order(base, lr), all_cards)

    # 三同张
    if n == 3 and len(set(normal_ranks)) <= 1:
        base = normal_ranks[0] if normal_ranks else lr
        return Play(HandType.TRIPLE, rank_order(base, lr), all_cards)

    # 三带二
    if n == 5:
        r = _try_triple_with_pair_wild(normals, nw, lr, all_cards)
        if r: return r

    # 顺子
    if n == 5:
        r = _try_straight_wild(normals, nw, lr, all_cards)
        if r: return r

    # 连对
    if n >= 6 and n % 2 == 0:
        r = _try_consecutive_pairs_wild(normals, nw, n, lr, all_cards)
        if r: return r

    # 钢板
    if n >= 6 and n % 3 == 0:
        r = _try_consecutive_triples_wild(normals, nw, n, lr, all_cards)
        if r: return r

    return None


# -- helpers --

def _all_same_suit(cards):
    suits = {c.suit for c in cards if c.suit is not None}
    return len(suits) == 1

def _is_consecutive(ranks, lr):
    if any(r >= Rank.JOKER_SMALL for r in ranks):
        return False
    sr = sorted(ranks)
    if sr[-1] - sr[0] == len(sr) - 1:
        return True
    if Rank.ACE in ranks:
        low = sorted([1 if r == Rank.ACE else r for r in ranks])
        if low[-1] - low[0] == len(low) - 1:
            return True
    return False


def _try_flush_straight_wild(normals, nw, lr, all_cards):
    if not normals:
        return None
    suits = {c.suit for c in normals}
    if len(suits) != 1:
        return None
    normal_ranks = sorted(set(c.rank for c in normals))
    seq = _consecutive_with_gaps(normal_ranks, 5, nw)
    if seq:
        key = max(rank_order(r, lr) for r in seq)
        return Play(HandType.FLUSH_STRAIGHT, key, all_cards)
    return None


def _try_straight_wild(normals, nw, lr, all_cards):
    normal_ranks = [c.rank for c in normals]
    if any(r >= Rank.JOKER_SMALL for r in normal_ranks):
        return None
    unique = sorted(set(normal_ranks))
    if len(normal_ranks) != len(unique):
        return None
    seq = _consecutive_with_gaps(unique, 5, nw)
    if seq:
        key = max(rank_order(r, lr) for r in seq)
        return Play(HandType.STRAIGHT, key, all_cards)
    return None


def _try_triple_with_pair_wild(normals, nw, lr, all_cards):
    cnt = Counter(c.rank for c in normals)
    nn = len(normals)
    for r_trio, c_trio in cnt.items():
        need_trio = max(0, 3 - c_trio)
        rw = nw - need_trio
        if rw < 0: continue
        actual_trio = min(c_trio, 3)
        if actual_trio + need_trio != 3: continue
        pair_normals = nn - min(c_trio, 3)
        if pair_normals + rw == 2:
            pair_ranks = [rr for rr, cc in cnt.items() if rr != r_trio for _ in range(cc)]
            if len(set(pair_ranks)) <= 1:
                return Play(HandType.TRIPLE_WITH_PAIR, rank_order(r_trio, lr), all_cards)
    return None


def _try_consecutive_pairs_wild(normals, nw, n, lr, all_cards):
    n_pairs = n // 2
    if n_pairs < 3: return None
    cnt = Counter(c.rank for c in normals)
    if any(r >= Rank.JOKER_SMALL for r in cnt): return None
    for start in range(2, 15):
        end = start + n_pairs - 1
        if end > 14: break
        seq = list(range(start, end + 1))
        wn = 0; valid = True
        for r in seq:
            have = cnt.get(r, 0)
            if have > 2: valid = False; break
            wn += (2 - have)
        extra = sum(cnt[r] for r in cnt if r not in seq)
        if valid and extra == 0 and wn <= nw:
            key = max(rank_order(r, lr) for r in seq)
            return Play(HandType.CONSECUTIVE_PAIRS, key, all_cards)
    return None


def _try_consecutive_triples_wild(normals, nw, n, lr, all_cards):
    n_trips = n // 3
    if n_trips < 2: return None
    cnt = Counter(c.rank for c in normals)
    if any(r >= Rank.JOKER_SMALL for r in cnt): return None
    for start in range(2, 15):
        end = start + n_trips - 1
        if end > 14: break
        seq = list(range(start, end + 1))
        wn = 0; valid = True
        for r in seq:
            have = cnt.get(r, 0)
            if have > 3: valid = False; break
            wn += (3 - have)
        extra = sum(cnt[r] for r in cnt if r not in seq)
        if valid and extra == 0 and wn <= nw:
            key = max(rank_order(r, lr) for r in seq)
            return Play(HandType.CONSECUTIVE_TRIPLES, key, all_cards)
    return None


def _consecutive_with_gaps(ranks, n_need, n_wild):
    if not ranks and n_wild >= n_need:
        return list(range(2, 2 + n_need))
    all_present = set(ranks)
    for start in range(2, 15):
        end = start + n_need - 1
        if end > 14: break
        seq = list(range(start, end + 1))
        gaps = sum(1 for r in seq if r not in all_present)
        extra = sum(1 for r in ranks if r not in seq)
        if extra == 0 and gaps <= n_wild:
            return seq
    # A-low: A=1,2,3,4,5
    if Rank.ACE in all_present or n_wild > 0:
        seq_raw = list(range(1, 1 + n_need))
        seq_mapped = [14 if r == 1 else r for r in seq_raw]
        if max(seq_raw) <= 14:
            gaps = sum(1 for r in seq_mapped if r not in all_present)
            extra = sum(1 for r in ranks if r not in seq_mapped)
            if extra == 0 and gaps <= n_wild:
                return sorted(seq_mapped)
    return None


# =====================================================================
#  2. can_beat
# =====================================================================

def can_beat(play: Play, last_play: Play, level_rank: int) -> bool:
    p_bomb = play.hand_type in BOMB_TYPES
    l_bomb = last_play.hand_type in BOMB_TYPES

    if p_bomb and not l_bomb: return True
    if not p_bomb and l_bomb: return False

    if p_bomb and l_bomb:
        pp = BOMB_POWER[play.hand_type]
        lp = BOMB_POWER[last_play.hand_type]
        if pp != lp: return pp > lp
        return play.key_rank > last_play.key_rank

    if play.hand_type != last_play.hand_type: return False
    if play.num_cards != last_play.num_cards: return False
    return play.key_rank > last_play.key_rank


# =====================================================================
#  3. find_valid_plays
# =====================================================================

def find_valid_plays(hand: list[Card], last_play: Optional[Play],
                     level_rank: int) -> list[Play]:
    if last_play is None:
        return _enumerate_free(hand, level_rank)
    return _enumerate_beat(hand, last_play, level_rank)


def _enumerate_beat(hand, last_play, lr):
    all_plays = _enumerate_free(hand, lr)
    return [p for p in all_plays if can_beat(p, last_play, lr)]


def _enumerate_free(hand, lr):
    results = []
    wilds = [c for c in hand if c.is_wild(lr)]
    normals = [c for c in hand if not c.is_wild(lr)]
    nw = len(wilds)
    by_rank = {}
    for c in normals:
        by_rank.setdefault(c.rank, []).append(c)

    # 单牌
    for c in hand:
        p = classify_hand([c], lr)
        if p: results.append(p)

    # 对子
    _add_pairs(results, by_rank, wilds, lr)
    # 三条
    _add_triples(results, by_rank, wilds, lr)
    # 炸弹
    _add_bombs(results, by_rank, wilds, lr)
    # 火箭
    jokers = [c for c in hand if c.is_joker]
    if len(jokers) == 4:
        results.append(Play(HandType.ROCKET, 100, jokers))
    # 三带二
    _add_triple_with_pairs(results, by_rank, wilds, lr)
    # 顺子
    _add_straights(results, by_rank, wilds, lr)
    # 同花顺
    _add_flush_straights(results, hand, wilds, lr)
    # 连对
    _add_consecutive_pairs(results, by_rank, wilds, lr)
    # 钢板
    _add_consecutive_triples(results, by_rank, wilds, lr)

    return results


def _add_pairs(results, by_rank, wilds, lr):
    for r, cards in by_rank.items():
        if len(cards) >= 2:
            for c1, c2 in combinations(cards, 2):
                results.append(Play(HandType.PAIR, rank_order(r, lr), [c1, c2]))
        if wilds and len(cards) >= 1:
            results.append(Play(HandType.PAIR, rank_order(r, lr), [cards[0], wilds[0]]))
    if len(wilds) >= 2:
        results.append(Play(HandType.PAIR, rank_order(lr, lr), list(wilds[:2])))


def _add_triples(results, by_rank, wilds, lr):
    for r, cards in by_rank.items():
        if len(cards) >= 3:
            for combo in combinations(cards, 3):
                results.append(Play(HandType.TRIPLE, rank_order(r, lr), list(combo)))
        if len(wilds) >= 1 and len(cards) >= 2:
            for c1, c2 in combinations(cards, 2):
                results.append(Play(HandType.TRIPLE, rank_order(r, lr), [c1, c2, wilds[0]]))
        if len(wilds) >= 2 and len(cards) >= 1:
            results.append(Play(HandType.TRIPLE, rank_order(r, lr), [cards[0]] + list(wilds[:2])))


def _add_bombs(results, by_rank, wilds, lr):
    nw = len(wilds)
    bomb_map = {4: HandType.BOMB_4, 5: HandType.BOMB_5,
                6: HandType.BOMB_6, 7: HandType.BOMB_7,
                8: HandType.BOMB_8}
    for r, cards in by_rank.items():
        nc = len(cards)
        for size in range(4, min(nc, 8) + 1):
            for combo in combinations(cards, size):
                results.append(Play(bomb_map[size], rank_order(r, lr), list(combo)))
        for w_use in range(1, nw + 1):
            total = nc + w_use
            if 4 <= total <= 8:
                bt = bomb_map[total]
                results.append(Play(bt, rank_order(r, lr), cards + list(wilds[:w_use])))


def _add_triple_with_pairs(results, by_rank, wilds, lr):
    nw = len(wilds)
    all_ranks = sorted(by_rank.keys())
    for r_trio in all_ranks:
        ct = by_rank[r_trio]
        for w_trio in range(max(0, 3 - len(ct)), min(nw, 3) + 1):
            actual = min(len(ct), 3)
            if actual + w_trio != 3: continue
            trio_cards = ct[:actual] + list(wilds[:w_trio])
            rw = nw - w_trio
            for r_pair in all_ranks:
                if r_pair == r_trio: continue
                cp = by_rank[r_pair]
                for w_pair in range(max(0, 2 - len(cp)), min(rw, 2) + 1):
                    ap = min(len(cp), 2)
                    if ap + w_pair != 2: continue
                    pair_cards = cp[:ap] + list(wilds[w_trio:w_trio + w_pair])
                    results.append(Play(HandType.TRIPLE_WITH_PAIR,
                                        rank_order(r_trio, lr),
                                        trio_cards + pair_cards))
            if rw >= 2 and w_trio == 0 and len(ct) >= 3:
                results.append(Play(HandType.TRIPLE_WITH_PAIR,
                                    rank_order(r_trio, lr),
                                    ct[:3] + list(wilds[:2])))


def _add_straights(results, by_rank, wilds, lr):
    nw = len(wilds)
    for start in range(2, 11):
        seq = list(range(start, start + 5))
        cards_chosen = []
        wn = 0
        for r in seq:
            if r in by_rank and by_rank[r]:
                cards_chosen.append(by_rank[r][0])
            else:
                wn += 1
        if wn > nw: continue
        if len(cards_chosen) + wn != 5: continue
        if any(c.rank >= Rank.JOKER_SMALL for c in cards_chosen): continue
        key = max(rank_order(r, lr) for r in seq)
        results.append(Play(HandType.STRAIGHT, key, cards_chosen + list(wilds[:wn])))
    # A-2-3-4-5
    seq_low = [14, 2, 3, 4, 5]
    cards_chosen = []
    wn = 0
    for r in seq_low:
        if r in by_rank and by_rank[r]:
            cards_chosen.append(by_rank[r][0])
        else:
            wn += 1
    if wn <= nw and len(cards_chosen) + wn == 5:
        key = rank_order(5, lr)
        results.append(Play(HandType.STRAIGHT, key, cards_chosen + list(wilds[:wn])))


def _add_flush_straights(results, hand, wilds, lr):
    nw = len(wilds)
    by_suit = {}
    for c in hand:
        if c.is_wild(lr) or c.is_joker: continue
        by_suit.setdefault(c.suit, {})[c.rank] = c
    for suit, rm in by_suit.items():
        for start in range(2, 11):
            seq = list(range(start, start + 5))
            cc = []; wn = 0
            for r in seq:
                if r in rm: cc.append(rm[r])
                else: wn += 1
            if wn <= nw and len(cc) + wn == 5:
                key = max(rank_order(r, lr) for r in seq)
                results.append(Play(HandType.FLUSH_STRAIGHT, key, cc + list(wilds[:wn])))
        # A-low
        seq_low = [14, 2, 3, 4, 5]
        cc = []; wn = 0
        for r in seq_low:
            if r in rm: cc.append(rm[r])
            else: wn += 1
        if wn <= nw and len(cc) + wn == 5:
            key = rank_order(5, lr)
            results.append(Play(HandType.FLUSH_STRAIGHT, key, cc + list(wilds[:wn])))


def _add_consecutive_pairs(results, by_rank, wilds, lr):
    nw = len(wilds)
    for n_pairs in range(3, 11):
        for start in range(2, 15):
            end = start + n_pairs - 1
            if end > 14: break
            seq = list(range(start, end + 1))
            cc = []; wn = 0; valid = True
            for r in seq:
                have = by_rank.get(r, [])
                if len(have) >= 2: cc.extend(have[:2])
                elif len(have) == 1: cc.append(have[0]); wn += 1
                else: wn += 2
            if wn <= nw and valid:
                key = max(rank_order(r, lr) for r in seq)
                results.append(Play(HandType.CONSECUTIVE_PAIRS, key, cc + list(wilds[:wn])))


def _add_consecutive_triples(results, by_rank, wilds, lr):
    nw = len(wilds)
    for n_trips in range(2, 8):
        for start in range(2, 15):
            end = start + n_trips - 1
            if end > 14: break
            seq = list(range(start, end + 1))
            cc = []; wn = 0
            for r in seq:
                have = by_rank.get(r, [])
                take = min(len(have), 3)
                cc.extend(have[:take])
                wn += (3 - take)
            if wn <= nw:
                key = max(rank_order(r, lr) for r in seq)
                results.append(Play(HandType.CONSECUTIVE_TRIPLES, key, cc + list(wilds[:wn])))
