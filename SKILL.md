---
name: craftcine
description: Create cinematic product videos in pure Python (24 shot recipes + 9 themes + parallel Pillow renderer + single CLI). Use when the user asks to turn a product or page into a promo video, says "use craftcine", or wants a single motion shot.
---

# craftcine — fast cinematic production

## Always start here

1. `python -m craftcine init <project> --title "<Product>"` — scaffold from the 10-shot template.
2. `python -m craftcine shots [--cat hero]` — pick from the 24 recipes, or build the `gallery`.
3. Edit `storyboard.json`: one shot = one message (`title`/`subtitle`), logo hold ≥ 1s, full flash ≤ 3 per film.
4. `render --preview` for instant iteration → `still` for frame QA → `render` for the final.
5. After delivery: `workbench --dir <project>`, and `draft` when external editing is requested.

## Hard rules

- Deterministic rendering: no wall-clock or unseeded randomness — use `easing.mulberry32(seed)`.
- Themes come from `themes.py` only (9 themes) — never invent ad-hoc colors.
- Shot names must exist in `shots.py` — validate with `shots.get(name)` before rendering.
- `render --beat <BPM>` whenever a strong-rhythm BGM is used (cuts snap automatically).
- Every project: preview → stills → final. Check `references/aesthetic-rules.md` before delivery.
