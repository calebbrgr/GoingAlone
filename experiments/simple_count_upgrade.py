"""Why simple_hand_count() has a trump-queen tier and a convex length bonus
instead of the flatter version it used to have.

The old simple count (bower=3, ace=2, king=1, 0 for everything else,
length bonus +1/+2/+3 for a 3rd/4th/5th trump card) scored a trump queen as
0 -- the same as a bare 9 -- despite being much closer in real trick value
to a king. It also grew the length bonus linearly, while the precise
hand_strength() model's bonus (TRUMP_LENGTH_BONUS) is convex: a 5th trump
card is worth far more than twice a 3rd.

This script monkeypatches euchre.rules' module-level value dicts (which
simple_hand_count reads as globals at call time, so mutating them in place
changes behavior without touching players.py) to replay the old system
alongside the current one and a rejected alternative, all against the same
precise hand_strength() opponent -- the same head-to-head design as
simple_count_validation.py.
"""
import _pathfix  # noqa: F401

from euchre import rules
from euchre.players import Strategy
from euchre.simulate import run_games, win_rate

GAMES = 16000

PRECISE = Strategy(name="precise", order_threshold=45, call_threshold=45, alone_threshold=60,
                    first_seat_offset=6, second_seat_offset=-6, third_seat_offset=2,
                    signal_aware=True, smart_discard=True, role_aware_lead=True, use_simple_count=False)

# Each variant: (trump-value dict, off-suit-value dict, length-bonus dict, order/call threshold).
# alone_threshold is always order_threshold + 2, matching STRATEGY.md's gap.
VARIANTS = {
    "old (pre-upgrade: no trump-queen tier, linear length bonus)": (
        {"right_bower": 3, "left_bower": 3, "A": 2, "K": 1, "Q": 0, "10": 0, "9": 0},
        {"A": 2, "K": 1, "Q": 0, "J": 0, "10": 0, "9": 0},
        {0: 0, 1: 0, 2: 0, 3: 1, 4: 2, 5: 3},
        7,
    ),
    "current (trump queen=1, convex length bonus +1/+3/+5)": (
        {"right_bower": 3, "left_bower": 3, "A": 2, "K": 1, "Q": 1, "10": 0, "9": 0},
        {"A": 2, "K": 1, "Q": 0, "J": 0, "10": 0, "9": 0},
        {0: 0, 1: 0, 2: 0, 3: 1, 4: 3, 5: 5},
        7,
    ),
    "rejected: full 4/3/2/1 trump ladder (bower/A/K/Q all bumped a tier)": (
        {"right_bower": 4, "left_bower": 4, "A": 3, "K": 2, "Q": 1, "10": 0, "9": 0},
        {"A": 2, "K": 1, "Q": 0, "J": 0, "10": 0, "9": 0},
        {0: 0, 1: 0, 2: 0, 3: 1, 4: 3, 5: 5},
        9,
    ),
}


def main() -> None:
    for label, (trump_vals, offsuit_vals, length_bonus, threshold) in VARIANTS.items():
        rules._SIMPLE_TRUMP_VALUE.clear(); rules._SIMPLE_TRUMP_VALUE.update(trump_vals)
        rules._SIMPLE_OFFSUIT_VALUE.clear(); rules._SIMPLE_OFFSUIT_VALUE.update(offsuit_vals)
        rules.SIMPLE_TRUMP_LENGTH_BONUS.clear(); rules.SIMPLE_TRUMP_LENGTH_BONUS.update(length_bonus)

        simple = Strategy(name="simple", order_threshold=threshold, call_threshold=threshold,
                           alone_threshold=threshold + 2, first_seat_offset=1, second_seat_offset=-1,
                           third_seat_offset=0, signal_aware=True, smart_discard=True,
                           role_aware_lead=True, use_simple_count=True)
        games = run_games([simple, PRECISE, simple, PRECISE], GAMES, seed=hash(label) % 10_000, target_score=10)
        print(f"{label}:")
        print(f"  win rate vs. precise hand_strength(): {win_rate(games, 0):.1%}\n")


if __name__ == "__main__":
    main()
