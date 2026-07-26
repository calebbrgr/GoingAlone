#!/usr/bin/env python3
"""Command-line entry point for running euchre simulations.

Examples:
    python cli.py                                  # baseline vs baseline, 2000 games
    python cli.py --games 5000 --seed 7
    python cli.py --team-a-alone 18 --team-b-alone 24   # cheaper vs pickier loners
    python cli.py --team-a-order 12 --team-b-order 18   # looser vs tighter order-ups
    python cli.py --no-signal-b                    # team B ignores partner-aware ducking
"""
from __future__ import annotations

import argparse

from euchre.players import Strategy
from euchre.simulate import points_per_hand, run_games, win_rate


def build_strategies(args: argparse.Namespace) -> list[Strategy]:
    team_a = Strategy(
        name="A", order_threshold=args.team_a_order, call_threshold=args.team_a_call,
        alone_threshold=args.team_a_alone, signal_aware=not args.no_signal_a,
    )
    team_b = Strategy(
        name="B", order_threshold=args.team_b_order, call_threshold=args.team_b_call,
        alone_threshold=args.team_b_alone, signal_aware=not args.no_signal_b,
    )
    # seats 0,2 = team A ; seats 1,3 = team B
    return [team_a, team_b, team_a, team_b]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--games", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--target-score", type=int, default=10)
    p.add_argument("--no-stick-the-dealer", action="store_true")

    p.add_argument("--team-a-order", type=int, default=45)
    p.add_argument("--team-a-call", type=int, default=45)
    p.add_argument("--team-a-alone", type=int, default=60)
    p.add_argument("--no-signal-a", action="store_true")

    p.add_argument("--team-b-order", type=int, default=45)
    p.add_argument("--team-b-call", type=int, default=45)
    p.add_argument("--team-b-alone", type=int, default=60)
    p.add_argument("--no-signal-b", action="store_true")

    args = p.parse_args()
    strategies = build_strategies(args)

    games = run_games(strategies, args.games, seed=args.seed, target_score=args.target_score,
                       stick_the_dealer=not args.no_stick_the_dealer)
    hands = [h for g in games for h in g.hands]

    print(f"{args.games} games simulated (seats 0,2=Team A ; seats 1,3=Team B)")
    print(f"Team A: order>={args.team_a_order} call>={args.team_a_call} "
          f"alone>={args.team_a_alone} signal_aware={not args.no_signal_a}")
    print(f"Team B: order>={args.team_b_order} call>={args.team_b_call} "
          f"alone>={args.team_b_alone} signal_aware={not args.no_signal_b}")
    print()
    print(f"Team A win rate: {win_rate(games, 0):.1%}")
    print(f"Team B win rate: {win_rate(games, 1):.1%}")
    print(f"Team A points/hand: {points_per_hand(hands, 0):.3f}")
    print(f"Team B points/hand: {points_per_hand(hands, 1):.3f}")

    maker_hands = [h for h in hands if h.maker_seat >= 0]
    alone_calls = [h for h in maker_hands if h.alone]
    if alone_calls:
        euchred_alone = sum(1 for h in alone_calls if h.euchred)
        print(f"\nLoner calls: {len(alone_calls)} ({len(alone_calls)/len(maker_hands):.1%} of hands with a maker), "
              f"euchred {euchred_alone}/{len(alone_calls)} ({euchred_alone/len(alone_calls):.1%})")


if __name__ == "__main__":
    main()
