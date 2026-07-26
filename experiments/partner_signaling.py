"""Does simple partner-aware card play (not overtaking your own partner's
winning card) matter, holding bidding strategy identical for both teams?
"""
import _pathfix  # noqa: F401

from euchre.players import Strategy
from euchre.simulate import run_games, win_rate

GAMES = 6000
BASELINE = dict(order_threshold=45, call_threshold=45, alone_threshold=60)


def main() -> None:
    team_a = Strategy(name="A_signal_aware", signal_aware=True, **BASELINE)
    team_b = Strategy(name="B_naive", signal_aware=False, **BASELINE)
    strategies = [team_a, team_b, team_a, team_b]
    games = run_games(strategies, GAMES, seed=42, target_score=10)
    hands = [h for g in games for h in g.hands]

    a_pts = sum(h.points[0] for h in hands) / len(hands)
    b_pts = sum(h.points[1] for h in hands) / len(hands)
    a_maker = [h for h in hands if h.maker_team == 0]
    b_maker = [h for h in hands if h.maker_team == 1]
    a_euchred = sum(1 for h in a_maker if h.euchred) / len(a_maker)
    b_euchred = sum(1 for h in b_maker if h.euchred) / len(b_maker)

    print(f"{GAMES} games. Both teams bid identically (order/call=45, alone=60).")
    print("Team A ducks instead of overtaking a winning partner; Team B always plays "
          "the cheapest card that wins the trick, even over its own partner.\n")
    print(f"Team A (signal-aware) win rate: {win_rate(games, 0):.1%}   points/hand {a_pts:.3f}   "
          f"euchred as maker {a_euchred:.1%}")
    print(f"Team B (naive)        win rate: {win_rate(games, 1):.1%}   points/hand {b_pts:.3f}   "
          f"euchred as maker {b_euchred:.1%}")


if __name__ == "__main__":
    main()
