"""The two numbers the article states, measured rather than asserted.

    python sweep.py              500 seeds x 8 slider settings = 4,000 worlds
    python sweep.py --quick      50 seeds, for a fast check

Two questions, one sweep:

1. Does turning the message slider change how much of the world has an order at
   all? (It should: more news travelling means more pairs with a cause between
   them, and fewer pairs that are merely concurrent.)

2. Can two observers who disagree about the order ever disagree about a CAUSAL
   pair? (They must not. Ever. Not once in four thousand worlds. If this number
   is not zero the whole article is wrong.)

Writes metrics_sweep.json.
"""

import argparse
import json
import statistics
from pathlib import Path

from two_observers import build_world, compare_logs, pair_stats, two_orders

HERE = Path(__file__).resolve().parent
RATES = [k / 7 for k in range(8)]          # eight settings, slack to chatty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="50 seeds instead of 500")
    args = ap.parse_args()
    n_seeds = 50 if args.quick else 500

    per_rate, causal_swaps, total_pairs, swapped_pairs, worlds = {}, 0, 0, 0, 0

    for rate in RATES:
        fracs = []
        for i in range(n_seeds):
            seed = str(100000 + i)
            w = build_world(seed, rate)
            st = pair_stats(w)
            fracs.append(st["frac"])
            total_pairs += st["total"]

            o1, o2 = two_orders(w, seed)
            cmp_ = compare_logs(w, o1, o2)
            swapped_pairs += cmp_["swapped"]
            causal_swaps += cmp_["causally_swapped"]
            worlds += 1
        per_rate[round(rate, 4)] = dict(
            mean_concurrent_frac=statistics.mean(fracs),
            median_concurrent_frac=statistics.median(fracs))
        print("slider {:.2f}   {:5.1f}% of pairs concurrent (mean over {} worlds)".format(
            rate, 100 * per_rate[round(rate, 4)]["mean_concurrent_frac"], n_seeds))

    lo = per_rate[round(RATES[0], 4)]["mean_concurrent_frac"]
    hi = per_rate[round(RATES[-1], 4)]["mean_concurrent_frac"]

    print()
    print("worlds generated              {}".format(worlds))
    print("event pairs compared          {}".format(total_pairs))
    print("pairs the two observers")
    print("  wrote in opposite orders    {}".format(swapped_pairs))
    print("  ...that were causal         {}   <- must be zero".format(causal_swaps))
    print()
    print("slider down: {:.0f}% of pairs have no order at all".format(100 * lo))
    print("slider up:   {:.0f}%".format(100 * hi))

    out = dict(
        worlds=worlds, seeds_per_rate=n_seeds, rates=RATES,
        per_rate=per_rate,
        event_pairs_compared=total_pairs,
        pairs_ordered_differently=swapped_pairs,
        causally_related_pairs_swapped=causal_swaps,
        concurrent_frac_slider_down=lo,
        concurrent_frac_slider_up=hi)
    (HERE / "metrics_sweep.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote metrics_sweep.json")


if __name__ == "__main__":
    main()
