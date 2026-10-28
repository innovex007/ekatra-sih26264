"""Restores the demo database to the freshly seeded state in about a second (no re-seed).
Uses the snapshot data/ekatra.clean.db written by the seed. Falls back to a full seed if it is missing."""
import json
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB, CLEAN = ROOT / "data" / "ekatra.db", ROOT / "data" / "ekatra.clean.db"
t0 = time.time()
if not CLEAN.exists():
    print("No clean snapshot yet - running the full seed once (about a minute)...")
    sys.exit(subprocess.call([sys.executable, "-m", "data.generator.seed", "--seed", "42"], cwd=ROOT))

src, dst = sqlite3.connect(CLEAN), sqlite3.connect(DB, timeout=30)
src.backup(dst)          # works while the API is running; it re-reads the file on its next query
src.close(); dst.close()

api = "http://localhost:8010"
try:
    urllib.request.urlopen(urllib.request.Request(api + "/admin/reload", method="POST"), timeout=5)
    s = json.load(urllib.request.urlopen(api + "/dashboard/summary", timeout=10))
    v = json.load(urllib.request.urlopen(urllib.request.Request(api + "/audit/verify", method="POST"), timeout=10))
    print(f"Demo reset in {time.time() - t0:.1f}s - {s['total']} cases, conflicts blocked {s['conflicts_blocked']}, "
          f"open overlaps {s['open_overlaps']}, audit chain {'intact' if v['intact'] else 'BROKEN'} ({v['events']} events).")
except Exception as e:  # API not running: the database is still restored
    print(f"Demo database restored in {time.time() - t0:.1f}s (API not reachable, so nothing was verified: {e}).")
