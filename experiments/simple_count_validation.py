"""How much does the human-practical simplified count cost, and how much
does it still buy you?

Two comparisons, 16,000 games each:
1. simple-count bot vs. the precise hand_strength bot -- both otherwise
   identical (signal-aware, smart discard, role-aware leads). This is the
   cost of rounding to numbers a human can actually count at the table.
2. simple-count bot vs. a "casual" bot that bids too loosely, ignores seat
   position, and ignores partner/discard/lead discipline entirely -- a
   rough stand-in for an unstudied opponent. This is what the simplified
   system is actually worth against the kind of player you meet at a table.
"""
import _pathfix  # noqa: F401

from euchre.players import Strategy
from euchre.simulate import run_games, win_rate

GAMES = 16000

SIMPLE = Strategy(name="simple", order_threshold=7, call_threshold=7, alone_threshold=9,
                   first_seat_offset=1, second_seat_offset=-1, third_seat_offset=0,
                   signal_aware=True, smart_discard=True, role_aware_lead=True, use_simple_count=True)

PRECISE = Strategy(name="precise", order_threshold=45, call_threshold=45, alone_threshold=60,
                    first_seat_offset=6, second_seat_offset=-6, third_seat_offset=2,
                    signal_aware=True, smart_discard=True, role_aware_lead=True, use_simple_count=False)

CASUAL = Strategy(name="casual", order_threshold=20, call_threshold=20, alone_threshold=30,
                   first_seat_offset=0, second_seat_offset=0, third_seat_offset=0,
                   signal_aware=False, smart_discard=False, role_aware_lead=False, use_simple_count=False)


def main() -> None:
    for label, opponent in [("precise (exact arithmetic)", PRECISE), ("casual (undisciplined)", CASUAL)]:
        strategies = [SIMPLE, opponent, SIMPLE, opponent]
        games = run_games(strategies, GAMES, seed=hash(label) % 10_000, target_score=10)
        print(f"simple-count vs. {label}:")
        print(f"  simple-count win rate: {win_rate(games, 0):.1%}")
        print(f"  {opponent.name:9s} win rate: {win_rate(games, 1):.1%}")
        print()


if __name__ == "__main__":
    main()
