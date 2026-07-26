"""Batch simulation helpers used by the CLI and by experiments/."""
from __future__ import annotations

import random

from .engine import GameResult, HandResult, play_game, play_hand, team_of
from .players import HeuristicPlayer, Strategy


def make_players(strategies: list[Strategy]) -> list[HeuristicPlayer]:
    assert len(strategies) == 4
    return [HeuristicPlayer(s) for s in strategies]


def run_hands(strategies: list[Strategy], num_hands: int, seed: int = 0,
              stick_the_dealer: bool = True) -> list[HandResult]:
    """Play independent hands (dealer rotating 0,1,2,3,...) without tracking a
    running game score. Useful for hand-level questions (bidding position,
    going-alone EV, trump thresholds) where game-to-10 framing isn't needed."""
    rng = random.Random(seed)
    players = make_players(strategies)
    results = []
    dealer = 0
    while len(results) < num_hands:
        r = play_hand(players, dealer, rng, stick_the_dealer=stick_the_dealer)
        if not r.redeal:
            results.append(r)
        dealer = (dealer + 1) % 4
    return results


def run_games(strategies: list[Strategy], num_games: int, seed: int = 0,
              target_score: int = 10, stick_the_dealer: bool = True) -> list[GameResult]:
    """Play full games to `target_score`, rotating the starting dealer each
    game so no seat is systematically favored across the batch. Useful for
    head-to-head win-rate comparisons between two strategy sets."""
    rng = random.Random(seed)
    players = make_players(strategies)
    results = []
    for i in range(num_games):
        starting_dealer = i % 4
        results.append(play_game(players, rng, target_score=target_score,
                                  stick_the_dealer=stick_the_dealer,
                                  starting_dealer=starting_dealer))
    return results


def win_rate(games: list[GameResult], team: int) -> float:
    return sum(1 for g in games if g.winner_team == team) / len(games)


def points_per_hand(hands: list[HandResult], team: int) -> float:
    return sum(h.points[team] for h in hands) / len(hands)
