#!/usr/bin/env python3
"""Regenerate the committed screenshot PNGs from their HTML sources.

Targets (HTML -> PNG):
- docs/explainers/*.html            -> docs/explainers/screenshots/*.png
- docs/demo/slides/six-things.html  -> docs/demo/slides/six-things.png
- docs/quickstart-screenshots/mockups/stepN-*.html
                                    -> docs/quickstart-screenshots/stepN-*-mockup.png

Usage (from the repo root):
    python3 scripts/regen_screenshots.py --check      # list PNGs older than their HTML
    python3 scripts/regen_screenshots.py              # regenerate the stale ones
    python3 scripts/regen_screenshots.py --all        # regenerate everything
    python3 scripts/regen_screenshots.py --only six-things --only step4

Runtime: Node Playwright (Chromium). Python's `playwright` package is not
needed. The browser is taken from PLAYWRIGHT_BROWSERS_PATH (never installed
here). The `playwright` node module is located via NODE_PATH, falling back to
`npm root -g`. If the module is missing the script exits with an error and
prints the equivalent headless-Chromium one-liner.

Staleness: a PNG is stale when the last git commit touching its HTML is newer
than the last commit touching the PNG (file mtime is used for untracked or
uncommitted files, because a fresh checkout gives every file the same mtime).

Capture settings (full-page, file:// URL, wait for network idle + fonts):
- explainers: viewport width 1600 (A3 landscape), deviceScaleFactor 2
- slide:      1920x1080 canvas, deviceScaleFactor 2
- mockups:    sizes from docs/quickstart-screenshots/CAPTURE-GUIDE.md, scale 2
Any PNG over 1.5 MB is re-captured at scale 1.5, then 1, until it fits.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAX_BYTES = int(1.5 * 1024 * 1024)
SCALES = (2, 1.5, 1)

NODE_JS = r"""
const { chromium } = require('playwright');
(async () => {
  const j = JSON.parse(process.argv[1]);
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: j.width, height: j.height },
    deviceScaleFactor: j.scale,
  });
  const page = await ctx.newPage();
  try { await page.goto(j.url, { waitUntil: 'networkidle', timeout: 20000 }); }
  catch (e) { await page.goto(j.url, { waitUntil: 'load' }); }
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  await page.waitForTimeout(j.wait);
  await page.screenshot({ path: j.out, fullPage: true, type: 'png' });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
"""


def jobs() -> list[dict]:
    out = []
    ex = REPO / "docs/explainers"
    names = {
        "01": "01-architecture-overview",
        "02": "02-it-system-explanation",
        "03": "03-user-cheatsheet",
        "04": "04-quickstart-lazy-pack",
    }
    for html in sorted(ex.glob("*.html")):
        key = html.name[:2]
        if key in names:
            out.append(dict(html=html, png=ex / "screenshots" / f"{names[key]}.png",
                            width=1600, height=1000, wait=500))
    out.append(dict(html=REPO / "docs/demo/slides/six-things.html",
                    png=REPO / "docs/demo/slides/six-things.png",
                    width=1920, height=1080, wait=800))
    qs = REPO / "docs/quickstart-screenshots"
    # viewport sizes: docs/quickstart-screenshots/CAPTURE-GUIDE.md
    for stem, w, h in (("step4-main-window", 1440, 980),
                       ("step5-install-selector", 1280, 720),
                       ("step6-quote-success", 1280, 1280)):
        out.append(dict(html=qs / "mockups" / f"{stem}.html",
                        png=qs / f"{stem}-mockup.png",
                        width=w, height=h, wait=1500))
    return out


def commit_time(p: Path) -> float:
    """Last commit time touching p; mtime if untracked or modified."""
    rel = str(p.relative_to(REPO))
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=REPO,
                               capture_output=True, text=True, check=True).stdout.strip()
        if not dirty:
            t = subprocess.run(["git", "log", "-1", "--format=%ct", "--", rel], cwd=REPO,
                               capture_output=True, text=True, check=True).stdout.strip()
            if t:
                return float(t)
    except (OSError, subprocess.CalledProcessError):
        pass
    return p.stat().st_mtime


def is_stale(j: dict) -> bool:
    if not j["html"].exists():
        return False
    if not j["png"].exists():
        return True
    return commit_time(j["html"]) > commit_time(j["png"])


def node_env() -> dict:
    env = dict(os.environ)
    paths = [p for p in env.get("NODE_PATH", "").split(os.pathsep) if p]
    if shutil.which("npm"):
        r = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            paths.append(r.stdout.strip())
    env["NODE_PATH"] = os.pathsep.join(paths)
    return env


def capture(j: dict, scale: float, env: dict, out: Path) -> None:
    payload = dict(url=j["html"].resolve().as_uri(), out=str(out), width=j["width"],
                   height=j["height"], scale=scale, wait=j["wait"])
    subprocess.run(["node", "-e", NODE_JS, json.dumps(payload)], env=env, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="report PNGs older than their HTML; exit 1 if any")
    ap.add_argument("--all", action="store_true", help="regenerate every PNG, not just stale ones")
    ap.add_argument("--only", action="append", default=[], metavar="SUBSTR",
                    help="restrict to PNGs whose path contains SUBSTR (repeatable)")
    a = ap.parse_args()

    sel = [j for j in jobs() if not a.only or any(s in str(j["png"]) for s in a.only)]
    stale = [j for j in sel if is_stale(j)]
    if a.check:
        for j in sel:
            tag = "STALE" if j in stale else "ok   "
            print(f"{tag} {j['png'].relative_to(REPO)}  <-  {j['html'].relative_to(REPO)}")
        print(f"{len(stale)} of {len(sel)} PNG(s) older than their HTML")
        return 1 if stale else 0

    todo = sel if a.all else stale
    if not todo:
        print("nothing to do: all PNGs are newer than their HTML")
        return 0
    if not shutil.which("node"):
        sys.exit("node not found; install Node + playwright, or run headless Chromium:\n"
                 "  chrome --headless=new --screenshot=OUT.png --window-size=W,H "
                 "--hide-scrollbars file:///abs/path.html")
    env = node_env()
    probe = subprocess.run(["node", "-e", "require('playwright')"], env=env, capture_output=True)
    if probe.returncode != 0:
        sys.exit("node module 'playwright' not importable (set NODE_PATH to its node_modules). "
                 "Fallback: chrome --headless=new --screenshot=OUT.png --window-size=W,H "
                 "--hide-scrollbars file:///abs/path.html")
    for j in todo:
        for scale in SCALES:
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td) / "shot.png"
                capture(j, scale, env, tmp)
                size = tmp.stat().st_size
                if size <= MAX_BYTES or scale == SCALES[-1]:
                    j["png"].parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(tmp, j["png"])
                    break
        note = "" if size <= MAX_BYTES else "  (WARNING: over 1.5 MB at scale 1)"
        print(f"wrote {j['png'].relative_to(REPO)}  scale={scale}  {size/1024:.0f} KB{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
