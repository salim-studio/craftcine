"""CraftCine themes — 9 one-click film themes. Pure color tokens, no images."""
from __future__ import annotations

THEMES = {
    "ink_press": {
        "bg": "#14100B", "surface": "#241C12", "text": "#F5EBD7",
        "accent": "#E8A923", "muted": "#A8977A", "paper_grain": True,
    },
    "modern_light": {
        "bg": "#F6F7F9", "surface": "#FFFFFF", "text": "#14181F",
        "accent": "#2563EB", "muted": "#6B7280", "paper_grain": False,
    },
    "midnight": {
        "bg": "#070B16", "surface": "#101828", "text": "#EAF0FF",
        "accent": "#7C9CFF", "muted": "#8A94AD", "paper_grain": False,
    },
    "sage": {
        "bg": "#10140F", "surface": "#1A211A", "text": "#E9F0E4",
        "accent": "#9DBE8C", "muted": "#8A968A", "paper_grain": False,
    },
    "coral": {
        "bg": "#1A0F0E", "surface": "#2A1815", "text": "#FFF1EA",
        "accent": "#FF6B57", "muted": "#C49A90", "paper_grain": False,
    },
    "iris": {
        "bg": "#120E1E", "surface": "#1D1533", "text": "#F0EAFE",
        "accent": "#A78BFA", "muted": "#9A8FB8", "paper_grain": False,
    },
    "deep_ocean": {
        "bg": "#06202B", "surface": "#0A2E3D", "text": "#E6F7FF",
        "accent": "#22C3E6", "muted": "#7FA8B8", "paper_grain": False,
    },
    "obsidian_violet": {
        "bg": "#0B0B10", "surface": "#17141F", "text": "#F2EDFF",
        "accent": "#C084FC", "muted": "#8E8A9E", "paper_grain": False,
    },
    "vintage_kraft": {
        "bg": "#20180F", "surface": "#3A2C1C", "text": "#F3E6CF",
        "accent": "#D97B2B", "muted": "#B39B78", "paper_grain": True,
    },
}

DEFAULT_THEME = "ink_press"


def get(name: str) -> dict:
    key = (name or DEFAULT_THEME).lower().replace("-", "_").replace(" ", "_")
    return THEMES.get(key, THEMES[DEFAULT_THEME])


def names() -> list[str]:
    return list(THEMES.keys())
