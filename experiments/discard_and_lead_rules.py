"""How much do the sourced discard and leading rules matter on their own?

Bidding strategy (order/call/alone thresholds, position offsets,
signal_aware) is held identical for every team here -- the only things that
vary are smart_discard (guarded-honor / void-building pickup discard) and
role_aware_lead (maker leads trump, defender doesn't). Team B is always the
fully naive baseline (both False, i.e. pre-source behavior); Team A cycles
through all four combinations, isolating each rule's individual contribution
and any interaction between them.
"""
import _pathfix  # noqa: F401

from euchre.players import Strategy
from euchre.simulate import run_games, win_rate

GAMES = 16000
BASELINE = dict(order_threshold=45, call_threshold=45, alone_threshold=60, signal_aware=True)


def main() -> None:
    combos = [
        (False, False, "naive (baseline behavior)"),
        (True, False, "smart_discard only"),
        (False, True, "role_aware_lead only"),
        (True, True, "both (fully sourced)"),
    ]
    print(f"{'variant':28s} {'A win rate':>11s} {'A pts/hand':>11s} {'A euchred|maker':>16s}")
    for smart_discard, role_aware_lead, label in combos:
        team_a = Strategy(name="A", smart_discard=smart_discard, role_aware_lead=role_aware_lead, **BASELINE)
        team_b = Strategy(name="B", smart_discard=False, role_aware_lead=False, **BASELINE)
        strategies = [team_a, team_b, team_a, team_b]
        seed = smart_discard * 2 + role_aware_lead + 1
        games = run_games(strategies, GAMES, seed=seed, target_score=10)
        hands = [h for g in games for h in g.hands]
        a_pts = sum(h.points[0] for h in hands) / len(hands)
        a_maker = [h for h in hands if h.maker_team == 0]
        euchred = sum(1 for h in a_maker if h.euchred) / len(a_maker) if a_maker else 0.0
        print(f"{label:28s} {win_rate(games, 0):>10.1%} {a_pts:>11.3f} {euchred:>15.1%}")


if __name__ == "__main__":
    main()
