"""Card representation and trump-aware comparisons for euchre."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import random

RANKS = ["9", "10", "J", "Q", "K", "A"]
SUITS = ["S", "H", "D", "C"]  # spades, hearts, diamonds, clubs
RED_SUITS = {"H", "D"}
BLACK_SUITS = {"S", "C"}

_SUIT_PARTNER = {"S": "C", "C": "S", "H": "D", "D": "H"}
_OFFSUIT_RANK_ORDER = {r: i for i, r in enumerate(["9", "10", "J", "Q", "K", "A"])}
_TRUMP_NONBOWER_ORDER = {"9": 1, "10": 2, "Q": 3, "K": 4, "A": 5}


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    def __repr__(self) -> str:
        return f"{self.rank}{self.suit}"

    def is_right_bower(self, trump: str) -> bool:
        return self.rank == "J" and self.suit == trump

    def is_left_bower(self, trump: str) -> bool:
        return self.rank == "J" and self.suit == _SUIT_PARTNER[trump]

    def effective_suit(self, trump: str) -> str:
        """The suit this card counts as, given trump (left bower counts as trump)."""
        if self.is_left_bower(trump):
            return trump
        return self.suit

    def is_trump(self, trump: str) -> bool:
        return self.effective_suit(trump) == trump

    def strength(self, trump: str, led_suit: str | None = None) -> tuple[int, int]:
        """Comparable strength as (tier, rank). Higher wins. tier 2=trump,
        1=follows led suit, 0=neither (can never win the trick)."""
        eff = self.effective_suit(trump)
        if eff == trump:
            if self.is_right_bower(trump):
                r = 7
            elif self.is_left_bower(trump):
                r = 6
            else:
                r = _TRUMP_NONBOWER_ORDER[self.rank]
            return (2, r)
        if led_suit is not None and eff == led_suit:
            return (1, _OFFSUIT_RANK_ORDER[self.rank])
        return (0, 0)


def left_bower_suit(trump: str) -> str:
    return _SUIT_PARTNER[trump]


def full_deck() -> list[Card]:
    return [Card(r, s) for s, r in product(SUITS, RANKS)]


def new_shuffled_deck(rng: random.Random) -> list[Card]:
    deck = full_deck()
    rng.shuffle(deck)
    return deck
