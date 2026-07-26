import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from euchre.cards import Card, RANKS
from euchre.rules import card_score, legal_plays, trick_winner, score_hand, hand_strength, simple_hand_count


def test_left_bower_counts_as_trump():
    jc = Card("J", "C")  # left bower when trump is spades
    assert jc.is_trump("S")
    assert jc.effective_suit("S") == "S"
    assert not jc.is_trump("H")  # not trump at all when trump is an unrelated suit


def test_bower_ranking_above_ace():
    trump = "S"
    right = Card("J", "S")
    left = Card("J", "C")
    ace = Card("A", "S")
    assert right.strength(trump) > left.strength(trump) > ace.strength(trump)


def test_trump_beats_offsuit_ace_even_low_trump():
    trump = "H"
    low_trump = Card("9", "H")
    off_ace = Card("A", "S")
    led_suit = "S"
    assert low_trump.strength(trump, led_suit) > off_ace.strength(trump, led_suit)


def test_must_follow_suit_including_left_bower():
    trump = "S"
    hand = [Card("J", "C"), Card("9", "H"), Card("A", "D")]
    # led suit is spades (trump); left bower (JC) counts as spades and must be played
    legal = legal_plays(hand, "S", trump)
    assert legal == [Card("J", "C")]


def test_can_play_anything_when_void_of_led_suit():
    trump = "S"
    hand = [Card("9", "H"), Card("A", "D")]
    legal = legal_plays(hand, "C", trump)  # void of clubs
    assert set(legal) == {Card("9", "H"), Card("A", "D")}


def test_trick_winner_offsuit_cannot_win():
    trump = "S"
    plays = [(0, Card("A", "H")), (1, Card("K", "D")), (2, Card("9", "S")), (3, Card("Q", "H"))]
    # led suit hearts; seat 2 plays a trump 9S and must win regardless of ace of hearts
    assert trick_winner(plays, trump) == 2


def test_trick_winner_follows_led_suit_when_no_trump_played():
    trump = "S"
    plays = [(0, Card("9", "H")), (1, Card("A", "H")), (2, Card("K", "D")), (3, Card("Q", "H"))]
    assert trick_winner(plays, trump) == 1  # AH highest of led suit, no trump in trick


def test_scoring_euchre():
    points = score_hand(maker_team=0, tricks_won={0: 2, 1: 3}, went_alone=False)
    assert points == {0: 0, 1: 2}


def test_scoring_march():
    points = score_hand(maker_team=0, tricks_won={0: 5, 1: 0}, went_alone=False)
    assert points == {0: 2, 1: 0}


def test_scoring_normal_make():
    points = score_hand(maker_team=1, tricks_won={0: 1, 1: 4}, went_alone=False)
    assert points == {0: 0, 1: 1}


def test_scoring_loner_march():
    points = score_hand(maker_team=1, tricks_won={0: 0, 1: 5}, went_alone=True)
    assert points == {0: 0, 1: 4}


def test_offsuit_ranks_are_strictly_monotonic():
    trump = "S"
    # off-suit means not spades and not the left-bower suit (clubs); use hearts
    values = [card_score(Card(r, "H"), trump) for r in RANKS]
    assert values == sorted(values) and len(set(values)) == len(values)


def test_trump_nonbower_ranks_are_strictly_monotonic():
    trump = "S"
    values = [card_score(Card(r, "S"), trump) for r in RANKS if r != "J"]
    assert values == sorted(values) and len(set(values)) == len(values)


def test_offsuit_ace_beats_weak_trump_but_not_trump_ace():
    # Sourced from euchre.cards/strategy/bidding/: off-suit ace (0.7 trick)
    # is a genuinely better standalone card than a bare low trump (trump 9,
    # 10, or Q all sit below it), but still weaker than trump ace (0.8) or
    # either bower -- trump dominates in aggregate via count, not by having
    # every individual trump card outrank every off-suit card.
    trump = "S"
    off_ace = card_score(Card("A", "H"), trump)
    assert off_ace > card_score(Card("9", "S"), trump)
    assert off_ace > card_score(Card("10", "S"), trump)
    assert off_ace > card_score(Card("Q", "S"), trump)
    assert off_ace < card_score(Card("A", "S"), trump)
    assert off_ace < card_score(Card("J", "S"), trump)  # right bower
    assert off_ace < card_score(Card("J", "C"), trump)  # left bower


def test_trump_length_bonus_rewards_a_long_trump_suit():
    trump = "S"
    # Same weak off-suit filler throughout; only the trump count (3 vs 2)
    # differs, isolating the length bonus that kicks in at 3+ trump.
    three_trump = [Card("9", "S"), Card("10", "S"), Card("Q", "S"), Card("9", "H"), Card("9", "D")]
    two_trump = [Card("9", "S"), Card("10", "S"), Card("9", "C"), Card("9", "H"), Card("9", "D")]
    assert hand_strength(three_trump, trump) > hand_strength(two_trump, trump)


def test_hand_strength_monotonic_with_bowers():
    trump = "S"
    strong = [Card("J", "S"), Card("J", "C"), Card("A", "S"), Card("9", "H"), Card("9", "D")]
    weak = [Card("9", "S"), Card("9", "H"), Card("9", "D"), Card("9", "C"), Card("10", "H")]
    assert hand_strength(strong, trump) > hand_strength(weak, trump)


def test_simple_hand_count_is_actually_simple_and_agrees_on_direction():
    trump = "S"
    # Both bowers + trump ace: 3+3+2 plus a +1 length bonus for the 3rd
    # trump = 9, a number a human can count in a few seconds.
    both_bowers_plus_ace = [Card("J", "S"), Card("J", "C"), Card("A", "S"), Card("9", "H"), Card("9", "D")]
    assert simple_hand_count(both_bowers_plus_ace, trump) == 9
    # Same relative ordering as the precise model on a clearly-worse hand.
    weak = [Card("9", "S"), Card("9", "H"), Card("9", "D"), Card("9", "C"), Card("10", "H")]
    assert simple_hand_count(both_bowers_plus_ace, trump) > simple_hand_count(weak, trump)
    assert hand_strength(both_bowers_plus_ace, trump) > hand_strength(weak, trump)
