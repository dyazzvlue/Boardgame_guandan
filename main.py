"""
GuanDan/main.py
CLI 入口。
"""
from __future__ import annotations
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from GuanDan.game import Game
from GuanDan.ai import GuandanAI
from GuanDan.ui import CLIBridge
from GuanDan.card import Card
from GuanDan.rules import Play
from typing import Optional


class AIBridge:
    def __init__(self, ais):
        self.ais = ais
        self.game = None
    def bind(self, game):
        self.game = game
    def ask_play(self, pi, hand, lp, vp):
        ai = self.ais.get(pi)
        if not ai: return None
        return ai.decide_play(hand, lp, self.game.last_player_idx,
                              self.game.finish_order, self.game.level_rank)
    def ask_tribute(self, pi, hand, giving, con):
        ai = self.ais.get(pi)
        if ai: return ai.decide_tribute(hand, giving, self.game.level_rank, con)
        return hand[0]
    def log(self, text, style="normal"):
        print(f"  [{style}] {text}")
    def broadcast_state(self): pass
    def broadcast_game_over(self, r):
        print(f"\n游戏结束！{r['winner_team']} 队获胜！")


class HybridBridge:
    def __init__(self, humans, ais):
        self.humans = humans
        self.ais = ais
        self.cli = CLIBridge()
        self.game = None
    def bind(self, game):
        self.game = game; self.cli.bind(game)
    def ask_play(self, pi, hand, lp, vp):
        if pi in self.humans: return self.cli.ask_play(pi, hand, lp, vp)
        ai = self.ais.get(pi)
        if ai: return ai.decide_play(hand, lp, self.game.last_player_idx,
                                     self.game.finish_order, self.game.level_rank)
        return None
    def ask_tribute(self, pi, hand, giving, con):
        if pi in self.humans: return self.cli.ask_tribute(pi, hand, giving, con)
        ai = self.ais.get(pi)
        if ai: return ai.decide_tribute(hand, giving, self.game.level_rank, con)
        return hand[0]
    def log(self, t, s="normal"): self.cli.log(t, s)
    def broadcast_state(self): self.cli.broadcast_state()
    def broadcast_game_over(self, r): self.cli.broadcast_game_over(r)


def main():
    ap = argparse.ArgumentParser(description="掼蛋")
    ap.add_argument("--ai-count", type=int, default=3)
    ap.add_argument("--names", nargs=4, default=["玩家","东AI","北AI","西AI"])
    args = ap.parse_args()

    ai_count = max(0, min(4, args.ai_count))
    hf = [True]*(4-ai_count) + [False]*ai_count
    ais = {i: GuandanAI(i) for i in range(4) if not hf[i]}

    if ai_count == 4:
        bridge = AIBridge(ais)
    elif ai_count == 0:
        bridge = CLIBridge()
    else:
        bridge = HybridBridge({i for i in range(4) if hf[i]}, ais)

    game = Game(bridge)
    game.init_players(args.names, hf)
    bridge.bind(game)

    print("=" * 40)
    print("        掼  蛋")
    print("=" * 40)
    for p in game.players:
        lb = "人" if p.is_human else "AI"
        print(f"  座{p.idx} [{p.team.name}] {p.name} ({lb})")
    print()
    game.run()

if __name__ == "__main__":
    main()
