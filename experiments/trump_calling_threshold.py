"""How much does bidding discipline (order-up / call threshold) matter?

Team A's order_threshold and call_threshold move together while Team B stays
fixed at the baseline (45). alone_threshold is held at 60 for both so the
loner decision doesn't confound this sweep.
"""
import _pathfix  # noqa: F401

from euchre.players import Strategy
from euchre.simulate import run_games, win_rate

GAMES_PER_POINT = 4000


def main() -> None:
    thresholds = [18, 26, 32, 36, 40, 43, 45, 47, 50, 54, 60, 68, 78]
    print(f"{'order/call threshold':>21s} {'A win rate':>11s} {'A pts/hand':>11s} "
          f"{'A maker share':>14s} {'A euchred|maker':>16s}")
    for t in thresholds:
        team_a = Strategy(name="A", order_threshold=t, call_threshold=t, alone_threshold=60, signal_aware=True)
        team_b = Strategy(name="B", order_threshold=45, call_threshold=45, alone_threshold=60, signal_aware=True)
        strategies = [team_a, team_b, team_a, team_b]
        games = run_games(strategies, GAMES_PER_POINT, seed=t, target_score=10)
        hands = [h for g in games for h in g.hands]
        a_pts = sum(h.points[0] for h in hands) / len(hands)
        a_maker = [h for h in hands if h.maker_team == 0]
        maker_share = len(a_maker) / len(hands)
        euchred = sum(1 for h in a_maker if h.euchred) / len(a_maker) if a_maker else 0.0
        print(f"{t:>21d} {win_rate(games, 0):>10.1%} {a_pts:>11.3f} "
              f"{maker_share:>13.1%} {euchred:>15.1%}")


if __name__ == "__main__":
    main()
