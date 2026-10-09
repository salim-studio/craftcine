"""CraftCine projects — file-based project store (no database needed).

Layout:
  <data_dir>/<project_id>/storyboard.json
  <data_dir>/<project_id>/meta.json
  <data_dir>/<project_id>/out/promo.mp4 ...
  <data_dir>/<project_id>/.cache/seg_*.mp4 (incremental render cache)
  <data_dir>/<project_id>/.stills/<idx>_<hash>.png (editor previews)
"""
from __future__ import annotations
import json
import os
import shutil
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, ".."))
TEMPLATE_JSON = os.path.join(REPO_ROOT, "template", "promo.json")


def data_dir(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    if os.environ.get("VERCEL") == "1":
        return "/tmp/craftcine-projects"
    return os.path.join(REPO_ROOT, "projects")


def _meta_path(root: str, pid: str) -> str:
    return os.path.join(root, pid, "meta.json")


def _sb_path(root: str, pid: str) -> str:
    return os.path.join(root, pid, "storyboard.json")


def _slug(title: str) -> str:
    keep = "".join(c.lower() if c.isalnum() else "-" for c in (title or "untitled"))
    keep = "-".join(p for p in keep.split("-") if p) or "untitled"
    return keep[:32]


def _seed_demo(root: str) -> None:
    """First run: clone the template into a demo project."""
    if os.path.isdir(root) and os.listdir(root):
        return
    try:
        create(root, "Demo Film", theme="ink_press")
    except Exception:
        pass


def list_projects(root: str) -> list[dict]:
    os.makedirs(root, exist_ok=True)
    _seed_demo(root)
    out = []
    for pid in sorted(os.listdir(root)):
        mp = _meta_path(root, pid)
        if os.path.isfile(mp):
            try:
                with open(mp, encoding="utf-8") as f:
                    out.append(json.load(f))
            except (OSError, ValueError):
                pass
    return out


def create(root: str, title: str, theme: str = "ink_press") -> dict:
    from . import themes as T
    from . import timeline as TL
    os.makedirs(root, exist_ok=True)
    pid = f"{_slug(title)}-{uuid.uuid4().hex[:6]}"
    os.makedirs(os.path.join(root, pid, "out"), exist_ok=True)
    with open(TEMPLATE_JSON, encoding="utf-8") as f:
        sb = json.load(f)
    if title:
        sb["shots"][0]["title"] = title
    if theme:
        T.get(theme)
        sb["theme"] = theme
    sb = TL.normalize(sb)
    with open(_sb_path(root, pid), "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=2)
    now = time.time()
    meta = {"id": pid, "title": title or "Untitled", "theme": sb["theme"],
            "shots": len(sb["shots"]), "total_sec": sb["total_sec"],
            "created": now, "updated": now}
    with open(_meta_path(root, pid), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def load(root: str, pid: str) -> tuple[dict, dict]:
    with open(_meta_path(root, pid), encoding="utf-8") as f:
        meta = json.load(f)
    with open(_sb_path(root, pid), encoding="utf-8") as f:
        sb = json.load(f)
    return meta, sb


def save(root: str, pid: str, sb: dict) -> dict:
    from . import timeline as TL
    sb = TL.normalize(sb)
    with open(_sb_path(root, pid), "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=2)
    with open(_meta_path(root, pid), encoding="utf-8") as f:
        meta = json.load(f)
    meta.update({"theme": sb.get("theme", meta.get("theme")), "shots": len(sb["shots"]),
                 "total_sec": sb["total_sec"], "updated": time.time()})
    with open(_meta_path(root, pid), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def delete(root: str, pid: str) -> None:
    shutil.rmtree(os.path.join(root, pid), ignore_errors=True)


def proj_dir(root: str, pid: str) -> str:
    return os.path.join(root, pid)
