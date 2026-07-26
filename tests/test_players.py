import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from euchre.cards import Card
from euchre.players import HeuristicPlayer, Strategy, TrickContext


def _make(**kwargs):
    return HeuristicPlayer(Strategy(**kwargs))


def test_first_seat_requires_stronger_hand_than_second_seat():
    # Same hand, same threshold -- only bid_position differs. First seat
    # (0, opponent of dealer) should be pickier than second seat (1,
    # dealer's own partner), per euchre.cards/strategy/bidding/.
    player = _make(order_threshold=35, first_seat_offset=6, second_seat_offset=-6)
    turned = Card("K", "S")
    # hand_strength = 38 here: clears the lenient second-seat bar (29) but
    # not the stricter first-seat bar (41).
    hand = [Card("J", "S"), Card("10", "S"), Card("A", "H"), Card("9", "D"), Card("9", "C")]
    call_first, _ = player.round1_decision(hand, turned, is_dealer=False, bid_position=0)
    call_second, _ = player.round1_decision(hand, turned, is_dealer=False, bid_position=1)
    assert call_second and not call_first


def test_dealer_position_ignores_seat_offset():
    # Dealer's own decision uses the real post-pickup hand directly, no
    # position discount/penalty applied -- bid_position must be a no-op.
    player = _make(order_threshold=35, first_seat_offset=6, second_seat_offset=-6)
    turned = Card("A", "S")
    hand = [Card("9", "S"), Card("10", "S"), Card("9", "H"), Card("9", "D"), Card("9", "C")]
    call_a, resulting_a = player.round1_decision(hand, turned, is_dealer=True, bid_position=0)
    call_b, resulting_b = player.round1_decision(hand, turned, is_dealer=True, bid_position=1)
    assert call_a == call_b and resulting_a == resulting_b
    assert len(resulting_a) == 5


def test_pickup_discard_never_discards_trump_when_offsuit_available():
    player = _make()
    turned = Card("9", "S")  # weak turn-up, trump = spades
    hand = [Card("10", "S"), Card("A", "H"), Card("K", "D"), Card("Q", "C"), Card("J", "H")]
    resulting = player.pickup_and_discard(hand, turned)
    trump_count_before = sum(1 for c in hand + [turned] if c.is_trump("S"))
    trump_count_after = sum(1 for c in resulting if c.is_trump("S"))
    assert trump_count_after == trump_count_before  # no trump discarded


def test_pickup_discard_protects_guarded_ace_over_weak_singleton():
    player = _make()
    trump = "S"
    turned = Card("9", "S")
    # Off-suit A-K guarded pair in hearts, plus weak singleton fillers.
    # Discarding should break neither the ace nor the king.
    hand = [Card("10", "S"), Card("A", "H"), Card("K", "H"), Card("Q", "D"), Card("9", "C")]
    resulting = player.pickup_and_discard(hand, turned)
    assert Card("A", "H") in resulting
    assert Card("K", "H") in resulting


def test_defender_does_not_lead_trump_without_right_bower():
    player = _make()
    trump = "S"
    # 3+ trump, which would trigger a trump lead for the *maker*, but this
    # hand holds neither bower -- a defender should lead the off-suit ace
    # instead of stripping trump for the opposing maker's benefit.
    hand = [Card("9", "S"), Card("10", "S"), Card("Q", "S"), Card("A", "H"), Card("9", "D")]
    ctx = TrickContext(hand=hand, trick_plays=[], trump=trump, seat=0,
                        teammate_seat=2, led_suit=None, is_maker_team=False)
    led = player.choose_card(ctx)
    assert led == Card("A", "H")


def test_defender_leads_right_bower_when_held():
    player = _make()
    trump = "S"
    hand = [Card("J", "S"), Card("9", "H"), Card("9", "D"), Card("Q", "C"), Card("10", "H")]
    ctx = TrickContext(hand=hand, trick_plays=[], trump=trump, seat=0,
                        teammate_seat=2, led_suit=None, is_maker_team=False)
    led = player.choose_card(ctx)
    assert led == Card("J", "S")


def test_maker_leads_trump_with_three_or_more():
    player = _make()
    trump = "S"
    hand = [Card("9", "S"), Card("10", "S"), Card("Q", "S"), Card("A", "H"), Card("9", "D")]
    ctx = TrickContext(hand=hand, trick_plays=[], trump=trump, seat=0,
                        teammate_seat=2, led_suit=None, is_maker_team=True)
    led = player.choose_card(ctx)
    assert led.is_trump(trump)


def test_naive_lead_ignores_role_and_strips_defenders_own_trump():
    # role_aware_lead=False: same hand/context as
    # test_defender_does_not_lead_trump_without_right_bower, but now the
    # defender leads trump anyway (the pre-source-fix behavior).
    player = _make(role_aware_lead=False)
    trump = "S"
    hand = [Card("9", "S"), Card("10", "S"), Card("Q", "S"), Card("A", "H"), Card("9", "D")]
    ctx = TrickContext(hand=hand, trick_plays=[], trump=trump, seat=0,
                        teammate_seat=2, led_suit=None, is_maker_team=False)
    led = player.choose_card(ctx)
    assert led.is_trump(trump)


def test_naive_discard_wastes_trump_that_smart_discard_protects():
    # A weak trump 9 (score 2) has a lower raw card_score than any of the
    # off-suit honors here (K=6, A=14) -- naive scoring (no trump exclusion)
    # discards it outright. smart_discard excludes trump from consideration
    # whenever an off-suit card is available, so it sheds the off-suit queen
    # (score 3, the true minimum among non-trump cards) instead, keeping
    # both trump cards intact.
    trump = "S"
    turned = Card("A", "S")
    hand = [Card("9", "S"), Card("A", "H"), Card("K", "D"), Card("Q", "C"), Card("K", "H")]

    naive = _make(smart_discard=False)
    naive_resulting = naive.pickup_and_discard(hand, turned)
    assert Card("9", "S") not in naive_resulting  # trump discarded away

    smart = _make(smart_discard=True)
    smart_resulting = smart.pickup_and_discard(hand, turned)
    assert Card("9", "S") in smart_resulting and Card("A", "S") in smart_resulting
    assert Card("Q", "C") not in smart_resulting  # weak off-suit filler discarded instead
