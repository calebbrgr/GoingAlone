"""Single-hand and full-game simulation loop."""
from __future__ import annotations

from dataclasses import dataclass, field
import random

from .cards import Card, new_shuffled_deck
from .players import HeuristicPlayer, TrickContext
from .rules import score_hand, trick_winner


def team_of(seat: int) -> int:
    return seat % 2  # seats 0,2 = team 0 ; seats 1,3 = team 1


def partner_of(seat: int) -> int:
    return (seat + 2) % 4


@dataclass
class HandResult:
    dealer: int
    order_round: int          # 1 = ordered up the turned card, 2 = called a suit
    maker_seat: int
    maker_team: int
    trump: str
    alone: bool
    tricks_won: dict          # team -> trick count
    points: dict              # team -> points scored this hand
    euchred: bool
    bid_position: int = -1    # index in bidding order (0=left of dealer .. 3=dealer)
    dealer_is_maker_team: bool = False
    redeal: bool = False


@dataclass
class GameResult:
    winner_team: int
    final_score: dict
    hands: list = field(default_factory=list)  # list[HandResult]


def deal(rng: random.Random):
    deck = new_shuffled_deck(rng)
    hands = [deck[i * 5:(i + 1) * 5] for i in range(4)]
    kitty = deck[20:24]
    turned_card = kitty[0]
    return hands, turned_card


def _seat_order_from(leader: int, active_seats: set[int]) -> list[int]:
    order = []
    seat = leader
    for _ in range(4):
        if seat in active_seats:
            order.append(seat)
        seat = (seat + 1) % 4
    return order


def play_hand(players: list[HeuristicPlayer], dealer: int, rng: random.Random,
              stick_the_dealer: bool = True) -> HandResult:
    hands, turned_card = deal(rng)
    bid_order = [(dealer + 1 + i) % 4 for i in range(4)]

    maker_seat = None
    trump = None
    order_round = None

    # --- round 1: order up the turned card ---
    for i, seat in enumerate(bid_order):
        is_dealer = seat == dealer
        call, resulting_hand = players[seat].round1_decision(hands[seat], turned_card, is_dealer, bid_position=i)
        if call:
            trump = turned_card.suit
            maker_seat = seat
            order_round = 1
            if is_dealer:
                hands[dealer] = resulting_hand
            else:
                hands[dealer] = players[dealer].pickup_and_discard(hands[dealer], turned_card)
            break

    # --- round 2: call any other suit (stick-the-dealer forces a call) ---
    if maker_seat is None:
        forbidden = turned_card.suit
        for i, seat in enumerate(bid_order):
            is_dealer = seat == dealer
            must_call = is_dealer and stick_the_dealer
            suit = players[seat].round2_decision(hands[seat], forbidden, must_call, bid_position=i)
            if suit:
                trump = suit
                maker_seat = seat
                order_round = 2
                break

    if maker_seat is None:
        return HandResult(dealer=dealer, order_round=0, maker_seat=-1, maker_team=-1,
                           trump="", alone=False, tricks_won={}, points={0: 0, 1: 0},
                           euchred=False, redeal=True)

    maker_team = team_of(maker_seat)
    alone = players[maker_seat].decide_go_alone(hands[maker_seat], trump)
    sitting_out = partner_of(maker_seat) if alone else None
    active_seats = {s for s in range(4) if s != sitting_out}

    tricks_won = {0: 0, 1: 0}
    leader = _seat_order_from((dealer + 1) % 4, active_seats)[0]
    for _ in range(5):
        order_this_trick = _seat_order_from(leader, active_seats)
        trick_plays: list[tuple[int, Card]] = []
        led_suit = None
        for seat in order_this_trick:
            ctx = TrickContext(
                hand=hands[seat], trick_plays=trick_plays, trump=trump,
                seat=seat, teammate_seat=partner_of(seat), led_suit=led_suit,
                is_maker_team=(team_of(seat) == maker_team),
            )
            card = players[seat].choose_card(ctx)
            hands[seat].remove(card)
            trick_plays.append((seat, card))
            if led_suit is None:
                led_suit = card.effective_suit(trump)
        winner = trick_winner(trick_plays, trump)
        tricks_won[team_of(winner)] += 1
        leader = winner

    points = score_hand(maker_team, tricks_won, alone)
    euchred = tricks_won[maker_team] < 3
    return HandResult(dealer=dealer, order_round=order_round, maker_seat=maker_seat,
                       maker_team=maker_team, trump=trump, alone=alone,
                       tricks_won=tricks_won, points=points, euchred=euchred,
                       bid_position=bid_order.index(maker_seat),
                       dealer_is_maker_team=(maker_team == team_of(dealer)))


def play_game(players: list[HeuristicPlayer], rng: random.Random, target_score: int = 10,
              stick_the_dealer: bool = True, starting_dealer: int = 0,
              max_hands: int = 200) -> GameResult:
    score = {0: 0, 1: 0}
    dealer = starting_dealer
    hands: list[HandResult] = []
    while score[0] < target_score and score[1] < target_score and len(hands) < max_hands:
        result = play_hand(players, dealer, rng, stick_the_dealer=stick_the_dealer)
        if result.redeal:
            continue  # same dealer redeals; only reachable if stick_the_dealer=False
        hands.append(result)
        for team, pts in result.points.items():
            score[team] += pts
        dealer = (dealer + 1) % 4
    winner = 0 if score[0] > score[1] else 1
    return GameResult(winner_team=winner, final_score=score, hands=hands)
