"""
GuanDan/game.py
掼蛋游戏引擎 -- 发牌、出牌循环、贡牌、升级。
"""
from __future__ import annotations
import random
try:
    from typing import Optional, Protocol, Any
except ImportError:
    from typing import Optional, Any
    from typing_extensions import Protocol

from .card import Card, Deck
from .constants import (
    HandType, Rank, Suit, Team,
    LEVEL_SEQUENCE, BOMB_TYPES,
    player_team, teammate, next_level, rank_order,
)
from .player import Player
from .rules import Play, classify_hand, can_beat, find_valid_plays


class GameBridge(Protocol):
    def ask_play(self, player_idx: int, hand: list[Card],
                 last_play: Optional[Play], valid_plays: list[Play]) -> Optional[list[Card]]: ...
    def ask_tribute(self, player_idx: int, hand: list[Card],
                    is_giving: bool, constraint: dict) -> Card: ...
    def log(self, text: str, style: str = "normal") -> None: ...
    def broadcast_state(self) -> None: ...
    def broadcast_game_over(self, result: dict) -> None: ...


class Game:
    def __init__(self, bridge: GameBridge) -> None:
        self.bridge = bridge
        self.players: list[Player] = []
        self.level: dict[Team, int] = {Team.A: 2, Team.B: 2}
        self.deck: Optional[Deck] = None
        self.current_idx: int = 0
        self.last_play: Optional[Play] = None
        self.last_player_idx: int = -1
        self.pass_count: int = 0
        self.finish_order: list[int] = []
        self.player_last_action: dict = {}  # idx -> {type:'play'|'pass', play:Play|None, cards:[Card]}
        self.round_num: int = 0
        self.phase: str = ""
        self.prev_finish_order: list[int] = []
        self.game_over: bool = False
        self.winner_team: Optional[Team] = None

    @property
    def level_rank(self) -> int:
        return min(self.level[Team.A], self.level[Team.B])

    def init_players(self, names, human_flags):
        self.players = [Player(n, i, h) for i, (n, h) in enumerate(zip(names, human_flags))]

    def deal(self):
        self.deck = Deck()
        self.deck.shuffle()
        for p in self.players:
            p.hand = self.deck.deal(27)
            p.sort_hand(self.level_rank)

    def run(self):
        while not self.game_over:
            self.round_num += 1
            lr = self.level_rank
            from .constants import RANK_NAMES
            self.bridge.log(
                f"=== 第 {self.round_num} 局 === 级牌: {RANK_NAMES.get(lr, lr)}"
                f"  A队:{self.level[Team.A]}  B队:{self.level[Team.B]}", "header")
            self.deal()
            if self.round_num > 1 and self.prev_finish_order:
                self._tribute_phase()
            first = self._determine_first()
            self.bridge.log(f"由 {self.players[first].name} 先出牌", "section")
            self._play_round(first)
            self._upgrade_phase()
            self.prev_finish_order = list(self.finish_order)
        result = {
            "winner_team": self.winner_team.name if self.winner_team is not None else "",
            "level_a": self.level[Team.A],
            "level_b": self.level[Team.B],
            "rounds": self.round_num,
        }
        self.bridge.log(f"** {self.winner_team.name} 队获胜！**", "header")
        self.bridge.broadcast_game_over(result)

    def _determine_first(self):
        if self.round_num == 1:
            return random.randint(0, 3)
        if self.prev_finish_order:
            return self.prev_finish_order[-1]
        return 0

    def _play_round(self, first_idx):
        self.phase = "play"
        self.finish_order = []
        self.current_idx = first_idx
        self.last_play = None
        self.last_player_idx = -1
        self.pass_count = 0
        self.player_last_action = {}
        self.bridge.broadcast_state()

        while len(self.finish_order) < 3:
            p = self.players[self.current_idx]
            if self.current_idx in self.finish_order:
                self.current_idx = (self.current_idx + 1) % 4
                continue

            is_free = (self.last_player_idx == self.current_idx) or (self.last_play is None)
            if is_free:
                self.last_play = None
                self.pass_count = 0
                self.player_last_action = {}

            valid = find_valid_plays(p.hand, self.last_play, self.level_rank)
            chosen = self.bridge.ask_play(self.current_idx, p.hand, self.last_play, valid)

            if chosen is None or len(chosen) == 0:
                if is_free:
                    # Must play -- pick smallest valid
                    if valid:
                        valid.sort(key=lambda x: (x.num_cards, x.key_rank))
                        chosen = valid[0].cards
                    else:
                        chosen = [p.hand[0]]

            if chosen is None or len(chosen) == 0:
                # PASS
                self.bridge.log(f"{p.name}: 过", "normal")
                self.player_last_action[self.current_idx] = {"type": "pass"}
                self.pass_count += 1
                active_others = [i for i in range(4)
                                 if i != self.last_player_idx and i not in self.finish_order]
                if self.pass_count >= len(active_others):
                    self.current_idx = self.last_player_idx
                    self.last_play = None
                    self.pass_count = 0
                    self.player_last_action = {}
                    continue
            else:
                play = classify_hand(chosen, self.level_rank)
                if play is None:
                    # Invalid play -- force valid or treat as pass
                    if is_free and valid:
                        valid.sort(key=lambda x: (x.num_cards, x.key_rank))
                        chosen = valid[0].cards
                        play = valid[0]
                    else:
                        # Treat as pass (or force smallest on free turn)
                        if is_free:
                            chosen = [p.hand[0]]
                            play = classify_hand(chosen, self.level_rank)
                            if play is None:
                                # Absolute fallback: just play a single
                                from .rules import Play as _P
                                play = _P(HandType.SINGLE, rank_order(chosen[0].rank, self.level_rank), chosen, 1)
                        else:
                            self.bridge.log(f"{p.name}: 过", "normal")
                            self.player_last_action[self.current_idx] = {"type": "pass"}
                            self.pass_count += 1
                            active_others = [i for i in range(4)
                                             if i != self.last_player_idx and i not in self.finish_order]
                            if self.pass_count >= len(active_others):
                                self.current_idx = self.last_player_idx
                                self.last_play = None
                                self.pass_count = 0
                                self.player_last_action = {}
                            else:
                                self.current_idx = (self.current_idx + 1) % 4
                            self.bridge.broadcast_state()
                            continue

                if self.last_play and not can_beat(play, self.last_play, self.level_rank):
                    # Can't beat -- treat as pass
                    self.bridge.log(f"{p.name}: 过", "normal")
                    self.player_last_action[self.current_idx] = {"type": "pass"}
                    self.pass_count += 1
                    active_others = [i for i in range(4)
                                     if i != self.last_player_idx and i not in self.finish_order]
                    if self.pass_count >= len(active_others):
                        self.current_idx = self.last_player_idx
                        self.last_play = None
                        self.pass_count = 0
                        self.player_last_action = {}
                        continue
                else:
                    p.remove_cards(chosen)
                    self.last_play = play
                    self.last_player_idx = self.current_idx
                    self.pass_count = 0
                    card_str = " ".join(c.display(self.level_rank) for c in chosen)
                    self.player_last_action[self.current_idx] = {"type": "play", "play": play, "cards": list(chosen)}
                    self.bridge.log(f"{p.name}: {play.hand_type.value} [{card_str}]", "play")

                    if p.hand_count == 0:
                        pos = len(self.finish_order)
                        labels = ["头游", "二游", "三游"]
                        self.finish_order.append(self.current_idx)
                        self.bridge.log(f"{p.name} {labels[pos]}！", "finish")

                        if len(self.finish_order) >= 3:
                            last_man = [i for i in range(4) if i not in self.finish_order][0]
                            self.finish_order.append(last_man)
                            self.bridge.log(f"{self.players[last_man].name} 末游", "finish")
                            break

                        mate = teammate(self.current_idx)
                        if mate not in self.finish_order:
                            self.current_idx = mate
                            self.last_play = None
                            self.pass_count = 0
                            self.bridge.log(f"对家 {self.players[mate].name} 接风", "section")
                            self.bridge.broadcast_state()
                            continue

            self.bridge.broadcast_state()
            self.current_idx = (self.current_idx + 1) % 4

    def _tribute_phase(self):
        self.phase = "tribute"
        fo = self.prev_finish_order
        winner_idx = fo[0]
        loser_idx = fo[-1]
        winner_team = player_team(winner_idx)
        loser_team = player_team(loser_idx)

        second_loser = fo[-2] if len(fo) >= 4 else None
        is_double_down = (second_loser is not None and
                          player_team(second_loser) == loser_team and
                          second_loser != winner_idx)

        big_jokers = [c for c in self.players[loser_idx].hand if c.rank == Rank.JOKER_BIG]
        if len(big_jokers) >= 2:
            self.bridge.log(f"{self.players[loser_idx].name} 双大王抗贡！", "section")
            self.bridge.broadcast_state()
            return

        if is_double_down:
            second_winner = fo[1]
            self._do_tribute(loser_idx, winner_idx)
            self._do_tribute(second_loser, second_winner)
        else:
            self._do_tribute(loser_idx, winner_idx)
        self.bridge.broadcast_state()

    def _do_tribute(self, giver_idx, receiver_idx):
        giver = self.players[giver_idx]
        receiver = self.players[receiver_idx]
        lr = self.level_rank

        # Find biggest non-wild card
        best = None; best_o = -1
        for c in giver.hand:
            if c.is_wild(lr): continue
            o = rank_order(c.rank, lr)
            if o > best_o: best_o = o; best = c
        if best is None: return

        tribute_card = self.bridge.ask_tribute(
            giver_idx, giver.hand, True,
            {"must_give": best.uid, "to": receiver.name})
        giver.remove_cards([tribute_card])
        receiver.add_cards([tribute_card])
        self.bridge.log(
            f"{giver.name} -> {receiver.name} 进贡 {tribute_card.display(lr)}", "tribute")

        return_card = self.bridge.ask_tribute(
            receiver_idx, receiver.hand, False,
            {"max_rank": 10, "to": giver.name})
        receiver.remove_cards([return_card])
        giver.add_cards([return_card])
        self.bridge.log(
            f"{receiver.name} -> {giver.name} 还牌 {return_card.display(lr)}", "tribute")
        giver.sort_hand(lr)
        receiver.sort_hand(lr)

    def _upgrade_phase(self):
        self.phase = "upgrade"
        fo = self.finish_order
        if len(fo) < 4: return

        winner_idx = fo[0]
        winner_team = player_team(winner_idx)
        last_team = player_team(fo[3])
        second_last_team = player_team(fo[2])

        if last_team != winner_team and second_last_team != winner_team:
            steps = 3; desc = "双下"
        elif last_team != winner_team:
            steps = 2; desc = "对手末游"
        else:
            steps = 1; desc = "己方末游"

        old = self.level[winner_team]
        new_lv, done = next_level(old, steps)
        self.level[winner_team] = new_lv
        from .constants import RANK_NAMES
        self.bridge.log(
            f"{winner_team.name}队 {desc} 升{steps}级: "
            f"{RANK_NAMES.get(old,old)} -> {RANK_NAMES.get(new_lv,new_lv)}", "upgrade")
        if done:
            self.game_over = True
            self.winner_team = winner_team
        self.bridge.broadcast_state()

    def get_state(self):
        lr = self.level_rank
        return {
            "phase": self.phase,
            "round_num": self.round_num,
            "level_rank": lr,
            "level": {t.name: v for t, v in self.level.items()},
            "current_idx": self.current_idx,
            "last_play": _play_to_dict(self.last_play) if self.last_play else None,
            "last_player_idx": self.last_player_idx,
            "finish_order": list(self.finish_order),
            "players": [
                {"name": p.name, "idx": p.idx, "team": p.team.name,
                 "hand_count": p.hand_count,
                 "hand": [_card_to_dict(c, lr) for c in p.hand]}
                for p in self.players
            ],
            "game_over": self.game_over,
            "winner_team": self.winner_team.name if self.winner_team else None,
        }


def _card_to_dict(card, lr):
    return {"uid": card.uid, "rank": card.rank,
            "suit": card.suit.value if card.suit else None,
            "display": card.display(lr),
            "is_wild": card.is_wild(lr), "is_joker": card.is_joker}

def _play_to_dict(play):
    return {"hand_type": play.hand_type.value, "key_rank": play.key_rank,
            "num_cards": play.num_cards,
            "cards": [{"uid": c.uid, "rank": c.rank,
                       "suit": c.suit.value if c.suit else None,
                       "display": c.display(0)} for c in play.cards]}
