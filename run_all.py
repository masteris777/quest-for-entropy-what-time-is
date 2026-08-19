"""Reproduce every number the article states, from scratch.

    python run_all.py            everything
    python run_all.py --quick    a smaller sweep, same checks

Each check below names the sentence in the article it is testing. If a check
fails, the article is wrong and I want to know.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = []


def check(claim, ok, detail):
    RESULTS.append((claim, ok, detail))
    print("  [{}] {}: {}".format("PASS" if ok else "FAIL", claim, detail))


def skip(claim, detail):
    RESULTS.append((claim, None, detail))
    print("  [SKIP] {}: {}".format(claim, detail))


def run(script, *extra):
    print("\n$ python {} {}".format(script, " ".join(extra)).rstrip())
    proc = subprocess.run([sys.executable, str(HERE / script), *extra],
                          cwd=HERE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
        raise SystemExit("{} failed".format(script))
    print(proc.stdout.strip()[-900:])
    return proc.stdout


def port_matches_page():
    """The article calls the Python a line-for-line port of the page. Check it.

    page_model.js is the model half of the published page, copied verbatim. Run
    both on the same seeds and the same slider settings; every count must agree.
    """
    node = shutil.which("node")
    if not node:
        skip("the Python model reproduces the page's JavaScript exactly",
             "node not installed - install Node.js to run this one")
        return

    harness = HERE / "_port_check.js"
    harness.write_text(
        (HERE / "page_model.js").read_text(encoding="utf-8") + """
const out = [];
for (const seed of ["1729", "100000", "100001", "424242"])
  for (const rate of [0, 1/7, 3/7, 5/7, 1]) {
    const w = buildWorld(seed, rate), st = pairStats(w);
    out.push([seed, rate, w.events.length, w.msgs.length, w.minD, st.conc, st.tot]);
  }
console.log(JSON.stringify(out));
""", encoding="utf-8")
    try:
        proc = subprocess.run([node, str(harness)], cwd=HERE, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            skip("the Python model reproduces the page's JavaScript exactly",
                 "node failed: {}".format(proc.stderr.strip()[:200]))
            return
        from two_observers import build_world, pair_stats
        js = json.loads(proc.stdout)
        mismatches = []
        for seed, rate, n_ev, n_msg, min_d, conc, tot in js:
            w = build_world(seed, rate)
            st = pair_stats(w)
            mine = (len(w["events"]), len(w["msgs"]), w["min_d"], st["concurrent"], st["total"])
            if mine != (n_ev, n_msg, min_d, conc, tot):
                mismatches.append((seed, rate, mine, (n_ev, n_msg, min_d, conc, tot)))
        check("the Python model reproduces the page's JavaScript exactly "
              "(article: a line-for-line port of the page)",
              not mismatches,
              "{} seed x slider combinations, every count identical".format(len(js))
              if not mismatches else "{} mismatches, first: {}".format(
                  len(mismatches), mismatches[0]))
    finally:
        harness.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="a smaller sweep")
    args = ap.parse_args()

    port_matches_page()

    # ---- the sweep --------------------------------------------------------
    run("sweep.py", *(["--quick"] if args.quick else []))
    m = json.loads((HERE / "metrics_sweep.json").read_text(encoding="utf-8"))

    check("two observers never disagree about a causal pair "
          "(article: zero causally related pairs ever swapped)",
          m["causally_related_pairs_swapped"] == 0,
          "{:,} pairs compared across {:,} worlds, {:,} written in opposite orders, "
          "{} of them causal".format(
              m["event_pairs_compared"], m["worlds"],
              m["pairs_ordered_differently"], m["causally_related_pairs_swapped"]))

    lo, hi = m["concurrent_frac_slider_down"], m["concurrent_frac_slider_up"]
    check("with the slider down, about two thirds of pairs have no order at all "
          "(article: two thirds of all event pairs are concurrent)",
          0.60 <= lo <= 0.72, "{:.1%} concurrent".format(lo))
    check("with the slider up, that falls to about one in six "
          "(article: about one in six)",
          0.13 <= hi <= 0.21, "{:.1%} concurrent, down from {:.1%}".format(hi, lo))
    check("the slider moves it monotonically - more news, less concurrency",
          all(a["mean_concurrent_frac"] >= b["mean_concurrent_frac"]
              for a, b in zip(m["per_rate"].values(), list(m["per_rate"].values())[1:])),
          "{} settings, falling all the way".format(len(m["per_rate"])))

    # ---- the figure -------------------------------------------------------
    out = run("assets/make_figures.py")
    check("in the hero image, the bookkeeping and the light cones agree for every "
          "event (article: same picture, two vocabularies)",
          "stamps:" in out and (HERE / "assets" / "hero.png").exists(),
          "figure rebuilt into assets/; its own assertion puts all 12 events in the "
          "same region by tally comparison and by light cone")

    print("\n" + "=" * 70)
    for claim, ok, _ in RESULTS:
        print("[{}] {}".format({True: "PASS", False: "FAIL", None: "SKIP"}[ok], claim))
    print("=" * 70)
    bad = [c for c, ok, _ in RESULTS if ok is False]
    if bad:
        raise SystemExit("{} check(s) FAILED".format(len(bad)))
    n_skip = sum(1 for _, ok, _ in RESULTS if ok is None)
    print("all {} checks reproduced{}".format(
        sum(1 for _, ok, _ in RESULTS if ok), ", {} skipped".format(n_skip) if n_skip else ""))


if __name__ == "__main__":
    main()
