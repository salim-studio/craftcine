"""CraftCine studio helpers — static gallery, editor-draft export, workbench server."""
from __future__ import annotations
import json
import os
from . import shots as S
from . import themes as T

BRAND_GRADIENT = "linear-gradient(135deg,#E8A923,#C084FC)"
COPYRIGHT = "© 2026 salim-slimani · CraftCine"

GALLERY_CSS = """
body{font-family:'Segoe UI',Arial,sans-serif;background:#0B0B10;color:#eee;margin:0}
header{padding:36px 20px;text-align:center;background:linear-gradient(135deg,#E8A923,#C084FC)}
header h1{margin:8px 0 4px;color:#14100B;font-size:34px;letter-spacing:1px}
header p{color:#3a2c1c;margin:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px;padding:22px;max-width:1280px;margin:0 auto}
.card{background:#17141F;border:1px solid #2c2838;border-radius:14px;padding:14px;transition:transform .15s}
.card:hover{transform:translateY(-3px);border-color:#C084FC}
.card h3{margin:0 0 6px;color:#E8A923;font-size:16px;font-family:Consolas,monospace}
.badge{display:inline-block;background:#2c2838;border-radius:20px;padding:2px 10px;font-size:12px;margin:2px;color:#cfc8e0}
.demo{height:120px;border-radius:10px;margin:10px 0;position:relative;overflow:hidden}
.card p{font-size:13px;color:#a49db8;line-height:1.5}
footer{text-align:center;padding:24px;color:#6f6a80;font-size:13px}
"""

DEMO_ANIM = """
@keyframes deal{0%{transform:translateX(120px);opacity:0}100%{transform:none;opacity:1}}
@keyframes pop{0%{transform:scale(.6);opacity:0}70%{transform:scale(1.05)}100%{transform:scale(1);opacity:1}}
@keyframes floaty{0%,100%{transform:translateY(-6px)}50%{transform:translateY(6px)}}
@keyframes flashy{0%,100%{opacity:1}50%{opacity:.2}}
"""


def build_gallery(out_html: str, theme: str = "ink_press") -> str:
    th = T.get(theme)
    cards = []
    for name, meta in sorted(S.SHOTS.items()):
        anim = {"feature": "deal .8s ease both", "title": "pop .7s ease both",
                "hero": "floaty 2s ease-in-out infinite", "transition": "flashy 1s linear infinite"}.get(meta["cat"], "pop .7s ease both")
        cards.append(f"""<div class="card"><h3>{name}</h3>
<span class="badge">{meta['cat']}</span><span class="badge">⚡{meta['energy']}</span>
<span class="badge">{meta['dur']}s</span>
<div class="demo" style="background:{th['surface']};border-top:4px solid {th['accent']}">
<div style="width:55%;height:56%;margin:18px auto;background:{th['bg']};border:2px solid {th['accent']};
border-radius:10px;animation:{anim}"></div></div>
<p>{meta['desc']}</p></div>""")
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>CraftCine Gallery — {len(cards)} shots</title><style>{GALLERY_CSS}{DEMO_ANIM}</style></head>
<body><header><h1>🎬 CraftCine Gallery</h1>
<p>{len(cards)} motion recipes · theme <b>{theme}</b> · copy a shot name into your storyboard</p></header>
<div class="grid">{''.join(cards)}</div>
<footer>{COPYRIGHT} — Cut. Craft. Cinema.</footer></body></html>"""
    os.makedirs(os.path.dirname(os.path.abspath(out_html)), exist_ok=True)
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    return out_html


def export_edit_draft(storyboard_path: str, out_json: str) -> str:
    """Editable editor draft: per-shot clips + caption + audio tracks.

    A portable JSON timeline any editor workflow can consume: reorder or
    retime clips, edit captions, or replace the audio without re-rendering
    from scratch.
    """
    with open(storyboard_path, encoding="utf-8") as f:
        sb = json.load(f)
    fps = sb.get("fps", 30)
    t = 0.0
    clips, captions = [], []
    for i, s in enumerate(sb["shots"]):
        d = float(s.get("duration", 2.5))
        clips.append({"id": i, "shot": s.get("shot"), "start": round(t, 3),
                      "duration": d, "start_frame": int(t * fps),
                      "speed": 1.0, "reorderable": True})
        if s.get("title"):
            captions.append({"clip_id": i, "text": s["title"], "sub": s.get("subtitle", ""),
                             "start": round(t, 3), "duration": d,
                             "font_size": 52, "color": "#F5EBD7", "editable": True})
        t += d
    draft = {"app": "craftcine", "fps": fps, "theme": sb.get("theme"),
             "total_sec": round(t, 3), "video_track": clips,
             "caption_track": captions,
             "audio_tracks": {"bgm": sb.get("bgm"), "sfx": sb.get("sfx", [])}}
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)
    return out_json


WORKBENCH_HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>CraftCine Workbench</title>
<style>body{font-family:'Segoe UI',sans-serif;background:#0B0B10;color:#eee;margin:0}
header{padding:14px 18px;background:linear-gradient(135deg,#E8A923,#C084FC);color:#14100B}
main{display:flex;flex-wrap:wrap}video{width:100%;background:#000;border-radius:10px}
.stage{width:58%;min-width:320px;padding:14px}aside{flex:1;min-width:280px;padding:14px}
textarea{width:100%;height:58vh;background:#17141F;color:#eee;border:1px solid #2c2838;border-radius:8px;font-family:Consolas,monospace}
button{background:#E8A923;border:none;border-radius:8px;padding:8px 16px;margin:4px 4px 0 0;cursor:pointer;font-weight:bold}
footer{padding:12px;text-align:center;color:#6f6a80;font-size:12px}</style></head>
<body><header><b>🎛️ CraftCine Workbench</b> — edit storyboard.json, then re-render</header>
<main><div class="stage"><video id="v" controls></video>
<p>Video: <code id="p"></code></p></div>
<aside><h3>storyboard.json</h3><textarea id="sb"></textarea><br>
<button onclick="save()">💾 Save</button> <button onclick="re()">🎬 Render</button><pre id="log"></pre></aside></main>
<footer>© 2026 salim-slimani · CraftCine</footer>
<script>const q=new URLSearchParams(location.search);
document.getElementById('p').textContent=q.get('video')||'out/promo.mp4';
document.getElementById('v').src=q.get('video')||'out/promo.mp4';
fetch(q.get('sb')||'storyboard.json').then(r=>r.text()).then(t=>sb.value=t);
function save(){fetch('/__save?f='+(q.get('sb')||'storyboard.json'),{method:'POST',body:sb.value}).then(r=>r.text()).then(t=>log.textContent=t)}
function re(){log.textContent='Rendering…';fetch('/__render?f='+(q.get('sb')||'storyboard.json')).then(r=>r.text()).then(t=>{log.textContent=t;v.load()})}
</script></body></html>"""


def serve_workbench(port: int, directory: str) -> None:
    import http.server
    import functools
    import subprocess
    import sys
    import urllib.parse

    class H(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == "/" or u.path.startswith("/workbench"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(WORKBENCH_HTML.encode("utf-8"))
            elif u.path == "/__render":
                q = urllib.parse.parse_qs(u.query)
                f = q.get("f", ["storyboard.json"])[0]
                r = subprocess.run([sys.executable, "-m", "craftcine", "render", f],
                                   capture_output=True, text=True, cwd=directory)
                out = (r.stdout + r.stderr)[-3000:]
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(out.encode("utf-8"))
            else:
                super().do_GET()

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == "/__save":
                q = urllib.parse.parse_qs(u.query)
                f = q.get("f", ["storyboard.json"])[0]
                n = int(self.headers.get("Content-Length", 0))
                data = self.rfile.read(n)
                with open(os.path.join(directory, f), "wb") as fh:
                    fh.write(data)
                self.send_response(200)
                self.end_headers()
                self.wfile.write("saved ✅".encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *a):
            pass

    handler = functools.partial(H, directory=directory)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"CraftCine workbench: http://localhost:{port}/workbench")
    try:
        import webbrowser
        webbrowser.open(f"http://localhost:{port}/workbench")
    except Exception:
        pass
    srv.serve_forever()
