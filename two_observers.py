"""The world model behind the two-observers toy, ported to Python.

    python two_observers.py        prints three worlds and their numbers

This is a line-for-line port of the JavaScript running the interactive page: the
same generator, the same random source, the same vector clocks. Same seed and
same slider setting give the same world in both, so anything measured here is a
measurement of the toy on the page and not of a lookalike written afterwards.

Three processes take turns for fifteen steps. A process either does something on
its own, or sends news to another, or reads its inbox. Nobody has a clock. All
anybody keeps is a tally: my own count, plus the highest count I have heard from
everyone else. That tally is a vector clock (Fidge and Mattern, 1988), and
comparing two of them is the whole of causality here:

    e happened before f     every entry of e's tally is <= f's
    e and f are concurrent  neither tally covers the other
"""

import math

MASK = 0xFFFFFFFF
NP, STEPS, ACT = 3, 15, 0.62


def _mul32(a, b):
    """Math.imul: the low 32 bits of the product, which are the same signed or not."""
    return (a * b) & MASK


def mulberry32(seed):
    """The page's random source, bit for bit."""
    state = seed & MASK

    def rnd():
        nonlocal state
        state = (state + 0x6D2B79F5) & MASK
        t = _mul32(state ^ (state >> 15), 1 | state)
        t = ((t + _mul32(t ^ (t >> 7), 61 | t)) & MASK) ^ t
        return ((t ^ (t >> 14)) & MASK) / 4294967296

    return rnd


def hash_seed(s):
    """FNV-1a over the seed string, as the page does it."""
    h = 2166136261
    for ch in str(s):
        h = _mul32(h ^ ord(ch), 16777619)
    return h & MASK


def jround(x):
    """JavaScript Math.round: halves go up, not to even."""
    return math.floor(x + 0.5)


def draw_dice(seed):
    """Every random number is drawn once, before the slider is applied, so moving
    the slider reshapes the same world instead of rolling a new one."""
    r = mulberry32(hash_seed(seed))
    return [[dict(act=r(), send=r(), dest=r(), delay=r(), both=r(), delay2=r())
             for _ in range(NP)] for _ in range(STEPS)]


def build_world(seed, rate):
    dice = draw_dice(seed)
    send_prob = 0.05 + 0.88 * rate              # more messages as the slider rises
    min_d = max(1, jround(3 - 2 * rate))        # the fastest a message can possibly be
    extra = max(1, jround(5 - 4 * rate))        # spread of delays above that floor
    both_prob = max(0.0, (rate - 0.35) / 0.65)  # eventually one send reaches everyone

    V = [[0] * NP for _ in range(NP)]
    events, msgs, flight = [], [], []

    for s in range(STEPS):
        busy = [False] * NP

        # Deliveries first. A process reads its whole inbox in one event: it ticks
        # its own counter once, then takes the entry-wise maximum over everything
        # that landed. One event per process per step, no more.
        for q in range(NP):
            inbox = [m for m in flight if m["to"] == q and m["at"] <= s]
            if not inbox:
                continue
            busy[q] = True
            V[q][q] += 1
            for m in inbox:
                for k in range(NP):
                    V[q][k] = max(V[q][k], m["V"][k])
            ev = dict(id=len(events), p=q, step=s, kind="recv", V=V[q][:], c=V[q][q])
            events.append(ev)
            for m in inbox:
                m["done"] = True
                msgs.append((m["src"], ev["id"]))
        flight = [m for m in flight if not m.get("done")]

        # then each idle process may do a local event, possibly a send
        for p in range(NP):
            if busy[p]:
                continue
            u = dice[s][p]
            if u["act"] >= ACT:
                continue
            V[p][p] += 1
            sending = s < STEPS - min_d and u["send"] < send_prob
            ev = dict(id=len(events), p=p, step=s, kind="send" if sending else "local",
                      V=V[p][:], c=V[p][p])
            events.append(ev)
            if not sending:
                continue
            q = (p + 1 + int(u["dest"] * (NP - 1))) % NP
            at = s + min_d + int(u["delay"] * extra)
            any_sent = False
            if at < STEPS:
                flight.append(dict(to=q, at=at, src=ev["id"], V=ev["V"][:]))
                any_sent = True
            if u["both"] < both_prob:           # same news, sent to the third process too
                q2 = 3 - p - q
                at2 = s + min_d + int(u["delay2"] * extra)
                if at2 < STEPS:
                    flight.append(dict(to=q2, at=at2, src=ev["id"], V=ev["V"][:]))
                    any_sent = True
            if not any_sent:
                ev["kind"] = "local"

    landed = {a for a, _ in msgs}               # a send nobody received is a local event
    for e in events:
        if e["kind"] == "send" and e["id"] not in landed:
            e["kind"] = "local"

    by_proc = [[e for e in events if e["p"] == p] for p in range(NP)]
    return dict(events=events, msgs=msgs, min_d=min_d, by_proc=by_proc)


# ---- the causal order, read straight off the tallies -----------------------
def leq(a, b):
    return all(x <= y for x, y in zip(a, b))


def concurrent(e, f):
    return not leq(e["V"], f["V"]) and not leq(f["V"], e["V"])


def pair_stats(w):
    """What fraction of all event pairs have no order at all."""
    E = w["events"]
    tot = conc = 0
    for i in range(len(E)):
        for j in range(i + 1, len(E)):
            tot += 1
            if concurrent(E[i], E[j]):
                conc += 1
    return dict(total=tot, concurrent=conc, frac=conc / tot if tot else 0.0)


# ---- every legal way to write the history down -----------------------------
def build_dag(w):
    """Edges: program order along each process, plus every message (send -> receive).
    The transitive closure of those edges IS happens-before - the same relation the
    tallies compute - so any topological order of this graph respects every causal
    pair. The sweep checks that rather than assuming it."""
    n = len(w["events"])
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for lane in w["by_proc"]:
        for a, b in zip(lane, lane[1:]):
            adj[a["id"]].append(b["id"])
            indeg[b["id"]] += 1
    for a, b in w["msgs"]:
        adj[a].append(b)
        indeg[b] += 1
    return adj, indeg


def topo_sort(w, dag, pick):
    adj, indeg0 = dag
    indeg = indeg0[:]
    ready = [i for i, d in enumerate(indeg) if d == 0]
    out = []
    while ready:
        v = ready.pop(pick(ready, w))
        out.append(v)
        for u in adj[v]:
            indeg[u] -= 1
            if indeg[u] == 0:
                ready.append(u)
    return out


def pick_natural(ready, w):
    """Observer 1: the obvious wall-clock reading - earliest step, then A, B, C."""
    best, k = math.inf, 0
    for i, eid in enumerate(ready):
        e = w["events"][eid]
        key = e["step"] * 10 + e["p"]
        if key < best:
            best, k = key, i
    return k


def compare_logs(w, o1, o2):
    """How many pairs the two observers write down in opposite orders - and how many
    of those were causally related, which must be none."""
    n = len(w["events"])
    p1, p2 = [0] * n, [0] * n
    for i, eid in enumerate(o1):
        p1[eid] = i
    for i, eid in enumerate(o2):
        p2[eid] = i
    swapped = bad = 0
    for i in range(n):
        for j in range(i + 1, n):
            if (p1[i] < p1[j]) != (p2[i] < p2[j]):
                swapped += 1
                if not concurrent(w["events"][i], w["events"][j]):
                    bad += 1
    return dict(swapped=swapped, causally_swapped=bad)


def two_orders(w, seed, reroll=1):
    """Observer 1 reads it the obvious way; observer 2 is handed a different legal order."""
    dag = build_dag(w)
    o1 = topo_sort(w, dag, pick_natural)
    r = mulberry32(hash_seed("{}:{}".format(seed, reroll)))
    o2 = o1
    for _ in range(12):
        o2 = topo_sort(w, dag, lambda ready, _w: int(r() * len(ready)))
        if o2 != o1:
            break
    return o1, o2


if __name__ == "__main__":
    for rate in (0.0, 0.5, 1.0):
        w = build_world("1729", rate)
        st = pair_stats(w)
        o1, o2 = two_orders(w, "1729")
        cmp_ = compare_logs(w, o1, o2)
        print("slider {:.2f}: {:2d} events, {:2d} messages, fastest message {} step(s), "
              "{:5.1f}% of pairs concurrent, {:3d} pairs written in a different order "
              "({} of them causal)".format(
                  rate, len(w["events"]), len(w["msgs"]), w["min_d"],
                  100 * st["frac"], cmp_["swapped"], cmp_["causally_swapped"]))
