"""Stateless rule helpers: legal plays, trick winners, hand evaluation, scoring."""
from __future__ import annotations

from .cards import Card, RANKS, SUITS

# Card values are anchored to the trick-win-probability estimates published
# at euchre.cards/strategy/bidding/: right bower = 1.0 trick, left bower =
# 1.0, trump ace = 0.8, trump king = 0.5, off-suit ace = 0.7, off-suit king
# = 0.3 (values x20 below to keep everything integer). Two deliberate
# departures from that source, both noted where they matter:
#
# 1. The source treats both bowers as a flat 1.0 trick, which is only true
#    standalone if you hold *both* -- a lone left bower without the right
#    can be beaten by it. We discount the left bower slightly (18 vs 20) to
#    preserve the right > left ordering used everywhere else in this engine
#    (Card.strength, trick_winner), rather than tying them.
# 2. The source doesn't give trump queen/10/9 or off-suit queen/jack/10/9;
#    those are interpolated to decay smoothly toward the bottom of each
#    tier, preserving strict rank order within a tier.
#
# Because the source numbers are real trick probabilities, NOT a "trump
# beats off-suit" scale, an off-suit ace (14) legitimately outranks a bare
# trump king... no -- it sits between trump ace and trump king (16 > 14 >
# 10): a lone off-suit ace is genuinely a better standalone trick than a
# lone low trump card. This corrects an earlier, unsourced assumption in
# this file that trump always beats off-suit card-for-card; it doesn't.
# Trump still dominates in aggregate because of TRUMP_LENGTH_BONUS below
# and because most hands hold multiple trump, not because each individual
# trump card outvalues every off-suit card.
_TRUMP_VALUE = {
    "right_bower": 20, "left_bower": 18,
    "A": 16, "K": 10, "Q": 8, "10": 4, "9": 2,
}
_OFFSUIT_VALUE = {"A": 14, "K": 6, "Q": 3, "J": 2, "10": 1, "9": 0}

# Trump *count* carries independent signal beyond the sum of individual
# card values -- the same bidding guide gates every seat's minimum bid on a
# trump-count threshold ("three trump including a bower", "two trump plus
# off-suit aces", etc.), not just a point total. This bonus captures the
# extra "control" value of a longer trump suit (more ability to draw out
# opponents' trump and keep the lead). Values are a reasonable starting
# point, not directly sourced, and are re-validated empirically in
# experiments/ rather than taken on faith.
TRUMP_LENGTH_BONUS = {0: 0, 1: 0, 2: 0, 3: 6, 4: 14, 5: 24}

_RANK_INDEX = {r: i for i, r in enumerate(RANKS)}  # 9=0 .. A=5, for tie-breaking


def rank_index(card: Card) -> int:
    """Plain rank order (9 < 10 < J < Q < K < A), independent of trump."""
    return _RANK_INDEX[card.rank]


def card_score(card: Card, trump: str) -> int:
    """Heuristic point value of a single card if `trump` is trump."""
    if card.is_right_bower(trump):
        return _TRUMP_VALUE["right_bower"]
    if card.is_left_bower(trump):
        return _TRUMP_VALUE["left_bower"]
    if card.is_trump(trump):
        return _TRUMP_VALUE[card.rank]
    return _OFFSUIT_VALUE[card.rank]


def hand_strength(hand: list[Card], trump: str) -> int:
    """Sum of per-card heuristic values plus a trump-length bonus. Used by
    bots to decide whether to order-up / call / go alone."""
    trump_count = sum(1 for c in hand if c.is_trump(trump))
    return sum(card_score(c, trump) for c in hand) + TRUMP_LENGTH_BONUS.get(trump_count, 0)


# A human-at-the-table approximation of the same idea: card_score/hand_strength
# is precise but requires exact arithmetic (e.g. "51") no one computes
# mid-hand. simple_hand_count rounds the same trick-value anchors to single
# digits so it can be counted in a few seconds: 3 for a bower, 2 for a trump
# or off-suit ace, 1 for a trump or off-suit king or a trump queen, 0 for
# everything else, plus a length bonus for extra trump. See
# experiments/simple_count_validation.py for how much win rate this costs
# relative to the precise model, and experiments/simple_count_upgrade.py for
# why the trump queen and the length-bonus curve below are worth the extra
# arithmetic: adding the trump queen (previously silently scored 0, despite
# being much closer to a king than to a 10/9) and steepening the length
# bonus for a 4th/5th trump card (it was linear, 1/2/3; the precise model's
# bonus is convex) closed roughly three-quarters of the win-rate gap to the
# precise model in a head-to-head test (44.2% -> 48.7% vs. hand_strength(),
# 10,000 games) for no added categories to memorize -- just "queen of trump
# counts like a king" and a slightly steeper bonus.
_SIMPLE_TRUMP_VALUE = {"right_bower": 3, "left_bower": 3, "A": 2, "K": 1, "Q": 1, "10": 0, "9": 0}
_SIMPLE_OFFSUIT_VALUE = {"A": 2, "K": 1, "Q": 0, "J": 0, "10": 0, "9": 0}
SIMPLE_TRUMP_LENGTH_BONUS = {0: 0, 1: 0, 2: 0, 3: 1, 4: 3, 5: 5}


def simple_card_score(card: Card, trump: str) -> int:
    if card.is_right_bower(trump):
        return _SIMPLE_TRUMP_VALUE["right_bower"]
    if card.is_left_bower(trump):
        return _SIMPLE_TRUMP_VALUE["left_bower"]
    if card.is_trump(trump):
        return _SIMPLE_TRUMP_VALUE[card.rank]
    return _SIMPLE_OFFSUIT_VALUE[card.rank]


def simple_hand_count(hand: list[Card], trump: str) -> int:
    """Count: 3 per bower, 2 per (trump-or-off-suit) ace, 1 per (trump-or-
    off-suit) king or trump queen, plus a length bonus for extra trump (+1
    for a 3rd, +3 for a 4th, +5 for a 5th). Meant to be computed by a human
    in-hand, not just by the bot."""
    trump_count = sum(1 for c in hand if c.is_trump(trump))
    return sum(simple_card_score(c, trump) for c in hand) + SIMPLE_TRUMP_LENGTH_BONUS.get(trump_count, 0)


def legal_plays(hand: list[Card], led_suit: str | None, trump: str) -> list[Card]:
    """Cards `hand` is allowed to play. Must follow the effective (bower-aware)
    led suit if able; otherwise anything is legal."""
    if led_suit is None:
        return list(hand)
    following = [c for c in hand if c.effective_suit(trump) == led_suit]
    return following if following else list(hand)


def trick_winner(plays: list[tuple[int, Card]], trump: str) -> int:
    """plays: list of (seat, card) in the order played. Returns winning seat."""
    led_suit = plays[0][1].effective_suit(trump)
    best_seat, best_card = plays[0]
    best_strength = best_card.strength(trump, led_suit)
    for seat, card in plays[1:]:
        s = card.strength(trump, led_suit)
        if s > best_strength:
            best_seat, best_card, best_strength = seat, card, s
    return best_seat


def score_hand(maker_team: int, tricks_won: dict[int, int], went_alone: bool) -> dict[int, int]:
    """tricks_won maps team id (0 or 1) -> trick count (sums to 5).
    Returns points awarded this hand, keyed by team id (0 for teams not scoring)."""
    defender_team = 1 - maker_team
    maker_tricks = tricks_won[maker_team]
    points = {0: 0, 1: 0}
    if maker_tricks < 3:
        points[defender_team] = 2  # euchred
    elif maker_tricks == 5:
        points[maker_team] = 4 if went_alone else 2  # march / loner march
    else:
        points[maker_team] = 1
    return points


def other_suits(suit: str) -> list[str]:
    return [s for s in SUITS if s != suit]
