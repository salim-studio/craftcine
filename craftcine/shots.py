"""CraftCine shot library — 30 curated motion recipes for product promos.

Each entry maps 1:1 to a compositor routine in compositor.py.
"""
from __future__ import annotations

SHOTS = {
    # ---- openers ----
    "fade-in": {"cat": "opener", "energy": 1, "dur": 2.0, "ease": "out",
                "desc": "Quiet fade + slow push. Use for the brand open.",
                "params": {"scale_from": 1.06, "scale_to": 1.0}},
    "iris-open": {"cat": "opener", "energy": 2, "dur": 2.2, "ease": "inout",
                  "desc": "Circular iris reveals the hero. Cinematic open.",
                  "params": {"iris_feather": 60}},
    "typewriter": {"cat": "opener", "energy": 2, "dur": 3.0, "ease": "linear",
                   "desc": "Char-by-char title reveal. Manifesto / statement.",
                   "params": {"cps": 18}},
    # ---- hero / product ----
    "spotlight-hero": {"cat": "hero", "energy": 3, "dur": 4.0, "ease": "spring",
                       "desc": "Single hero card: gather -> push -> float -> settle. The money shot.",
                       "params": {"push": 0.12, "float_amp": 10}},
    "zoom-push": {"cat": "hero", "energy": 3, "dur": 3.2, "ease": "expo",
                  "desc": "Camera pushes into the product card. Feature reveal.",
                  "params": {"zoom": 1.35}},
    "orbit-tilt": {"cat": "hero", "energy": 4, "dur": 3.5, "ease": "inout",
                   "desc": "Slight 2.5D orbit around a close-up. Premium feel.",
                   "params": {"tilt_deg": 8}},
    "kenburns": {"cat": "hero", "energy": 2, "dur": 4.0, "ease": "linear",
                 "desc": "Slow pan + zoom. A breathing moment.",
                 "params": {"pan_px": 60, "zoom": 1.12}},
    "parallax-float": {"cat": "hero", "energy": 2, "dur": 3.5, "ease": "inout",
                       "desc": "Two depth layers drift in opposite directions. Dreamy hold.",
                       "params": {"layers": 2, "amp": 24}},
    # ---- features / lists ----
    "deck-deal-flyin": {"cat": "feature", "energy": 4, "dur": 3.0, "ease": "expo",
                        "desc": "Cards fly in like a dealt deck. Feature batch intro.",
                        "params": {"n": 3, "stagger": 0.12}},
    "row-embed": {"cat": "feature", "energy": 3, "dur": 3.0, "ease": "out",
                  "desc": "Rows slide in and embed into a panel. Dense UI showcase.",
                  "params": {"n": 4}},
    "stack-cards": {"cat": "feature", "energy": 3, "dur": 3.0, "ease": "back",
                    "desc": "Cards stack with overshoot. Steps / process.",
                    "params": {"n": 3, "offset": 26}},
    "grid-stagger": {"cat": "feature", "energy": 3, "dur": 2.8, "ease": "out",
                     "desc": "2x2 grid staggers in. Integrations / logo wall.",
                     "params": {"cols": 2, "rows": 2}},
    "split-reveal": {"cat": "feature", "energy": 3, "dur": 2.5, "ease": "inout",
                     "desc": "Wipe split reveals before/after. Comparison.",
                     "params": {"direction": "horizontal"}},
    # ---- data ----
    "digit-roll": {"cat": "data", "energy": 3, "dur": 2.5, "ease": "expo",
                   "desc": "Number rolls up to a target. Stats / metrics.",
                   "params": {"value": 128}},
    "ticker-wall": {"cat": "data", "energy": 4, "dur": 3.0, "ease": "linear",
                    "desc": "Infinite vertical ticker. Log / activity feed.",
                    "params": {"rows": 6, "speed": 220}},
    # ---- camera ----
    "page-pan": {"cat": "camera", "energy": 2, "dur": 3.5, "ease": "inout",
                 "desc": "Slow pan across a full-page capture texture.",
                 "params": {"pan_px": 160}},
    "page-zoom": {"cat": "camera", "energy": 3, "dur": 3.0, "ease": "expo",
                  "desc": "Zoom from full page to one element. Real-UI proof.",
                  "params": {"zoom": 1.6}},
    # ---- text ----
    "caption-pop": {"cat": "title", "energy": 2, "dur": 2.2, "ease": "back",
                    "desc": "Caption pops under the card. One message per shot.",
                    "params": {"y_from": 30}},
    "logo-hold": {"cat": "title", "energy": 1, "dur": 2.5, "ease": "out",
                  "desc": "Logo locks and holds >= 1s. Mandatory end breather.",
                  "params": {"hold": 1.0}},
    "cta-pulse": {"cat": "cta", "energy": 3, "dur": 2.5, "ease": "spring",
                   "desc": "CTA button pulses once. Final conversion shot.",
                   "params": {"pulses": 1}},
    # ---- transitions ----
    "flash-cut": {"cat": "transition", "energy": 5, "dur": 0.6, "ease": "linear",
                  "desc": "2-frame white flash cut. Beat cuts only (<= 3 per film).",
                  "params": {}},
    "slide-left": {"cat": "transition", "energy": 3, "dur": 1.2, "ease": "inout",
                   "desc": "Card slides left, next enters. Workhorse transition.",
                   "params": {}},
    "slide-up": {"cat": "transition", "energy": 3, "dur": 1.2, "ease": "out",
                 "desc": "Rise transition. Section change.",
                 "params": {}},
    "glitch-cut": {"cat": "transition", "energy": 5, "dur": 0.8, "ease": "linear",
                   "desc": "RGB-split hard cut. Tech / edgy beats only.",
                   "params": {"slices": 6}},
    # ---- second-wave additions ----
    "rise-in": {"cat": "title", "energy": 2, "dur": 2.4, "ease": "back",
                "desc": "Card rises with overshoot. Statement / chapter card.",
                "params": {"rise_px": 120}},
    "zoom-out": {"cat": "hero", "energy": 3, "dur": 3.2, "ease": "inout",
                 "desc": "Close-up pulls back to wide. Context reveal.",
                 "params": {"zoom": 1.6}},
    "slide-right": {"cat": "transition", "energy": 3, "dur": 1.2, "ease": "inout",
                    "desc": "Card slides right, next enters. Mirror of slide-left.",
                    "params": {}},
    "card-flip": {"cat": "feature", "energy": 4, "dur": 2.2, "ease": "back",
                  "desc": "Card flips in on its vertical axis. Surprise reveal.",
                  "params": {}},
    "stat-trio": {"cat": "data", "energy": 3, "dur": 3.0, "ease": "out",
                  "desc": "Three stat cards stagger in with rolling numbers. KPI wall.",
                  "params": {"values": [42, 68, 95]}},
    "quote-card": {"cat": "title", "energy": 2, "dur": 3.0, "ease": "out",
                   "desc": "Centered testimonial card. Title is the quote, subtitle the author.",
                   "params": {}},
}

CATEGORIES = sorted({v["cat"] for v in SHOTS.values()})


def get(name: str) -> dict:
    key = (name or "").lower().strip().replace(" ", "-").replace("_", "-")
    if key not in SHOTS:
        raise KeyError(f"unknown shot '{name}'. Available: {', '.join(sorted(SHOTS))}")
    return {"name": key, **SHOTS[key]}


def search(cat: str = "", energy: int = 0) -> list[dict]:
    out = []
    for k, v in SHOTS.items():
        if cat and v["cat"] != cat:
            continue
        if energy and v["energy"] != energy:
            continue
        out.append({"name": k, **v})
    return out
