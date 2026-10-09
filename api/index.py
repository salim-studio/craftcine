"""CraftCine on Vercel — serverless HTTP entrypoint (stdlib only + craftcine).

Routes:
  GET  / | /api            landing page
  GET  /logo.svg           brand logo
  GET  /gallery[?theme=]   full shot gallery (HTML)
  GET  /api/shots[?cat=]   shot library (JSON)
  GET  /api/themes         theme list (JSON)
  GET  /api/storyboard     starter storyboard (JSON)
  GET  /api/render-demo    tiny demo film, ~5s @ 480x270 (video/mp4)

Note: serverless functions have hard time limits, so this endpoint only
serves browsing + a small demo. Render full-length films locally:
  python -m craftcine render myfilm/storyboard.json
"""
from __future__ import annotations
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from craftcine import shots as S
from craftcine import themes as T
from craftcine import timeline as TL
from craftcine import studio as ST

COPYRIGHT = "© 2026 salim-slimani · CraftCine"

LANDING = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CraftCine — Cut. Craft. Cinema.</title>
<style>body{font-family:'Segoe UI',Arial,sans-serif;background:#0B0B10;color:#eee;margin:0;text-align:center}
.hero{padding:70px 20px;background:linear-gradient(135deg,#E8A923,#C084FC)}
.hero h1{color:#14100B;font-size:46px;margin:10px 0;letter-spacing:2px}
.hero p{color:#3a2c1c;font-size:18px}
.btn{display:inline-block;margin:8px;padding:12px 26px;border-radius:10px;background:#14100B;color:#F5EBD7;text-decoration:none;font-weight:bold}
.links{padding:30px}.links a{color:#C084FC;margin:0 12px;font-family:Consolas,monospace}
code{background:#17141F;padding:3px 8px;border-radius:6px;color:#E8A923}
footer{padding:20px;color:#6f6a80;font-size:13px}</style></head>
<body><div class="hero">
<img src="/logo.svg" width="96" alt="CraftCine logo">
<h1>CRAFTCINE</h1><p><b>Cut. Craft. Cinema.</b> — cinematic product videos in pure Python.</p>
<a class="btn" href="/gallery">Browse 24 shots</a>
<a class="btn" href="/api/render-demo">Watch 5s demo</a></div>
<div class="links">
<a href="/api/shots">/api/shots</a><a href="/api/themes">/api/themes</a>
<a href="/api/storyboard">/api/storyboard</a>
<p>Full films render locally: <code>python -m craftcine render myfilm/storyboard.json</code></p></div>
<footer>© 2026 salim-slimani · CraftCine</footer></body></html>"""


def _json(obj: object, status: int = 200) -> tuple[int, str, bytes]:
    return status, "application/json", json.dumps(obj).encode("utf-8")


def _render_demo() -> tuple[int, str, bytes]:
    from craftcine import renderer as R
    sb = TL.normalize({
        "width": 480, "height": 270, "fps": 12,
        "theme": "ink_press", "seed": 7,
        "shots": [
            {"shot": "fade-in", "duration": 1.5, "title": "CraftCine",
             "subtitle": "Cut. Craft. Cinema."},
            {"shot": "spotlight-hero", "duration": 2.0, "title": "Hero Shot",
             "subtitle": "Under the spotlight"},
            {"shot": "logo-hold", "duration": 1.5, "title": "CRAFTCINE",
             "subtitle": "Rendered by an API"},
        ],
    })
    out = "/tmp/craftcine-demo.mp4"
    R.render(sb, out, jobs=1, progress=False)
    with open(out, "rb") as f:
        return 200, "video/mp4", f.read()


def route(method: str, path: str) -> tuple[int, str, bytes]:
    u = urllib.parse.urlparse(path)
    q = urllib.parse.parse_qs(u.query)
    p = u.path.rstrip("/") or "/"
    if p in ("/", "/api"):
        return 200, "text/html; charset=utf-8", LANDING.encode("utf-8")
    if p == "/logo.svg":
        with open(os.path.join(ROOT, "assets", "brand", "logo.svg"), "rb") as f:
            return 200, "image/svg+xml", f.read()
    if p in ("/gallery", "/api/gallery"):
        theme = q.get("theme", ["ink_press"])[0]
        tmp = "/tmp/craftcine-gallery.html"
        ST.build_gallery(tmp, theme=theme)
        with open(tmp, "rb") as f:
            return 200, "text/html; charset=utf-8", f.read()
    if p == "/api/shots":
        return _json(S.search(cat=q.get("cat", [""])[0]))
    if p == "/api/themes":
        return _json({"default": T.DEFAULT_THEME, "themes": T.names()})
    if p == "/api/storyboard":
        with open(os.path.join(ROOT, "template", "promo.json"), encoding="utf-8") as f:
            return 200, "application/json", f.read().encode("utf-8")
    if p == "/api/render-demo":
        return _render_demo()
    return 404, "application/json", b'{"error": "not found"}'


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            status, ctype, body = route("GET", self.path)
        except Exception as e:  # never leak a stack trace; stay JSON
            status, ctype, body = 500, "application/json", json.dumps(
                {"error": f"{type(e).__name__}: {e}"}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass
