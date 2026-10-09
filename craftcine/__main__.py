"""CraftCine CLI — single entry point. Pure Python, no browser, no heavy deps.

  python -m craftcine init myfilm          # new project from the template
  python -m craftcine shots               # list the 24 shot recipes
  python -m craftcine render film/storyboard.json [--preview] [--jobs 8]
  python -m craftcine still film/storyboard.json --frame 45
  python -m craftcine gallery             # static HTML gallery
  python -m craftcine draft film/storyboard.json   # editable timeline JSON
  python -m craftcine workbench --dir film --port 5198
  python -m craftcine theme --set midnight --file film/storyboard.json
"""
from __future__ import annotations
import argparse
import json
import os

from . import shots as S
from . import themes as T
from . import timeline as TL
from . import renderer as R
from . import studio as ST

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_JSON = os.path.normpath(os.path.join(HERE, "..", "template", "promo.json"))


def cmd_init(args):
    dest = args.project
    os.makedirs(dest, exist_ok=True)
    sb_src = args.storyboard or TEMPLATE_JSON
    with open(sb_src, encoding="utf-8") as f:
        sb = json.load(f)
    if args.title:
        sb["shots"][0]["title"] = args.title
    if args.theme:
        sb["theme"] = args.theme
    out = os.path.join(dest, "storyboard.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=2)
    print(f"Project ready: {out}")
    print(f"  shots={len(sb['shots'])} theme={sb['theme']}")
    print(f"  Fast preview: python -m craftcine render {out} --preview")
    print(f"  Final render: python -m craftcine render {out}")


def cmd_shots(args):
    rows = S.search(cat=args.cat or "", energy=args.energy or 0)
    print(f"{len(rows)} shots" + (f" [cat={args.cat}]" if args.cat else ""))
    for r in rows:
        print(f"  {r['name']:18s} [{r['cat']:10s} E{r['energy']} {r['dur']}s] {r['desc']}")


def cmd_render(args):
    sb = TL.load(args.storyboard)
    if args.beat:
        sb = TL.snap_to_beats(sb, args.beat)
        print(f"Beat sync: cuts snapped to {args.beat} BPM")
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.storyboard)), "out",
                                   "preview.mp4" if args.preview else "promo.mp4")
    mode = "PREVIEW 640x360@15fps" if args.preview else f"FINAL {sb['width']}x{sb['height']}@{sb['fps']}fps"
    print(f"{mode} — theme={sb['theme']}")
    path = R.render(sb, out, preview=args.preview, jobs=args.jobs)
    print(f"Done: {path} ({os.path.getsize(path)//1024} KB)")


def cmd_still(args):
    sb = TL.load(args.storyboard)
    out = args.out or "still.png"
    R.still(sb, args.frame, out)
    print(f"Still frame {args.frame} -> {out}")


def cmd_gallery(args):
    out = ST.build_gallery(args.out, theme=args.theme)
    print(f"Gallery ({len(S.SHOTS)} shots): {out}")


def cmd_draft(args):
    out = ST.export_edit_draft(args.storyboard, args.out)
    print(f"Editable draft: {out}")


def cmd_theme(args):
    if args.list:
        for n in T.names():
            print(f"  {n}")
        return
    with open(args.file, encoding="utf-8") as f:
        sb = json.load(f)
    T.get(args.set)
    sb["theme"] = args.set
    sb = TL.normalize(sb)
    with open(args.file, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=2)
    print(f"Theme -> {args.set}")


def cmd_workbench(args):
    ST.serve_workbench(args.port, args.dir)


def build_parser():
    p = argparse.ArgumentParser(prog="craftcine", description="CraftCine — cinematic product videos in pure Python")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init", help="new project from the template")
    a.add_argument("project"); a.add_argument("--storyboard"); a.add_argument("--title"); a.add_argument("--theme")
    a.set_defaults(fn=cmd_init)
    a = sub.add_parser("shots", help="list shot recipes")
    a.add_argument("--cat"); a.add_argument("--energy", type=int)
    a.set_defaults(fn=cmd_shots)
    a = sub.add_parser("render", help="render a storyboard to mp4")
    a.add_argument("storyboard"); a.add_argument("--out"); a.add_argument("--preview", action="store_true")
    a.add_argument("--jobs", type=int, default=0); a.add_argument("--beat", type=float, default=0)
    a.set_defaults(fn=cmd_render)
    a = sub.add_parser("still", help="dump one frame for QA review")
    a.add_argument("storyboard"); a.add_argument("--frame", type=int, default=0); a.add_argument("--out")
    a.set_defaults(fn=cmd_still)
    a = sub.add_parser("gallery", help="build the static HTML gallery")
    a.add_argument("--out", default="gallery/index.html"); a.add_argument("--theme", default="ink_press")
    a.set_defaults(fn=cmd_gallery)
    a = sub.add_parser("draft", help="export an editable timeline draft (JSON)")
    a.add_argument("storyboard"); a.add_argument("--out", default="edit_draft.json")
    a.set_defaults(fn=cmd_draft)
    a = sub.add_parser("theme", help="list or switch themes")
    a.add_argument("--list", action="store_true"); a.add_argument("--set"); a.add_argument("--file", default="storyboard.json")
    a.set_defaults(fn=cmd_theme)
    a = sub.add_parser("workbench", help="browser editor for the delivered film")
    a.add_argument("--dir", default="."); a.add_argument("--port", type=int, default=5198)
    a.set_defaults(fn=cmd_workbench)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
