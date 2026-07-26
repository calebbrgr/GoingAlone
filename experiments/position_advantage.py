"""Where does dealer / bidding-position advantage come from?

All four seats run the *identical* strategy, so any measured gap in
points-per-hand between positions is a pure structural effect of the deal and
bidding order -- not a difference in skill.
"""
import _pathfix  # noqa: F401

from euchre.players import Strategy
from euchre.simulate import run_hands

POSITION_NAMES = {
    0: "left of dealer (1st bid, opponent)",
    1: "dealer's partner   (2nd bid)",
    2: "right of dealer (3rd bid, opponent)",
    3: "dealer            (4th bid)",
}


def main() -> None:
    baseline = Strategy(name="baseline", order_threshold=45, call_threshold=45, alone_threshold=60)
    strategies = [baseline] * 4

    hands = run_hands(strategies, num_hands=40_000, seed=1)
    n = len(hands)

    # Points earned by "the dealer's team" vs "the non-dealer team" each hand,
    # regardless of absolute seat numbers.
    dealer_team_pts = 0.0
    other_team_pts = 0.0
    dealer_team_maker = 0
    for h in hands:
        dteam = h.dealer % 2
        oteam = 1 - dteam
        dealer_team_pts += h.points[dteam]
        other_team_pts += h.points[oteam]
        if h.dealer_is_maker_team:
            dealer_team_maker += 1

    print(f"Simulated {n} independent hands, identical strategy in all 4 seats.\n")
    print("=== Dealer's team vs. non-dealer's team ===")
    print(f"Dealer's team points/hand:     {dealer_team_pts/n:.4f}")
    print(f"Non-dealer team points/hand:   {other_team_pts/n:.4f}")
    print(f"Dealer's team is the maker:    {dealer_team_maker/n:.1%} of hands "
          f"(50% would mean no edge)\n")

    print("=== By bidding-order position (who ends up calling trump, and how it pays off) ===")
    print(f"{'position':38s} {'share of hands they make':>26s} {'points/hand THAT TEAM earns':>28s}")
    for pos in range(4):
        made = [h for h in hands if h.bid_position == pos]
        share = len(made) / n
        team_pts_when_made = sum(h.points[h.maker_team] for h in made) / len(made) if made else 0.0
        print(f"{POSITION_NAMES[pos]:38s} {share:>25.1%}  {team_pts_when_made:>27.3f}")

    print("\n=== Round the trump was decided in (1 = ordered up turned card, 2 = called) ===")
    for rnd in (1, 2):
        sub = [h for h in hands if h.order_round == rnd]
        if not sub:
            continue
        euchre_rate = sum(1 for h in sub if h.euchred) / len(sub)
        maker_pts = sum(h.points[h.maker_team] for h in sub) / len(sub)
        print(f"round {rnd}: {len(sub)/n:.1%} of hands, maker euchred {euchre_rate:.1%} of the time, "
              f"maker points/hand {maker_pts:.3f}")


if __name__ == "__main__":
    main()
