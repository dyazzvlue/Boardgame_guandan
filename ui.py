"""
GuanDan/ui.py
CLI 交互桥。
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from .card import Card
from .constants import HandType, Rank, rank_order, RANK_NAMES
from .rules import Play, find_valid_plays, classify_hand

if TYPE_CHECKING:
    from .game import Game


class CLIBridge:
    def __init__(self):
        self.game = None

    def bind(self, game):
        self.game = game

    def ask_play(self, player_idx, hand, last_play, valid_plays):
        p = self.game.players[player_idx]
        lr = self.game.level_rank
        print(f"\n{'─'*50}")
        print(f"轮到 {p.name} (座位{p.idx}, {p.team.name}队)")
        self._print_hand(hand, lr)
        if last_play:
            cs = " ".join(c.display(lr) for c in last_play.cards)
            print(f"  场上: {last_play.hand_type.value} [{cs}]")
        else:
            print("  场上: 空（自由出牌）")
        if not valid_plays:
            print("  无牌可出")
            return None
        print(f"  可出 {len(valid_plays)} 种")
        while True:
            inp = input("  牌编号(空格分隔) 或 p 过牌: ").strip()
            if inp.lower() == 'p':
                if last_play is None:
                    print("  自由出牌不能过！")
                    continue
                return None
            try:
                indices = [int(x) for x in inp.split()]
            except ValueError:
                print("  请输入数字"); continue
            if not indices: continue
            if any(i < 0 or i >= len(hand) for i in indices):
                print(f"  范围: 0~{len(hand)-1}"); continue
            chosen = [hand[i] for i in indices]
            play = classify_hand(chosen, lr)
            if play is None:
                print("  非法牌型"); continue
            return chosen

    def ask_tribute(self, player_idx, hand, is_giving, constraint):
        p = self.game.players[player_idx]
        lr = self.game.level_rank
        action = "进贡" if is_giving else "还牌"
        print(f"\n{p.name} {action} (给 {constraint.get('to','?')})")
        self._print_hand(hand, lr)
        while True:
            try:
                idx = int(input("  牌编号: ").strip())
            except ValueError:
                continue
            if idx < 0 or idx >= len(hand): continue
            card = hand[idx]
            if is_giving and card.is_wild(lr):
                print("  不能贡逢人配"); continue
            if not is_giving and card.rank > 10:
                print("  还牌须<=10"); continue
            return card

    def log(self, text, style="normal"):
        pfx = {"header":"===","section":">","warning":"!","play":"*",
               "finish":"!!","tribute":"$","upgrade":"^"}.get(style," ")
        print(f"  {pfx} {text}")

    def broadcast_state(self):
        if not self.game: return
        for p in self.game.players:
            done = "done" if p.idx in self.game.finish_order else f"{p.hand_count}"
            print(f"  [{p.team.name}]{p.name}:{done}", end="")
        print()

    def broadcast_game_over(self, result):
        print(f"\n{'='*50}")
        print(f"  游戏结束！{result['winner_team']} 队获胜！")
        print(f"  A:{result['level_a']} B:{result['level_b']} 共{result['rounds']}局")

    @staticmethod
    def _print_hand(hand, lr):
        print("  手牌:")
        for i, c in enumerate(hand):
            w = " [配]" if c.is_wild(lr) else ""
            print(f"    {i:2d}: {c.display(lr)}{w}")
