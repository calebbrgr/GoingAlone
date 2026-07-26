# GoingAlone

A euchre simulator with rule-based, parameterized bots, built to answer one
question: **where does competitive advantage actually come from in euchre?**

**Want the answer as something you can actually use at a table, not as
simulation code?** See [`STRATEGY.md`](STRATEGY.md) — a practical bidding
cheat sheet and the one card-play rule that matters most, distilled from the
findings below and validated to win ~98% of games against a typical
undisciplined opponent.

## Layout

```
euchre/
  cards.py      Card model, bower-aware trump/led-suit comparisons
  rules.py      legal plays, trick winner, hand-strength heuristic, scoring
  players.py    HeuristicPlayer + Strategy (tunable thresholds/flags)
  engine.py     one hand / one full game (deal -> bid -> play -> score)
  simulate.py   batch runners (run_hands, run_games) used by the CLI/experiments
cli.py          quick head-to-head simulator from the command line
experiments/    scripts that isolate one variable at a time and report the effect
tests/          rule-correctness unit tests (bowers, follow-suit, scoring, ...)
```

## Quick start

```
python3 -m pytest tests/ -q          # verify the rules engine
python3 cli.py --games 2000          # Team A (seats 0,2) vs Team B (seats 1,3)
python3 cli.py --team-a-alone 18 --team-b-alone 24
python3 experiments/going_alone_threshold.py
```

`cli.py --help` lists every tunable knob (order/call/alone thresholds,
`--no-signal-a/b` to disable partner-aware play, `--no-stick-the-dealer`).

## How a bot decides anything

The strategy is no longer just invented and tuned in a vacuum — it's checked
against a published euchre strategy guide (**[euchre.cards](https://euchre.cards/strategy/)**,
specifically its [bidding](https://euchre.cards/strategy/bidding/),
[going-alone](https://euchre.cards/strategy/going-alone/), and
[common-mistakes](https://euchre.cards/strategy/common-mistakes/) pages), and
every deviation from that source is documented in code comments and below.

### Card valuation

`hand_strength(hand, trump)` (`euchre/rules.py`) sums a per-card point count
anchored to that guide's published trick-win-probability estimates (right
bower = 1.0 trick, left bower = 1.0, trump ace = 0.8, trump king = 0.5,
off-suit ace = 0.7, off-suit king = 0.3 — scaled x20 here to stay integer),
plus a trump-length bonus:

| | 9 | 10 | Q | K | A | left bower | right bower |
|---|---|---|---|---|---|---|---|
| trump | 2 | 4 | 8 | 10 | 16 | 18 | 20 |
| off-suit | 0 | 1 | 3 | 6 | 14 | — | — |

**This corrected a real, previously-unsourced assumption in this repo.** The
old model asserted "the weakest trump always outranks the strongest
off-suit card" and had a test enforcing it. The sourced numbers say
otherwise: a lone off-suit ace (14) is a genuinely better standalone card
than a bare trump king (10), queen (8), 10, or 9 — only trump ace and the
two bowers outrank it. Trump still dominates *in aggregate*, but through
`TRUMP_LENGTH_BONUS` (+6 for a 3rd trump card, +14 for a 4th, +24 for a 5th)
rather than every individual trump card outscoring every off-suit card —
matching the guide's own framing, which gates bidding on trump *count*
("three trump including a bower"), not a flat point sum. Two off-guide
adjustments, both commented in `rules.py`: the left bower is scored 18 vs
the right bower's 20 (the source ties them at 1.0 trick each, which is only
true if you hold *both* — the earlier per-tier monotonicity fix, `9 < 10 < J
< Q < K < A` with no collapsed ties, is preserved); and queen/10/9 values
(not given by the source) are interpolated to decay smoothly within each
tier.

### Bidding is seat-relative, not just team-relative

Per the guide: ordering up hands the *dealer* — whoever that is — a free
upgrade (pick up the turned card, discard the worst). If you're on the
dealer's own team, that upgrade helps you; if you're an opponent, you're
strengthening the hand you have to beat. So the same hand should be bid
differently depending on where you sit relative to the dealer this hand,
regardless of which "team" you're on. `Strategy.position_offset()` adds an
offset to `order_threshold`/`call_threshold` by bidding position:
first seat (opponent, bids first) +6 (strictest), second seat (dealer's own
partner) −6 (loosest), third seat (opponent) +2. Verified empirically this
is actually worth playing: with everything else held equal, the
position-aware side wins **52.0%** to **48.0%** against a flat-threshold
opponent (`experiments/` ad hoc check, 6,000 games).

### Discarding protects guarded honors and builds voids

The dealer's post-pickup discard (`pickup_and_discard`) now: (1) never
discards a trump card while any off-suit card is available; (2) never breaks
a guarded ace or king (an off-suit ace/king is exempt from the void-building
discount below, regardless of suit length); (3) among the remaining weak
filler cards, prefers trimming a suit you hold 2+ of down toward a singleton
over sacrificing a card that's already a singleton — sourced directly from
the guide's example: "discard a ten from a two-card suit rather than a nine
from a singleton, despite the ten's higher rank," because ending up with two
near-void suits creates more future ruffing opportunities than fully voiding
one suit while keeping an intact (but still weak) doubleton in another.

### Leading depends on whether you called trump

`_choose_lead` now takes `is_maker_team` into account. The guide is blunt
about this: *"leading trump when the opponents called trump...almost always
hurts your team."* So: the maker's team leads trump aggressively with 3+
trump (draws out defenders' trump, protects the maker's winners). The
defending team essentially never leads trump — the sole exception is leading
the right bower itself, which wins outright and needs no protection —
leading an off-suit ace instead to bank a trick before trump gets drawn.

A `Strategy` bundles all the *tunable* pieces — the three thresholds, the
three position offsets, and `signal_aware` (duck instead of overtaking your
own partner's winning card, validated separately in Finding 4 below).
Sweeping one knob while holding the rest fixed is what makes the experiments
below causally interpretable. The defaults (`order_threshold=45,
call_threshold=45, alone_threshold=60`, offsets `(6, -6, 2)`) aren't
guessed — they're empirical win-rate-maximizing / self-consistent values
found by the same sweep methodology used in the findings below (see "Where
the thresholds come from").

### A human-computable version of the same thing

`hand_strength()` requires exact arithmetic ("51") that nobody actually does
mid-hand. `simple_hand_count()` (`Strategy(use_simple_count=True)`) rounds
the same anchors to single digits — 3 per bower, 2 per ace, 1 per king or a
trump queen, 0 for everything else, plus a length bonus for extra trump
(+1/+3/+5 for a 3rd/4th/5th trump card) — so it's countable at the table in
a few seconds. Bidding decisions can use either evaluator; discard/lead
mechanics always use the precise one, since those are pattern-following
("don't break a guarded ace"), not arithmetic under time pressure. See
[`STRATEGY.md`](STRATEGY.md) for the resulting cheat sheet and Finding 6
below for what the rounding costs.

## Findings

All numbers below come from the scripts in `experiments/` (re-run them to
reproduce; each prints its own sample size and settings).

### 1. Dealer-side advantage is the single biggest effect in the game — and correct play makes it *bigger*

`experiments/position_advantage.py` — 40,000 hands, **identical strategy in
all four seats**, so any gap is structural, not skill.

| | points/hand |
|---|---|
| Dealer's team | **0.950** |
| Non-dealer team | 0.518 |

The dealer's team scores **~1.8x** the points of the other team, on identical
skill. The surprising part: this used to be driven roughly evenly by "the
dealer's team wins the bid somewhat more" plus "they make bigger when they
do." Once bidding became position-aware (Finding-that-isn't-numbered above),
the dealer's team's *maker share* jumped to **71.9%** (was 56.8% under flat
thresholds) — because a well-calibrated opponent now recognizes that
ordering up mostly just hands the dealer a free upgrade, and *should* pass
far more often. First and third seat (the two opponent positions) now only
end up as maker 14.3% and 13.8% of hands combined 28.1%, vs. dealer 35.1% and
dealer's partner 36.8%. Playing *correctly* as an opponent means bidding
tighter, which means bidding less, which means ceding the hand to the dealer
side even more often than a naively symmetric bot would. The one offsetting
effect: opponent hands that do clear the higher bar are stronger on average,
so their per-call success rate improves (points/hand ratio actually narrowed
from ~2.2x to ~1.8x even as the frequency gap widened) — but not enough to
close the gap. This is where most of the built-in, skill-independent edge in
euchre lives, and no amount of good defensive-side bidding discipline
removes it — it can only be partially compensated for.

### 2. Going alone: a real but narrow-and-asymmetric edge

`experiments/going_alone_threshold.py` — sweeping Team A's alone-threshold
against a fixed baseline opponent (`alone_threshold=60`), 4,000 games/point:

| alone_threshold | win rate | loner share | loner euchred |
|---|---|---|---|
| 34 (very loose) | 32.3% | 99.1% | 32.4% |
| 46 | 40.0% | 78.3% | 25.0% |
| **58–66 (optimum)** | **~49.2–50.3%** | 13–30% | 1.7–6.3% |
| 80 (very strict) | 46.4% | 1.9% | 0.0% |
| never | 45.6% | 0% | — |

In point-count terms, the tier the guide calls "near-guaranteed" (both bowers
+ trump ace + two off-suit aces = 18+20+16+14+14 = 82) is far above our
empirical optimum (~60) — our threshold sits closer to the guide's Tier 2
("strong candidate") hands, e.g. right bower + trump ace/king + two off-suit
aces (20+16+10+14+14=74, though that's still above 60 — a hand like both
bowers + trump king + one off-suit ace, 18+20+10+14=62, lands right at it).
The curve is still asymmetric exactly as before: calling alone too often is
far more costly (32.3% win rate at the loose end) than never calling alone
at all (45.6%). Err conservative, not aggressive.

### 3. Bidding discipline (order-up/call threshold): an inverted U, and it's steep

`experiments/trump_calling_threshold.py` — same sweep design, 4,000 games/point,
against a fixed baseline opponent (`order/call=45`):

| threshold | win rate | maker share | euchred as maker |
|---|---|---|---|
| 18 (call almost anything) | 20.0% | 88.6% | 46.6% |
| 32 | 32.7% | 71.9% | 36.3% |
| **43–47 (optimum)** | **~48.6–50.9%** | 47–53% | 16–20% |
| 60 | 39.6% | 29.6% | 12.8% |
| 78 (call almost nothing) | 22.4% | 21.8% | 21.2% |

Calling trump too often is still the single fastest way to lose (worse than
never going alone, worse than sloppy card play) — being maker 88.6% of the
time sounds dominant but you're euchred *nearly half* of those hands. Being
too tight is also a loser, and interestingly for a *different* reason than
before: at the very tight end (78) the euchre-as-maker rate climbs back up
to 21.2%, because the only hands that still clear such a strict bar skew
toward long-but-low trump suits (the length bonus can push a mediocre hand
over a high bar) without the individual high cards needed to actually run
the suit — a reminder that `hand_strength` is a heuristic, not a perfect
oracle, and extreme settings expose its blind spots.

### 4. Partner-aware card play (not overtaking your own partner) is a clean, isolated win

`experiments/partner_signaling.py` — 6,000 games, **identical bidding
strategy** for both teams (`order/call=45, alone=60`); the only difference is
whether a player ducks (plays low) when its own partner is already winning
the trick, vs. always playing the cheapest card that wins even if that means
beating its own partner's card:

| | win rate | points/hand | euchred as maker |
|---|---|---|---|
| Signal-aware (ducks for partner) | **54.9%** | 0.758 | 17.0% |
| Naive (always takes the trick) | 45.1% | 0.705 | 20.3% |

A >9-point win-rate swing from one simple, cost-free rule ("don't beat your
own partner's winning card") — the cheapest lever in the whole simulation:
no extra information needed, just don't waste tricks your partner already
won. This number has stayed essentially unchanged (54.9–55.2%) across every
revision of the card-valuation and bidding model in this project, because it
doesn't depend on hand_strength at all — only on trick-order logic.

### 5. Discard and leading rules: real, but the smallest levers measured

`experiments/discard_and_lead_rules.py` — 16,000 games per variant, bidding
strategy identical for everyone (`order/call=45, alone=60, signal_aware=True`).
Team B is always the fully naive baseline (pre-source discard/lead
behavior); Team A cycles through all four combinations of `smart_discard`
(guarded-honor / void-building discard) and `role_aware_lead` (maker leads
trump, defender doesn't):

| variant | win rate | points/hand | euchred as maker |
|---|---|---|---|
| naive (baseline behavior) | 49.5% | 0.730 | 17.3% |
| smart_discard only | 50.4% | 0.735 | 17.4% |
| role_aware_lead only | **51.6%** | 0.739 | 17.4% |
| both (fully sourced) | 51.5% | 0.743 | 17.4% |

Both rules help, but neither is large, and role-aware leading (~2.1 points)
matters roughly twice as much as the discard rule (~0.9 points) on its own.
The two together (~2.0 points) land *below* the sum of their individual
effects (~3.0 points) — mild diminishing returns rather than synergy, likely
because both rules mostly matter in overlapping situations (a hand strong
enough to matter for the discard choice is often also the hand that
determines whether you're leading trump). These are genuinely the smallest
effects measured in this project — a reminder that not every piece of
"correct" advice from a strategy guide moves the needle by the same amount;
bidding discipline and partner-awareness dominate, and card-play
micro-optimization is a distant third and fourth.

### 6. A human-computable strategy loses ~4 points to a perfect calculator — and still wins 98% against a casual opponent

`experiments/simple_count_validation.py` — 16,000 games each. Same overall
strategy (position-aware bidding, signal-aware play, smart discard, role-aware
leads) played two ways: with `simple_hand_count()` (the single-digit,
countable-at-the-table version) vs. with the precise `hand_strength()`, and
separately, `simple_hand_count()` vs. a "casual" opponent (loose flat
threshold, no seat awareness, no partner-awareness, no discard/lead
discipline — a stand-in for a typical unstudied player):

| matchup | simple-count win rate |
|---|---|
| vs. precise `hand_strength()` (exact arithmetic) | 48.1% |
| vs. casual/undisciplined opponent | **97.5%** |

Rounding to numbers a human can actually count still costs something —
about 4 win-rate points against an opponent computing exact values. That
gap used to be ~13 points; `experiments/simple_count_upgrade.py` (16,000
games) shows where most of it went: the original `simple_hand_count()`
scored a trump queen as 0, the same as a bare 9, and grew its trump-length
bonus linearly (+1/+2/+3 for a 3rd/4th/5th trump card) where the precise
model's bonus is convex. Counting the trump queen like a king and
steepening the length bonus to +1/+3/+5 — both still trivial to track at
the table, no new categories to memorize — took the isolated matchup from
43.7% to 47.4% on its own. A more "principled"-looking alternative (bump
every trump card a full tier above its off-suit counterpart: bower/A/K/Q ->
4/3/2/1) was also tested and performed *worse* (46.7%) — a reminder that
"looks more accurate" and "wins more" aren't the same thing; it added a
category to track without buying anything empirically.

That remaining ~4-point gap is almost never the comparison that matters in
practice: no one plays exact `hand_strength()` arithmetic at a real table.
Against the kind of opponent you're actually likely to face, applying
**just the two dominant levers** (a disciplined, seat-aware bidding count,
and never overtaking your own partner's winning card) — with everything
else rounded to single digits — wins essentially every game. See
[`STRATEGY.md`](STRATEGY.md) for this as an actual usable cheat sheet.

### Takeaway

Ranked by how much win-rate is on the table: **dealer position** (structural,
you can't opt out of it — and correct opponent bidding discipline makes the
*frequency* gap worse even as it narrows the per-hand quality gap) >
**bidding-threshold discipline** (~30-point win-rate spread between good and
bad calibration, steep penalty in both directions, for related but distinct
reasons at each extreme) > **going-alone calibration** (~18-point spread,
asymmetric — bad to overuse, only mildly bad to underuse) >
**partner-aware card play** (~9-point spread, but "free" — no new
information needed) > **position-aware bidding** (~4-point spread, worth
doing but not dominant) > **role-aware leading** (~2 points) >
**guarded-honor/void-building discard** (~1 point). The two rankings that
might surprise: correct defensive bidding *amplifies* the dealer's edge
rather than closing it, and the two card-play refinements sourced most
directly from "common mistakes" advice (discard shape, lead selection) are
the smallest levers in the whole simulation — most of euchre's skill gap
lives in bidding discipline and not wasting your partner's winning tricks,
not in fine card-play technique. Finding 6 is the practical payoff of that
ranking: because the two dominant levers are cheap to apply exactly (a
seat-aware bidding count, a single "don't overtake partner" rule) while the
smaller levers are the ones that actually need precise arithmetic to
squeeze out, you can round everything to single digits and still capture
the overwhelming majority of the available edge against a real opponent.

### Where the thresholds come from

The defaults in `Strategy` (`order/call=45, alone=60`, position offsets
`(6, -6, 2)`) are empirical best-response / self-consistent values: for each
knob, one side was swept against a fixed opponent until win rate peaked,
then the opponent was moved to that peak and re-swept to confirm the peak
didn't move (a rough fixed-point check, not a full game-theoretic solve).
The position-offset *magnitudes* were separately checked against smaller
(3,-3,1) and larger (10,-10,4 and 14,-14,6) variants — (6,-6,2) beat all of
them. See the sweeps above, or rerun with different starting baselines to
re-derive them from scratch.

## Sources

- [euchre.cards/strategy/bidding/](https://euchre.cards/strategy/bidding/) — seat-relative bidding minimums, trick-value point system
- [euchre.cards/strategy/going-alone/](https://euchre.cards/strategy/going-alone/) — loner hand tiers, score-based aggression
- [euchre.cards/strategy/](https://euchre.cards/strategy/) — leading strategy (maker vs. defender), duck-for-partner
- [euchre.cards/strategy/common-mistakes/](https://euchre.cards/strategy/common-mistakes/) — guarded-honor discard, void-building discard example
