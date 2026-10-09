<p align="center">
  <img src="assets/brand/logo.svg" width="120" alt="CraftCine logo">
</p>

<h1 align="center">CraftCine</h1>

<p align="center"><b>Cut. Craft. Cinema.</b> — cinematic product videos rendered in pure Python.</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.1.1-amber" alt="version">
  <img src="https://img.shields.io/badge/python-%3E%3D3.9-blue" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/renderer-Pillow%20%2B%20ffmpeg-lightgrey" alt="renderer">
</p>

## Why CraftCine

- **Zero heavy toolchain** — no browser, no Node, no UI framework. `pip install` and render.
- **30 curated shot recipes** — a tight motion vocabulary covering ~90% of promo needs.
- **9 one-click themes** — switch the whole film's look with one flag.
- **Parallel renderer** — frames render across all CPU cores; instant `--preview` mode for iteration.
- **One CLI** — `init / shots / render / still / subs / gallery / draft / theme / studio / workbench`.
- **Deterministic** — the same `(storyboard, seed)` always produces the same mp4.

## Install (2 minutes)

```bash
pip install pillow numpy imageio imageio-ffmpeg
pip install -e .   # or: pip install git+https://github.com/salim-studio/craftcine.git
```

## Fastest path to a film

```bash
python -m craftcine init myfilm --title "My Product"
python -m craftcine render myfilm/storyboard.json --preview   # instant preview
python -m craftcine render myfilm/storyboard.json             # final film
python -m craftcine gallery --out gallery/index.html          # browse all 30 shots
python -m craftcine draft myfilm/storyboard.json              # editable timeline JSON
python -m craftcine workbench --dir myfilm                    # browser editor
```

## Studio (web app)

```bash
python -m craftcine studio --port 5198   # opens http://localhost:5198/studio
```

- **Dashboard** — create and manage film projects (file-based, no database).
- **Visual editor** — reorder shots, edit copy, switch themes, per-shot previews.
- **Background renders** — progress bar, incremental cache (only edited shots re-render).
- **One-click exports** — MP4, SRT subtitles, editable timeline JSON.
- **Product images** — put `"image": "shot.png"` on any shot to composite a real
  screenshot into the card.
- **Video import** — upload a clip in the studio (⬆️ Import video), attach it to
  any shot with the 🎞️ dropdown, and the motion plays over your footage
  (or in storyboard JSON: `"clip": "assets/demo.mp4"`, optional `"clip_offset"`).
  Limits: 100 MB local / 25 MB hosted — bigger files need the local studio.

## Shots (30)

`fade-in · iris-open · typewriter · spotlight-hero · zoom-push · orbit-tilt ·`
`kenburns · parallax-float · deck-deal-flyin · row-embed · stack-cards ·`
`grid-stagger · split-reveal · digit-roll · ticker-wall · page-pan · page-zoom ·`
`caption-pop · logo-hold · cta-pulse · flash-cut · slide-left · slide-up · glitch-cut`

```bash
python -m craftcine shots
python -m craftcine shots --cat hero
```

## Themes (9)

`ink_press · modern_light · midnight · sage · coral · iris · deep_ocean · obsidian_violet · vintage_kraft`

```bash
python -m craftcine theme --list
python -m craftcine theme --set midnight --file myfilm/storyboard.json
```

## storyboard.json

```json
{"width": 1280, "height": 720, "fps": 30, "theme": "ink_press", "seed": 7,
 "shots": [{"shot": "spotlight-hero", "duration": 4.0,
            "title": "My Product", "subtitle": "Under the spotlight"}]}
```

House rules: one shot = one message. The closing logo holds ≥ 1s. Full-screen
flashes: max 3 per film. `render --beat 128` snaps cuts to the beat (works
without any extra dependency). Rendering is deterministic — no wall-clock or
unseeded randomness anywhere in the frame path.

## Tests

```bash
python -m pytest tests/ -q
```

## Deploy on Vercel

The repo ships a serverless entrypoint (`api/index.py`): landing page, shot
library API, HTML gallery, and a ~5s demo render.

```bash
vercel --prod
```

Live routes: `/` · `/gallery` · `/api/shots` · `/api/themes` ·
`/api/storyboard` · `/api/render-demo`

> The hosted studio renders synchronously in a capped preview profile
> (640×360@15fps, max 90s) to fit serverless limits. For full-quality
> 720p/1080p films, run the studio locally with `python -m craftcine studio`.

## Layout

```
craftcine/
├── craftcine/        easing | shots (30) | themes | compositor | timeline
│                     renderer (incremental cache) | studio | subs | projects | jobs
│                     server (Flask studio) | __main__ (CLI)
├── craftcine/web/    studio templates + static CSS
├── assets/brand/     logo + visual identity
├── template/         ready-to-render 10-shot promo (~30s)
├── references/       production method (pipeline + visual QA)
├── gallery/          generated static gallery
├── tests/            deterministic + smoke tests
└── SKILL.md          agent instructions
```

---

<p align="center">© 2026 salim-slimani · CraftCine — Cut. Craft. Cinema.</p>
