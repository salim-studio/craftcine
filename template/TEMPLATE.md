# CraftCine starter template (10 shots, ~30s, 1280×720@30)

| # | Shot | Role |
|---|---|---|
| 1 | iris-open | Cinematic open + product name |
| 2 | spotlight-hero | The hero shot (most important) |
| 3 | page-pan | Real-interface proof |
| 4 | deck-deal-flyin | 3 features, dealt fast |
| 5 | zoom-push | Push on the key feature |
| 6 | digit-roll | Number / stat |
| 7 | row-embed | Dense interface |
| 8 | ticker-wall | Live activity |
| 9 | logo-hold | Logo hold ≥ 1s |
| 10 | cta-pulse | The single call to action |

## Quick swap

```bash
python -m craftcine init myfilm --title "My Product" --theme midnight
# edit myfilm/storyboard.json: titles + subtitles + value for the counter
python -m craftcine render myfilm/storyboard.json --preview
python -m craftcine render myfilm/storyboard.json
```
