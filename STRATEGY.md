# A practical euchre strategy card

Everything here is derived from `euchre/rules.py`'s `simple_hand_count()` and
validated by `experiments/simple_count_validation.py`. It is deliberately
*not* the most accurate model this project has (`hand_strength()` is more
precise — see `README.md`) — it's the model that trades a small amount of
accuracy for being something you can actually compute in your head in a few
seconds, mid-hand, under time pressure. This document is that trade written
down as a usable strategy, not just a code comment.

## The count

Look at your hand (or your hand + the turned-up card, if you're the
dealer). For the suit in question, add up:

| card | points |
|---|---|
| either bower (right or left) | **3** each |
| ace (trump or off-suit) | **2** each |
| king (trump or off-suit), or the **trump queen** | **1** each |
| off-suit queen, jack (non-bower), 10, 9; trump 10, 9 | 0 |
| **+1** if you hold a 3rd trump card, **+3** for a 4th, **+5** for a 5th | (length bonus) |

That's the whole system. No other card matters.

## Bidding (round 1: order up the turned card)

Your bar depends on where you sit relative to the dealer this hand — because
ordering up hands *the dealer* a free upgrade (pick up the turned card,
discard their worst), and that upgrade only helps you if the dealer is your
partner:

| seat | who | minimum count to order up |
|---|---|---|
| 1st to bid | opponent (left of dealer) | **8** |
| 2nd to bid | **your own partner is the dealer** | **6** |
| 3rd to bid | opponent (right of dealer) | **7** |
| you're the dealer | evaluate your hand *with* the turned card, discard your worst | **7** |

The gap between "1st seat" (8) and "2nd seat" (6) is the single most
important adjustment in this sheet — it's worth about as much on its own as
everything else in this document *except* bidding-threshold and partner-play
discipline (see README.md Finding "position-aware bidding," +4 win-rate
points in isolation). If you take away one thing: **when your partner is
dealing, bid looser; when an opponent is dealing, bid tighter** — the same
hand should get a different answer depending on whose turn it is to deal.

Round 2 (nobody ordered up, you can call any *other* suit): same bar, same
seat-based adjustment, evaluated against your hand as dealt (no pickup).

## Concrete hand shapes (so "count to 7" isn't abstract)

| hand | count | clears the base bar (7)? |
|---|---|---|
| Both bowers alone | 6 | not quite — needs one more card |
| Both bowers + any 3rd trump card | 7 | yes |
| Both bowers + 1 off-suit ace | 8 | yes, easily |
| 1 bower + trump ace + trump king | 7 | yes |
| 1 bower + 2 off-suit aces | 7 | yes |
| 3 plain trump (no bower), no side support | 4 | no |
| 3 plain trump + 1 off-suit ace + 1 off-suit king | 7 | yes |
| 2 trump, no aces, no bower | 1 | not close |

The pattern: **a bower is worth roughly as much as a trump ace + trump king
combined.** Without a bower, you need real side-suit strength (multiple
aces/kings) to compensate — three bare trump cards with nothing else is a
pass, not a call.

## Going alone

**Count 9 or more (in the hand you'll actually play, i.e. after your own
pickup/discard if you're the dealer).** No seat adjustment — this applies
everywhere.

The clean benchmark that hits exactly 9: **both bowers + the trump ace.**
That's the shape to look for. Slightly weaker equivalents also clear it
(both bowers + an off-suit ace + an off-suit king = 9), but "both bowers
plus the trump ace" is the one worth memorizing.

Don't round up "close enough" — the cost of calling alone too early is much
worse than the cost of playing it safe. A hand at count 6-7 that goes alone
gets euchred roughly a third of the time; wait for 9.

## The one card-play rule that matters more than any of the above

**If your partner is already winning the trick, don't beat their card.**
Play your lowest legal card instead. This alone is worth more win rate in
this project's simulations (README.md Finding 4, ~9 win-rate points) than
every bidding refinement combined except the base threshold itself. It
costs nothing — no counting, no memory, just checking "is my partner
already ahead on this trick" before you play.

The two smaller card-play refinements below matter (README.md Finding 5,
~1-2 points each) but are genuinely optional polish, not requirements:

- **Discarding (as dealer):** don't break up a guarded ace or king. Among
  your weak leftover cards, prefer trimming a suit you hold two-or-more of
  down toward a single card, rather than giving up a card that's already
  your only one in that suit.
- **Leading:** if your team called trump and you hold 3+ trump (or a
  bower), lead trump to strip the defenders'. If you're defending, don't
  lead trump at all unless it's the right bower — lead an off-suit ace
  instead.

## What this is actually worth

`experiments/simple_count_validation.py`, 16,000 games each:

| matchup | this cheat sheet's win rate |
|---|---|
| vs. a bot with the exact (non-roundable) arithmetic model | 48.1% |
| vs. a "casual" opponent — loose bidding, no seat awareness, no partner-awareness, no discard/lead discipline | **97.5%** |

Rounding still costs something — about 4 win-rate points against an
opponent playing this hand's *exact* value down to the last point, which no
human does at a real table. That's much narrower than it used to be: the
count above used to score a trump queen as 0 (the same as a bare 9) and
grow its length bonus linearly (+1/+2/+3 for a 3rd/4th/5th trump card).
Counting the trump queen like a king and steepening the length bonus to
+1/+3/+5 — both still trivial to track at the table — closed most of that
gap on their own (`experiments/simple_count_upgrade.py`: 43.7% -> 47.4% in
isolation). Against the kind of play you'll actually face — someone who
orders up on any 2 trump, doesn't think about dealer position, and happily
overtakes their own partner's winning ace — this sheet still wins
**nineteen games out of twenty**. That gap between 48.1% and 97.5% is the
whole point: you don't need a calculator to have a large edge, you need
bidding discipline and the one partner rule, applied consistently — getting
the arithmetic closer to exact just narrows the smaller remaining gap.
