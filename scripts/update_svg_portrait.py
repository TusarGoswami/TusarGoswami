#!/usr/bin/env python3
"""Update profile.svg by embedding the new portrait while keeping all other information identical."""

import base64
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = ROOT / "assets" / "profile.svg"
PORTRAIT_PATH = ROOT / "assets" / "portrait.png"

# Load original SVG from git HEAD with explicit UTF-8
raw_git_svg = subprocess.check_output(["git", "show", "HEAD:assets/profile.svg"], cwd=ROOT)
orig_svg = raw_git_svg.decode("utf-8")

# Read new portrait as base64
raw_portrait = PORTRAIT_PATH.read_bytes()
new_b64 = base64.b64encode(raw_portrait).decode("ascii")
new_uri = f"data:image/png;base64,{new_b64}"

# Replace base64 image URI
updated_svg = re.sub(
    r'href="data:image/png;base64,[^"]+"',
    f'href="{new_uri}"',
    orig_svg,
)

# Write as UTF-8
SVG_PATH.write_text(updated_svg, encoding="utf-8")
print(f"[OK] profile.svg updated cleanly with new portrait ({len(updated_svg):,} bytes)")

# Validate XML
from xml.etree.ElementTree import fromstring
fromstring(updated_svg)
print("[OK] profile.svg is valid XML")
