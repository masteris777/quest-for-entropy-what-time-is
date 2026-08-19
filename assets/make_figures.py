"""Figures for Quest for Entropy #12, "What Time Is".

    python make_figures.py          # writes hero.png next to this file

hero.png   one wide image, two panels, the SAME thirteen events in both, drawn in
           the SAME coordinates - time runs upward on both sides, so the reader can
           compare them without rotating anything in their head.
           Left  - the engineer's vocabulary: cause, effect, independent, and the
                   vector stamps he actually reads them off. His region boundary is
                   feathered: it is only as sharp as his messages happen to be.
           Right - the physicist's vocabulary: past light cone, future light cone,
                   elsewhere. Same events, same wedges, one thing added - a speed
                   limit, so his boundary closes at exactly 45 degrees.
           Nothing moves between the panels. Only the names change, and the edge
           gets sharp. That is the whole argument of the picture.
           (Distributed-systems papers usually draw this sideways, with time running
           left to right. That convention is dropped here on purpose: it makes the
           reader perform a quarter turn before they can compare the two panels.)

Light theme on purpose - the Substack page is white.

The event history is checked, not just drawn: the script asserts that no message is
superluminal, and that the vector-clock comparison (Fidge/Mattern) puts every event in
exactly the region the light cone puts it in. The two vocabularies agree by
construction, which is the whole claim of the picture.
"""

from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent


def save(fig, name, dpi):
    """Write an opaque RGB PNG - the Substack page is white, nothing should be see-through."""
    path = HERE / name
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)
    try:
        from PIL import Image
        im = Image.open(path)
        if im.mode != "RGB":
            flat = Image.new("RGB", im.size, "white")
            flat.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
            flat.save(path)
    except ImportError:
        pass
    return path

# ---------------------------------------------------------------- palette (light)
INK = "#1b1d24"
MUTED = "#767b87"
LINE = "#343842"          # process lines / worldlines
MSG = "#565a66"           # messages

CAUSE_TXT = "#2d55a8"
EFFECT_TXT = "#a85a17"
INDEP_TXT = "#787f8c"
FOCUS = "#7a3fc0"

# the wedges are painted as a gradient, not flat fill: these are the colours at full
# strength, right at the event, and A_NEAR/A_FAR is how much of them survives with
# distance from it.
CAUSE_DEEP = (0.722, 0.804, 0.941)
EFFECT_DEEP = (0.949, 0.812, 0.643)
INDEP_DEEP = (0.902, 0.906, 0.918)
FOCUS_RGB = (0.478, 0.247, 0.753)
A_NEAR, A_FAR = 0.95, 0.33

MONO = "DejaVu Sans Mono"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "text.color": INK,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})

# ------------------------------------------------------------------- the history
# Physicist coordinates: x = space, t = time, light travels one unit of x per unit of t.
XP = {"A": 0.0, "B": 2.0, "C": 4.0}
ORDER = ["A", "B", "C"]

EVENTS = {
    "a1": ("A", 0.8), "a2": ("A", 3.0), "a3": ("A", 5.0), "a4": ("A", 8.0),
    "b1": ("B", 1.6), "b2": ("B", 3.6), "F": ("B", 5.0), "b4": ("B", 8.6),
    "c1": ("C", 1.4), "c2": ("C", 4.2), "c3": ("C", 7.0), "c4": ("C", 9.0),
}
MESSAGES = [("c1", "b2"), ("a2", "F"), ("F", "c3"), ("F", "a4"), ("a3", "c4"), ("c2", "b4")]
FOCUS_EV = "F"

# the square each panel occupies, in physicist coordinates
FX, FT = XP[EVENTS[FOCUS_EV][0]], EVENTS[FOCUS_EV][1]
HALF = 4.9
XLO, XHI = FX - HALF, FX + HALF          # -2.9 .. 6.9
TLO, THI = FT - HALF, FT + HALF          #  0.1 .. 9.9
# F sits dead centre, so the four causal regions are exactly the square's four
# diagonal quarters - the cleanest possible statement of the same picture twice.


def pos(ev):
    proc, t = EVENTS[ev]
    return XP[proc], t


def vector_clocks():
    """Fidge/Mattern stamps: own count, plus the highest count heard from everyone else."""
    recv = {b: a for a, b in MESSAGES}
    sent = {}
    clock = {p: [0, 0, 0] for p in ORDER}
    stamps = {}
    for ev in sorted(EVENTS, key=lambda e: EVENTS[e][1]):
        proc = EVENTS[ev][0]
        if ev in recv:
            other = sent[recv[ev]]
            clock[proc] = [max(a, b) for a, b in zip(clock[proc], other)]
        clock[proc][ORDER.index(proc)] += 1
        stamps[ev] = tuple(clock[proc])
        sent[ev] = tuple(clock[proc])
    return stamps


STAMPS = vector_clocks()


def _leq(u, v):
    return all(a <= b for a, b in zip(u, v))


def check():
    """No message beats light, and bookkeeping agrees with geometry for every event."""
    for a, b in MESSAGES:
        (xa, ta), (xb, tb) = pos(a), pos(b)
        assert tb - ta >= abs(xb - xa) - 1e-9, f"superluminal message {a}->{b}"
    f = STAMPS[FOCUS_EV]
    for ev in EVENTS:
        if ev == FOCUS_EV:
            continue
        x, t = pos(ev)
        dt, dx = t - FT, abs(x - FX)
        geom = "future" if dt >= dx else ("past" if -dt >= dx else "elsewhere")
        s = STAMPS[ev]
        book = "past" if _leq(s, f) else ("future" if _leq(f, s) else "elsewhere")
        assert geom == book, f"{ev}: cone says {geom}, stamps say {book}"


check()

# stamps worth printing on the engineer's panel: one per region, plus the focus
SHOWN = {
    "a2": (-1.06, 0.00),        # comparable, and it caused F
    "F": (0.00, -0.98),
    "c2": (+1.06, 0.00),        # incomparable with F: no fact about which came first
    "c3": (-1.06, 0.00),        # comparable, and F caused it
}


# --------------------------------------------------------------------- hero.png
def field(softness, nx=820):
    """The four causal regions of F, painted as one soft image.

    Colour says which region a point is in; the paint fades with distance from F,
    so the eye is pulled to the event the whole picture is about. `softness` is the
    width of the boundary: the physicist has a speed limit, so his edge is a hard
    line; the engineer's boundary is only as sharp as his messages happen to be,
    so his is feathered. Same regions, different confidence about where they end.
    """
    xs = np.linspace(XLO, XHI, nx)
    ts = np.linspace(TLO, THI, nx)
    X, T = np.meshgrid(xs, ts)
    dx, dt = np.abs(X - FX), T - FT

    s = max(softness, 1e-3)
    w_fut = 1.0 / (1.0 + np.exp(-(dt - dx) / s))
    w_past = 1.0 / (1.0 + np.exp(-(-dt - dx) / s))
    w_else = np.clip(1.0 - w_fut - w_past, 0.0, 1.0)
    total = w_fut + w_past + w_else

    rgb = np.zeros(X.shape + (3,))
    for w, col in ((w_fut, EFFECT_DEEP), (w_past, CAUSE_DEEP), (w_else, INDEP_DEEP)):
        rgb += (w / total)[..., None] * np.array(col)

    r = np.hypot(X - FX, T - FT)
    alpha = (A_FAR + (A_NEAR - A_FAR) * np.exp(-r / 3.6))[..., None]
    out = 1.0 - alpha * (1.0 - rgb)

    glow = (0.17 * np.exp(-(r / 0.80) ** 2))[..., None]
    out = out * (1 - glow) + np.array(FOCUS_RGB) * glow

    rng = np.random.default_rng(7)
    out += rng.normal(0.0, 0.0018, out.shape)      # a little paper grain
    return np.clip(out, 0.0, 1.0)


def spaced(text):
    return "\u2009".join(text.upper())


def hero():
    figw, figh, dpi = 10.6667, 6.0, 150            # 1600 x 900
    fig = plt.figure(figsize=(figw, figh), dpi=dpi)

    pw, ph = 700 / (figw * dpi), 700 / (figh * dpi)
    y0 = 0.118
    rects = [(0.035, y0, pw, ph), (1 - 0.035 - pw, y0, pw, ph)]

    for rect, mode in zip(rects, ["eng", "phys"]):
        draw_panel(fig.add_axes(rect), mode)

    for rect, title in zip(rects, ["what a distributed system sees", "what a physicist sees"]):
        fig.text(rect[0] + rect[2] / 2, y0 + ph + 0.042, spaced(title),
                 ha="center", va="center", fontsize=10.5, weight="bold", color="#4c505b")

    fig.add_artist(Line2D([0.5, 0.5], [y0 + 0.02, y0 + ph - 0.02],
                          color="#e7e4de", lw=1.0, zorder=0))

    fig.text(0.5, 0.048, "same picture, two vocabularies",
             ha="center", va="center", fontsize=15.5, color="#5a5e69", style="italic")

    save(fig, "hero.png", dpi)


def draw_panel(ax, mode):
    eng = mode == "eng"
    halo = [pe.withStroke(linewidth=3.2, foreground="white")]

    ax.set_xlim(XLO, XHI)
    ax.set_ylim(TLO, THI)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.imshow(field(0.55 if eng else 0.035), extent=(XLO, XHI, TLO, THI),
              origin="lower", interpolation="bilinear", zorder=0)

    # the physicist's panel has one thing the engineer's has not: a speed limit,
    # so his regions close at exactly 45 degrees and the edge is a drawn line.
    if not eng:
        for cx, cy in [(XLO, TLO), (XHI, TLO), (XLO, THI), (XHI, THI)]:
            ax.plot([FX, cx], [FT, cy], color="#9aa0ac", lw=1.0, zorder=1)
        ax.text(5.95, 8.30, "45°", fontsize=9.5, color="#8d7a63", ha="left", va="center",
                zorder=6, path_effects=halo)

    labels = [
        ((-1.05, 1.32), "cause" if eng else "past\nlight cone", CAUSE_TXT),
        ((-1.05, 8.68), "effect" if eng else "future\nlight cone", EFFECT_TXT),
        ((-1.75, 6.55), "independent" if eng else "elsewhere", INDEP_TXT),
        ((5.75, 6.55), "independent" if eng else "elsewhere", INDEP_TXT),
    ]
    for (x, t), txt, col in labels:
        ax.text(x, t, txt, ha="center", va="center", fontsize=11.5, color=col,
                linespacing=1.3, zorder=6, path_effects=halo)

    # process lines / worldlines
    for p in ORDER:
        x = XP[p]
        ax.plot([x, x], [0.35, 9.80], color=LINE, lw=2.2, solid_capstyle="round",
                zorder=3, path_effects=[pe.withStroke(linewidth=5.0, foreground="white")])
        ax.text(x, 0.05, p, ha="center", va="center", fontsize=13, weight="bold",
                color=LINE, zorder=6, path_effects=halo)

    for a, b in MESSAGES:
        ax.annotate("", xy=pos(b), xytext=pos(a), zorder=4,
                    arrowprops=dict(arrowstyle="-|>", color=MSG, lw=1.5,
                                    shrinkA=6, shrinkB=7, mutation_scale=13,
                                    path_effects=[pe.withStroke(linewidth=3.4,
                                                                foreground="white")]))

    for ev in EVENTS:
        px, py = pos(ev)
        if ev == FOCUS_EV:
            for ms, al in ((26, 0.16), (21, 0.26)):
                ax.plot([px], [py], "o", ms=ms, color=FOCUS, alpha=al, mec="none", zorder=5)
            ax.plot([px], [py], "o", ms=11.5, color=FOCUS, mec="white", mew=2.0, zorder=6)
        else:
            ax.plot([px], [py], "o", ms=7.0, color=INK, mec="white", mew=1.3, zorder=5)

    ax.text(FX + 0.42, FT + 0.52, "this event", ha="left", va="center", fontsize=9.5,
            color=FOCUS, zorder=7, path_effects=halo)

    # vector stamps live on the engineer's panel only - that is his instrument
    if eng:
        for ev, (dx, dy) in SHOWN.items():
            px, py = pos(ev)
            focus = ev == FOCUS_EV
            ax.text(px + dx, py + dy, "A:{} B:{} C:{}".format(*STAMPS[ev]),
                    ha="center", va="center", fontsize=9, family=MONO,
                    color=FOCUS if focus else "#3c4049", zorder=7,
                    bbox=dict(facecolor="white", edgecolor=FOCUS if focus else "#dcd9d3",
                              boxstyle="round,pad=0.26", lw=0.9, alpha=0.94))

    # time direction - drawn identically in both panels, which is the point
    ax.annotate("", xy=(-2.60, 3.05), xytext=(-2.60, 0.75),
                arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.2, mutation_scale=11))
    ax.text(-2.60, 3.30, "time", ha="center", va="bottom", fontsize=10.5,
            color=MUTED, rotation=90, path_effects=halo)


if __name__ == "__main__":
    hero()
    print("stamps:", {k: STAMPS[k] for k in sorted(STAMPS)})
    print("wrote assets/hero.png")
