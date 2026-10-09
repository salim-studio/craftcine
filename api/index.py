"""CraftCine on Vercel — exposes the Flask studio app.

Vercel's Python runtime serves the module-level `app`. Browsing, gallery
and APIs work hosted; full renders stay local (see jobs.is_serverless).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from craftcine.server import create_app

app = create_app()
