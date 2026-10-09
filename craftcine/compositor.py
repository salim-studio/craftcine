"""CraftCine compositor — Pillow 2.5D renderer. Fast, dependency-light, deterministic."""
from __future__ import annotations
import math
import os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from . import easing as E
from . import themes as T

_FONT_CACHE: dict[int, object] = {}


def _font(size: int):
    size = max(10, int(size))
    if size not in _FONT_CACHE:
        try:
            _FONT_CACHE[size] = ImageFont.load_default(size=size)
        except TypeError:
            _FONT_CACHE[size] = ImageFont.load_default()
    return _FONT_CACHE[size]


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _card_base(cw: int, ch: int, theme: dict, accent_top: bool = True) -> Image.Image:
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    r = min(36, cw // 18, ch // 10)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=r, fill=_hex(theme["surface"]) + (255,))
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=r, outline=_hex(theme["accent"]) + (255,), width=3)
    if accent_top:
        d.rounded_rectangle([0, 0, cw - 1, max(8, ch // 18)], radius=r, fill=_hex(theme["accent"]) + (255,))
    # fake UI dots
    for i, col in enumerate([(255, 90, 90), (255, 200, 80), (90, 220, 140)]):
        x = 24 + i * 28
        d.ellipse([x, ch // 18 + 18, x + 14, ch // 18 + 32], fill=col + (255,))
    # fake text lines inside card
    lw = int(cw * 0.7)
    y0 = int(ch * 0.42)
    muted = _hex(theme["muted"]) + (255,)
    acc = _hex(theme["accent"]) + (255,)
    d.rounded_rectangle([cw // 2 - lw // 2, y0, cw // 2 + lw // 2, y0 + 12], radius=6, fill=muted)
    d.rounded_rectangle([cw // 2 - lw // 3, y0 + 26, cw // 2 + lw // 3, y0 + 38], radius=6, fill=acc)
    return card


def _paste_center(base: Image.Image, layer: Image.Image, cx: float, cy: float, scale: float = 1.0, alpha: int = 255):
    w, h = layer.size
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    if (nw, nh) != (w, h):
        layer = layer.resize((nw, nh), Image.BILINEAR)
    if alpha < 255:
        a = layer.split()[3].point(lambda v: v * alpha // 255)
        layer.putalpha(a)
    base.alpha_composite(layer, (int(cx - nw / 2), int(cy - nh / 2)))

def _text_center(base: Image.Image, text: str, cx: float, y: float, size: int, color: tuple, stroke: int = 0):
    if not text:
        return
    d = ImageDraw.Draw(base)
    f = _font(size)
    bbox = d.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    d.text((cx - tw / 2, y), text, font=f, fill=color + (255,) if len(color) == 3 else color,
           stroke_width=stroke, stroke_fill=(0, 0, 0, 180) if stroke else None)


_READERS: dict[str, object] = {}
_CLIP_INFO: dict[str, tuple] = {}


def _close_clip_readers():
    for r in list(_READERS.values()):
        try:
            r.close()
        except Exception:
            pass


def release_clip(path: str) -> None:
    """Close + forget a cached clip reader (needed before deleting on Windows)."""
    path = os.path.normpath(path)
    r = _READERS.pop(path, None)
    if r is not None:
        try:
            r.close()
        except Exception:
            pass
    _CLIP_INFO.pop(path, None)


import atexit as _atexit
_atexit.register(_close_clip_readers)


def clip_info(path: str) -> tuple[float, int, float]:
    """(fps, nframes, duration_sec) for a video file. Cached per file version."""
    import imageio.v2 as imageio
    path = os.path.normpath(path)
    st = os.stat(path)
    ver = (st.st_mtime_ns, st.st_size)
    hit = _CLIP_INFO.get(path)
    if hit and hit[0] == ver:
        return hit[1]
    r = imageio.get_reader(path)
    try:
        meta = r.get_meta_data() or {}
        fps = float(meta.get("fps") or 25.0)
        dur = meta.get("duration")
        n = meta.get("nframes")
        if dur is None:
            if n in (None, float("inf")):
                try:
                    n = r.count_frames()
                except Exception:
                    n = 0
            n = int(n or 0) or int(fps * 5)
            dur = n / fps
        else:
            dur = float(dur)
            n = int(n) if isinstance(n, (int, float)) and n not in (float("inf"),) else max(1, int(dur * fps))
    finally:
        try:
            r.close()
        except Exception:
            pass
    info = (fps, n, dur)
    _CLIP_INFO[path] = (ver, info)
    return info


def get_clip_frame(path: str, t: float):
    """One RGB frame from a video file at time t (loops). Numpy array."""
    import imageio.v2 as imageio
    path = os.path.normpath(path)
    fps, n, dur = clip_info(path)
    if dur <= 0 or n <= 0:
        raise ValueError(f"unreadable clip: {path}")
    idx = int((t % dur) * fps) % n
    r = _READERS.get(path)
    if r is None:
        r = imageio.get_reader(path)
        _READERS[path] = r
    try:
        return r.get_data(idx)
    except Exception:
        try:
            r.close()
        except Exception:
            pass
        r = imageio.get_reader(path)
        _READERS[path] = r
        return r.get_data(idx)


def render_frame(shot: str, t: float, W: int, H: int, theme_name: str = "ink_press",
                 title: str = "", subtitle: str = "", seed: int = 7,
                 value: int = 0, image: str | None = None,
                 values: list | None = None, clip=None) -> Image.Image:
    """Render one RGBA frame. t in 0..1, deterministic from (shot, seed).

    `image` is a still path, `clip` a video frame (numpy array). Clip wins.
    """
    t = max(0.0, min(1.0, t))
    theme = T.get(theme_name)
    bg, surf, txt, acc, mut = _hex(theme["bg"]), _hex(theme["surface"]), _hex(theme["text"]), _hex(theme["accent"]), _hex(theme["muted"])
    base = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(base)
    cx, cy = W / 2, H / 2 + E.handheld(t, seed) * 0.4

    cw, ch = int(W * 0.62), int(H * 0.46)
    card = _card_base(cw, ch, theme)

    # optional product visual: video clip frame wins, still image otherwise.
    # Either is cover-fit into the card body (window chrome stays on top).
    tex = None
    if clip is not None:
        try:
            import numpy as _np
            tex = Image.fromarray(_np.asarray(clip)).convert("RGB")
        except Exception:
            tex = None
    if tex is None and image and os.path.exists(str(image)):
        try:
            tex = Image.open(str(image)).convert("RGB")
        except Exception:
            tex = None
    if tex is not None:
        try:
            iw, ih = cw - 24, int(ch * 0.58)
            shot_img = ImageOps.fit(tex, (iw, ih), Image.LANCZOS).convert("RGBA")
            mask = Image.new("L", (iw, ih), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, iw - 1, ih - 1], radius=14, fill=255)
            card.paste(shot_img, (12, ch - ih - 12), mask)
        except Exception:
            pass

    # per-shot motion -------------------------------------------------------
    if shot == "fade-in":
        e = E.ease_out_cubic(t)
        _paste_center(base, card, cx, cy, 1.06 - 0.06 * e, int(255 * e))
    elif shot == "zoom-push":
        e = E.ease_out_expo(t)
        _paste_center(base, card, cx, cy, 0.85 + 0.5 * e, 255)
    elif shot == "spotlight-hero":
        e = E.damped_settle(t)
        glow_r = int(min(W, H) * (0.32 + 0.06 * math.sin(t * math.pi)))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r], fill=acc + (46,))
        base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
        _paste_center(base, card, cx, cy - 10 * math.sin(t * math.pi), 0.9 + 0.1 * e, 255)
    elif shot == "orbit-tilt":
        e = E.ease_in_out_cubic(t)
        off = (e - 0.5) * W * 0.08
        _paste_center(base, card, cx + off, cy, 0.95 + 0.08 * math.sin(t * math.pi), 255)
        d.line([0, H - 1, W * e, H - 1], fill=acc + (255,), width=6)
    elif shot == "kenburns":
        _paste_center(base, card, cx - 60 + 120 * t, cy, 1.0 + 0.12 * t, 255)
    elif shot == "parallax-float":
        back = _card_base(int(cw * 1.15), int(ch * 1.15), theme, accent_top=False)
        _paste_center(base, back, cx - 24 + 24 * t, cy, 1.0, 160)
        _paste_center(base, card, cx + 24 - 24 * t, cy - 8 * math.sin(t * 2 * math.pi), 1.0, 255)
    elif shot in ("deck-deal-flyin", "stack-cards", "grid-stagger", "row-embed"):
        n = 3 if shot != "grid-stagger" else 4
        mw, mh = (cw // 2, ch // 2) if shot == "grid-stagger" else (cw, ch // 3 + 40)
        for i in range(n):
            lt = E.lagged(t, i, n)
            mini = _card_base(mw, mh, theme)
            if shot == "deck-deal-flyin":
                x = cx + (1 - lt) * W * 0.7 * (1 if i % 2 == 0 else -1)
                y = cy + (i - n / 2) * (mh + 18)
                _paste_center(base, mini, x, y, 0.7 + 0.3 * lt, int(255 * min(1, lt * 1.5)))
            elif shot == "stack-cards":
                _paste_center(base, mini, cx, cy + (i - 1) * 26 * lt, 0.92 + 0.04 * i, 255 if lt > 0.05 else 0)
            elif shot == "grid-stagger":
                gx = cx + (mw + 20) * ((i % 2) - 0.5)
                gy = cy + (mh + 20) * ((i // 2) - 0.5)
                _paste_center(base, mini, gx, gy + (1 - lt) * 60, lt, int(255 * lt))
            else:  # row-embed
                _paste_center(base, mini, cx + (1 - lt) * W * 0.5, cy + (i - n / 2) * (mh + 14), 1.0, int(255 * lt))
    elif shot == "split-reveal":
        e = E.ease_in_out_cubic(t)
        _paste_center(base, card, cx, cy, 1.0, 255)
        split = int(W * e)
        d.rectangle([split - 4, 0, split + 4, H], fill=acc + (255,))
    elif shot == "digit-roll":
        e = E.ease_out_expo(t)
        _paste_center(base, card, cx, cy - 30, 1.0, 255)
        _text_center(base, str(int((value or 128) * e)), cx, cy + ch / 2 + 10, int(H * 0.11), acc)
    elif shot == "ticker-wall":
        for i in range(6):
            y = ((i * 90 + t * 220) % (H + 90)) - 45
            mini = _card_base(int(cw * 0.9), 64, theme, accent_top=False)
            _paste_center(base, mini, cx, y, 1.0, 220)
    elif shot in ("page-pan", "page-zoom"):
        e = E.ease_in_out_cubic(t) if shot == "page-pan" else E.ease_out_expo(t)
        big = _card_base(int(W * 0.9), int(H * 0.7), theme)
        if shot == "page-pan":
            _paste_center(base, big, cx - 160 + 320 * e, cy, 1.05, 255)
        else:
            _paste_center(base, big, cx, cy, 1.0 + 0.6 * e, 255)
    elif shot == "typewriter":
        _paste_center(base, card, cx, cy + 40, 1.0, 255)
        nch = int(len(title) * E.linear(t)) if title else int(20 * t)
        _text_center(base, (title or "CraftCine — Cinematic Product Films")[:max(1, nch)] + "▌", cx, cy - H * 0.22, int(H * 0.055), txt)
    elif shot == "caption-pop":
        e = E.ease_out_back(t)
        _paste_center(base, card, cx, cy - 20, 0.9 + 0.1 * min(1, e), 255)
    elif shot == "logo-hold":
        e = E.ease_out_cubic(min(1, t * 2))
        _paste_center(base, card, cx, cy, 0.9 + 0.1 * e, 255)
        if t > 0.35:  # mandatory hold breather
            _text_center(base, title or "CRAFTCINE", cx, cy - 10, int(H * 0.07), txt)
    elif shot == "cta-pulse":
        e = E.damped_settle(t)
        _paste_center(base, card, cx, cy - 20, 1.0, 255)
        bw, bh = int(W * 0.34 * (1 + 0.05 * e)), int(H * 0.1)
        btn = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        bd = ImageDraw.Draw(btn)
        bd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh // 2, fill=acc + (255,))
        _paste_center(base, btn, cx, cy + ch / 2 + 60, 1.0, 255)
        _text_center(base, title or "Get Started", cx, cy + ch / 2 + 60 - bh / 3, int(H * 0.038), (20, 20, 20))
    elif shot == "flash-cut":
        _paste_center(base, card, cx, cy, 1.0, 255)
        flash = int(255 * (1 - abs(t - 0.5) * 2))
        white = Image.new("RGBA", (W, H), (255, 255, 255, max(0, flash)))
        base.alpha_composite(white)
    elif shot == "glitch-cut":
        _paste_center(base, card, cx, cy, 1.0, 255)
        for i in range(6):
            rng = E.mulberry32(seed + i)()
            if rng > 0.5:
                y0 = int(rng * H)
                sl = base.crop((0, y0, W, min(H, y0 + 18)))
                base.alpha_composite(sl, (int((rng - 0.5) * 40), y0))
    elif shot in ("slide-left", "slide-up"):
        e = E.ease_in_out_cubic(t)
        if shot == "slide-left":
            _paste_center(base, card, cx + W * (0.6 - e * 0.6), cy, 1.0, 255)
        else:
            _paste_center(base, card, cx, cy + H * (0.5 - e * 0.5), 1.0, 255)
    elif shot == "iris-open":
        e = E.ease_in_out_cubic(t)
        _paste_center(base, card, cx, cy, 1.0, 255)
        r = int(min(W, H) * 0.7 * (1 - e))
        if r > 4:
            mask = Image.new("L", (W, H), 0)
            md = ImageDraw.Draw(mask)
            md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
            dark = Image.new("RGBA", (W, H), (0, 0, 0, 220))
            base.paste(dark, (0, 0), Image.eval(mask, lambda v: 255 - v))
    elif shot == "rise-in":
        e = E.ease_out_back(t)
        k = min(1.0, e)
        _paste_center(base, card, cx, cy + (1 - k) * 120, 0.92 + 0.08 * k, 255)
    elif shot == "zoom-out":
        e = E.ease_in_out_cubic(t)
        _paste_center(base, card, cx, cy, 1.6 - 0.6 * e, 255)
    elif shot == "slide-right":
        e = E.ease_in_out_cubic(t)
        _paste_center(base, card, cx - W * (0.6 - e * 0.6), cy, 1.0, 255)
    elif shot == "card-flip":
        e = E.ease_out_back(t)
        sx = max(0.05, math.sin(min(1.0, e) * math.pi / 2))
        flipped = card.resize((max(1, int(cw * sx)), ch), Image.BILINEAR)
        _paste_center(base, flipped, cx, cy, 1.0, int(255 * min(1.0, t * 3)))
    elif shot == "stat-trio":
        vals = list(values) if values else [42, 68, 95]
        mw = cw // 3 - 10
        for i in range(3):
            lt = E.lagged(t, i, 3)
            mini = _card_base(mw, ch, theme)
            x = cx + (i - 1) * (mw + 16)
            _paste_center(base, mini, x, cy + (1 - lt) * 50, 0.9 + 0.1 * lt, int(255 * lt))
            if lt > 0.6:
                _text_center(base, str(int(vals[i % len(vals)] * E.ease_out_expo(t))),
                             x, cy + 6, int(H * 0.06), acc)
    elif shot == "quote-card":
        e = E.ease_out_cubic(t)
        _paste_center(base, card, cx, cy, 0.94 + 0.06 * e, int(255 * min(1.0, t * 2)))
        _text_center(base, "\u201c", cx, cy - ch / 2 - 14, int(H * 0.13), acc)
    else:
        _paste_center(base, card, cx, cy, 1.0, 255)

    # captions (one message per shot rule) ----------------------------------
    if shot not in ("typewriter", "logo-hold", "digit-roll", "cta-pulse") and (title or subtitle):
        if title:
            _text_center(base, title, cx, H * 0.78, int(H * 0.052), txt, stroke=1)
        if subtitle:
            _text_center(base, subtitle, cx, H * 0.78 + H * 0.06, int(H * 0.032), mut)
    # letterbox for cinema feel on hero shots
    if shot in ("spotlight-hero", "orbit-tilt", "iris-open"):
        bh = int(H * 0.055)
        d.rectangle([0, 0, W, bh], fill=(0, 0, 0, 255))
        d.rectangle([0, H - bh, W, H], fill=(0, 0, 0, 255))
    return base.convert("RGB")
