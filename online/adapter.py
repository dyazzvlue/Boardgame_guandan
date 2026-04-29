"""
GuanDan/online/adapter.py
AbstractGame 子类，集成 gameplatform。
"""
from __future__ import annotations
import sys, os
from typing import Any, Optional

try:
    from framework.core import AbstractGame, AbstractBridge
except ImportError as _e:
    raise ImportError(f"需要 gameplatform 框架: {_e}")

_GD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PARENT = os.path.dirname(_GD_DIR)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from GuanDan.game import Game
from GuanDan.card import Card
from GuanDan.ai import GuandanAI
from GuanDan.rules import Play, classify_hand, can_beat
from GuanDan.constants import rank_order
from .state import serialize


class _OnlineBridge:
    def __init__(self, ab, game_ref, ais):
        self._b = ab
        self._game_ref = game_ref
        self._ais = ais

    @property
    def _game(self): return self._game_ref[0]

    def ask_play(self, pi, hand, lp, vp):
        ai = self._ais.get(pi)
        if ai:
            return ai.decide_play(hand, lp, self._game.last_player_idx,
                                  self._game.finish_order, self._game.level_rank)
        self._b.broadcast_state()
        data = {"last_play": _pd(lp) if lp else None, "valid_count": len(vp)}
        resp = self._b.ask(pi, "play", data)
        if resp is None or resp == "pass": return None
        if isinstance(resp, list):
            uid_set = set(resp)
            chosen = [c for c in hand if c.uid in uid_set]
            if chosen: return chosen
        return None

    def ask_tribute(self, pi, hand, giving, con):
        ai = self._ais.get(pi)
        if ai: return ai.decide_tribute(hand, giving, self._game.level_rank, con)
        self._b.broadcast_state()
        kind = "tribute_give" if giving else "tribute_return"
        resp = self._b.ask(pi, kind, con)
        if isinstance(resp, int):
            for c in hand:
                if c.uid == resp: return c
        tmp = GuandanAI(pi)
        return tmp.decide_tribute(hand, giving, self._game.level_rank, con)

    def log(self, t, s="normal"): self._b.log(t, s)
    def broadcast_state(self): self._b.broadcast_state()
    def broadcast_game_over(self, r): self._b.broadcast_game_over(r)


class GuandanGame(AbstractGame):
    GAME_ID = "guandan"
    GAME_NAME = "掼蛋"
    MIN_PLAYERS = 4
    MAX_PLAYERS = 4

    def __init__(self):
        self.game = None
        self._ais = {}
        self._game_ref = [None]

    def setup(self, player_names, human_flags):
        self._ais = {i: GuandanAI(i) for i, h in enumerate(human_flags) if not h}
        ob = _OnlineBridge(self.bridge, self._game_ref, self._ais)
        self.game = Game(ob)
        self._game_ref[0] = self.game
        self.game.init_players(player_names, human_flags)

    def run(self):
        self.game.run()

    def get_state(self):
        if not self.game: return {}
        return serialize(self.game)

    def on_player_disconnected(self, pi):
        if self.game and pi < len(self.game.players):
            self.game.players[pi].is_human = False
            self._ais[pi] = GuandanAI(pi)


def _pd(play):
    if not play: return None
    return {"hand_type": play.hand_type.value, "key_rank": play.key_rank,
            "num_cards": play.num_cards,
            "cards": [{"uid": c.uid, "rank": c.rank,
                       "suit": c.suit.value if c.suit else None} for c in play.cards]}
