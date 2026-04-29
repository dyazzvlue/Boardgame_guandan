"""
GuanDan/online/state.py
序列化游戏状态，隐藏其他玩家手牌。
"""
from __future__ import annotations


def serialize(game, viewer_idx=-1):
    lr = game.level_rank
    players = []
    for p in game.players:
        d = {"name": p.name, "idx": p.idx, "team": p.team.name,
             "hand_count": p.hand_count, "is_human": p.is_human}
        if p.idx == viewer_idx:
            d["hand"] = [_cd(c, lr) for c in p.hand]
        players.append(d)
    lp = None
    if game.last_play:
        lp = {"hand_type": game.last_play.hand_type.value,
              "key_rank": game.last_play.key_rank,
              "num_cards": game.last_play.num_cards,
              "cards": [_cd(c, lr) for c in game.last_play.cards],
              "player_idx": game.last_player_idx}
    return {
        "phase": game.phase, "round_num": game.round_num,
        "level_rank": lr,
        "level": {t.name: v for t, v in game.level.items()},
        "current_idx": game.current_idx,
        "last_play": lp, "last_player_idx": game.last_player_idx,
        "finish_order": list(game.finish_order),
        "players": players,
        "game_over": game.game_over,
        "winner_team": game.winner_team.name if game.winner_team else None,
    }

def _cd(card, lr):
    return {"uid": card.uid, "rank": card.rank,
            "suit": card.suit.value if card.suit else None,
            "display": card.display(lr),
            "is_wild": card.is_wild(lr), "is_joker": card.is_joker}
