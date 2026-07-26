"""When is going alone actually worth it?

Team A's alone_threshold is swept while Team B stays at a fixed baseline.
Everything else (order/call thresholds, signal awareness) is identical, so any
win-rate movement is attributable to the alone decision alone.
"""
import _pathfix  # noqa: F401

from euchre.players import Strategy
from euchre.simulate import run_games, win_rate

GAMES_PER_POINT = 4000
BASELINE = dict(order_threshold=45, call_threshold=45, signal_aware=True)


def main() -> None:
    thresholds = [34, 38, 42, 46, 50, 54, 58, 60, 62, 66, 70, 80, 99]
    print(f"{'alone_threshold':>16s} {'A win rate':>11s} {'A pts/hand':>11s} "
          f"{'loner share':>12s} {'loner euchred':>14s}")
    for t in thresholds:
        team_a = Strategy(name="A", alone_threshold=t, **BASELINE)
        team_b = Strategy(name="B", alone_threshold=60, **BASELINE)
        strategies = [team_a, team_b, team_a, team_b]
        games = run_games(strategies, GAMES_PER_POINT, seed=t, target_score=10)
        hands = [h for g in games for h in g.hands]
        a_hands = [h for h in hands if h.maker_team == 0]
        loners = [h for h in a_hands if h.alone]
        loner_share = len(loners) / len(a_hands) if a_hands else 0.0
        loner_euchred = sum(1 for h in loners if h.euchred) / len(loners) if loners else 0.0
        a_pts = sum(h.points[0] for h in hands) / len(hands)
        label = "never" if t == 99 else str(t)
        print(f"{label:>16s} {win_rate(games, 0):>10.1%} {a_pts:>11.3f} "
              f"{loner_share:>11.1%} {loner_euchred:>13.1%}")


if __name__ == "__main__":
    main()
