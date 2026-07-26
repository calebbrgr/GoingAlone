"""Heuristic euchre bots. Behavior is driven entirely by a `Strategy` of
numeric thresholds / flags, so experiments can sweep one knob at a time and
attribute win-rate differences to it."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from .cards import Card
from .rules import card_score, hand_strength, legal_plays, other_suits, rank_index, simple_hand_count

# Discount applied to a non-trump, non-honor card's discard priority for
# each card already held in its suit -- makes it cheaper to discard from a
# suit you're trimming toward a singleton (setting up a future void to ruff
# into) than to give up your only card in a suit that's already a
# singleton. Sourced from euchre.cards/strategy/common-mistakes/: "discard a
# ten from a two-card suit rather than a nine from a singleton, despite the
# ten's higher rank." Never applied to aces/kings -- those are protected as
# guarded honors regardless of suit length (see pickup_and_discard).
_VOID_BUILDING_DISCOUNT = {1: 0, 2: 3, 3: 5, 4: 6}


@dataclass
class Strategy:
    name: str = "default"
    order_threshold: int = 45   # min hand_strength to order-up / pick up in round 1
    call_threshold: int = 45    # min hand_strength to call a suit in round 2
    alone_threshold: int = 60   # min hand_strength (post-pickup/call) to go alone
    signal_aware: bool = True   # duck instead of overtaking a winning partner
    smart_discard: bool = True  # guarded-honor / void-building discard (False = naive min-value discard)
    role_aware_lead: bool = True  # maker leads trump, defender doesn't (False = always the same trump-lead rule)
    use_simple_count: bool = False  # bid/call/alone off simple_hand_count (human-countable) instead of hand_strength

    # Position-relative bidding adjustments (added to order/call_threshold),
    # sourced from euchre.cards/strategy/bidding/: first seat (opponent, left
    # of dealer) should bid tightest, since ordering up hands the *dealer* a
    # free upgrade (pick up the turned card, discard the worst). Second seat
    # (dealer's own partner) can bid loosest, since that upgrade lands on
    # their own side. Third seat (opponent, right of dealer) sits in between.
    # Dealer's own decision needs no offset -- it already evaluates the real
    # post-pickup hand, not a discount on the pre-pickup one.
    first_seat_offset: int = 6
    second_seat_offset: int = -6
    third_seat_offset: int = 2

    def position_offset(self, bid_position: int) -> int:
        return {0: self.first_seat_offset, 1: self.second_seat_offset,
                2: self.third_seat_offset}.get(bid_position, 0)


@dataclass
class TrickContext:
    hand: list[Card]
    trick_plays: list[tuple[int, Card]]  # (seat, card) already played this trick
    trump: str
    seat: int
    teammate_seat: int
    led_suit: str | None
    is_maker_team: bool = True


class HeuristicPlayer:
    def __init__(self, strategy: Strategy | None = None):
        self.strategy = strategy or Strategy()

    def _evaluate(self, hand: list[Card], trump: str) -> int:
        """Bidding-decision hand evaluation only (order-up/call/alone) --
        discard mechanics always use the precise card_score regardless of
        this flag, since guarded-honor/void-building is a pattern to
        recognize, not arithmetic to do under time pressure."""
        if self.strategy.use_simple_count:
            return simple_hand_count(hand, trump)
        return hand_strength(hand, trump)

    # ---- forced dealer pickup (used whenever this player is dealt the turned card) ----
    def pickup_and_discard(self, hand: list[Card], turned_card: Card) -> list[Card]:
        """smart_discard=True: never break trump unless forced; never break a
        guarded ace/king; otherwise prefer trimming a longer weak suit toward
        a singleton (building future void/ruff potential) over sacrificing a
        card that's already a singleton (see _VOID_BUILDING_DISCOUNT).
        smart_discard=False: naive baseline -- discard whatever has the
        lowest raw card_score, trump included, no honor protection. Used as
        the "before" side of experiments/discard_and_lead_rules.py."""
        trump = turned_card.suit
        candidate = hand + [turned_card]
        if not self.strategy.smart_discard:
            discard = min(candidate, key=lambda c: (card_score(c, trump), rank_index(c)))
            return [c for c in candidate if c is not discard]

        non_trump = [c for c in candidate if not c.is_trump(trump)]
        pool = non_trump if non_trump else candidate
        suit_counts = Counter(c.suit for c in pool)

        def discard_priority(c: Card) -> tuple[int, int]:
            is_honor = c.rank in ("A", "K")
            discount = 0 if is_honor else _VOID_BUILDING_DISCOUNT.get(suit_counts[c.suit], 0)
            return (card_score(c, trump) - discount, rank_index(c))

        discard = min(pool, key=discard_priority)
        return [c for c in candidate if c is not discard]

    # ---- bidding: round 1 (order up the turned card) ----
    def round1_decision(self, hand: list[Card], turned_card: Card, is_dealer: bool,
                         bid_position: int = 0) -> tuple[bool, list[Card]]:
        """Returns (call, resulting_hand). resulting_hand is the hand after a
        dealer pickup+discard (or the hand unchanged for non-dealers).
        bid_position (0/1/2) is this seat's index in the bidding order,
        ignored when is_dealer."""
        trump = turned_card.suit
        if is_dealer:
            resulting = self.pickup_and_discard(hand, turned_card)
            strength = self._evaluate(resulting, trump)
            return strength >= self.strategy.order_threshold, resulting
        strength = self._evaluate(hand, trump)
        threshold = self.strategy.order_threshold + self.strategy.position_offset(bid_position)
        return strength >= threshold, hand

    # ---- bidding: round 2 (call any other suit) ----
    def round2_decision(self, hand: list[Card], forbidden_suit: str, must_call: bool,
                         bid_position: int = 0) -> str | None:
        best_suit, best_strength = None, -1
        for suit in other_suits(forbidden_suit):
            s = self._evaluate(hand, suit)
            if s > best_strength:
                best_suit, best_strength = suit, s
        if must_call:
            return best_suit
        threshold = self.strategy.call_threshold + self.strategy.position_offset(bid_position)
        return best_suit if best_strength >= threshold else None

    # ---- going alone ----
    def decide_go_alone(self, hand: list[Card], trump: str) -> bool:
        return self._evaluate(hand, trump) >= self.strategy.alone_threshold

    # ---- card play ----
    def choose_card(self, ctx: TrickContext) -> Card:
        legal = legal_plays(ctx.hand, ctx.led_suit, ctx.trump)
        if not ctx.trick_plays:
            return self._choose_lead(legal, ctx)
        return self._choose_follow(legal, ctx)

    def _choose_lead(self, legal: list[Card], ctx: TrickContext) -> Card:
        """role_aware_lead=True (sourced from euchre.cards/strategy/): the
        maker's team should lead trump aggressively with 3+ trump, to strip
        opponents' trump. The defending team should almost never lead trump
        -- "leading trump when the opponents called trump...almost always
        hurts your team" -- with the sole exception of leading the right
        bower, which wins outright and needs no protection. Defenders lead
        off-suit aces instead to bank tricks before trump gets drawn.
        role_aware_lead=False: naive baseline -- apply the maker's trump-lead
        rule regardless of role. Used as the "before" side of
        experiments/discard_and_lead_rules.py."""
        trump = ctx.trump
        trump_cards = sorted(
            (c for c in legal if c.is_trump(trump)),
            key=lambda c: c.strength(trump), reverse=True,
        )
        has_strong_trump_lead = len(trump_cards) >= 3 or (trump_cards and trump_cards[0].strength(trump)[1] >= 6)
        if not ctx.is_maker_team and self.strategy.role_aware_lead:
            if trump_cards and trump_cards[0].is_right_bower(trump):
                return trump_cards[0]
        elif has_strong_trump_lead:
            return trump_cards[0]
        off_aces = [c for c in legal if c.rank == "A" and not c.is_trump(trump)]
        if off_aces:
            return off_aces[0]
        non_trump = [c for c in legal if not c.is_trump(trump)]
        pool = non_trump if non_trump else legal
        return min(pool, key=lambda c: card_score(c, trump))

    def _choose_follow(self, legal: list[Card], ctx: TrickContext) -> Card:
        trump = ctx.trump
        led_suit = ctx.led_suit
        best_seat, best_card = ctx.trick_plays[0]
        best_strength = best_card.strength(trump, led_suit)
        for seat, card in ctx.trick_plays[1:]:
            s = card.strength(trump, led_suit)
            if s > best_strength:
                best_seat, best_card, best_strength = seat, card, s

        partner_winning = best_seat == ctx.teammate_seat
        if partner_winning and self.strategy.signal_aware:
            return min(legal, key=lambda c: card_score(c, trump))

        winners = [c for c in legal if c.strength(trump, led_suit) > best_strength]
        if winners:
            return min(winners, key=lambda c: card_score(c, trump))
        return min(legal, key=lambda c: card_score(c, trump))
