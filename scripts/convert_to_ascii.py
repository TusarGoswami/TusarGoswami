#!/usr/bin/env python3
"""Ultra-high resolution Micro-ASCII portrait generator.

Produces a 760x1134 (Retina 2x) ASCII portrait with 140 columns x 190 rows
of microscopic code glyphs (~26,000 cells), delivering razor-sharp facial
recognition (eyes, glasses, mustache, smile) with matrix hacker aesthetics.
"""

import collections
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "assets" / "new_photo.png"
OUTPUT = ROOT / "assets" / "portrait.png"

# Canvas dimensions (2x Retina scale matching 380x567 display aspect ratio)
CANVAS_W, CANVAS_H = 760, 1134

# Grid sizing: 140 columns x 190 rows (~26,600 micro-ASCII cells)
COLS = 140
ROWS = 190

CELL_W = 704.0 / COLS
CELL_H = 1084.0 / ROWS
OFFSET_X = 28.0
OFFSET_Y = 25.0

# Colors
BG_COLOR = (1, 5, 12)
BORDER_COLOR = (28, 44, 60)
DOT_COLOR = (18, 30, 44)

# Glyph set from sparse to dense
RAMP = [
    ".", ":", ";", "~", "+", "=", "*", 
    "x", "s", "z", "u", "v", 
    "c", "a", "e", "3", "5", "9",
    "0", "A", "C", "D", "E", "F",
    "Q", "O", "8", "B", "%", "&", "#", "@"
]


def load_font():
    """Load small monospace font for micro-ASCII rendering."""
    candidates = [
        ("C:/Windows/Fonts/consola.ttf", 7),
        ("C:/Windows/Fonts/lucon.ttf", 6),
        ("C:/Windows/Fonts/courbd.ttf", 7),
    ]
    for path, size in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def build_background_mask(img_small):
    """Flood-fill background mask from borders."""
    cols, rows = img_small.size
    is_bg = [[False] * cols for _ in range(rows)]
    queue = collections.deque()

    for c in range(cols):
        queue.append((0, c))
        queue.append((rows - 1, c))
    for r in range(rows):
        queue.append((r, 0))
        queue.append((r, cols - 1))

    while queue:
        r, c = queue.popleft()
        if 0 <= r < rows and 0 <= c < cols and not is_bg[r][c]:
            pixel = img_small.getpixel((c, r))
            brightness = (pixel[0] + pixel[1] + pixel[2]) / 3.0
            color_spread = max(pixel) - min(pixel)
            if brightness > 165 and color_spread < 40:
                is_bg[r][c] = True
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    queue.append((r + dr, c + dc))

    return is_bg


def generate():
    print(f"Loading photo from: {INPUT}")
    orig = Image.open(INPUT).convert("RGB")

    # Zoomed crop focusing on head, face, collar, tie, and shoulders
    # Framing: (269, 80, 1555, 2000)
    cropped = orig.crop((269, 80, 1555, 2000))

    # Pre-process for sharp facial clarity
    sharpened = cropped.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=2))
    contrast = ImageEnhance.Contrast(sharpened).enhance(1.22)
    color_boost = ImageEnhance.Color(contrast).enhance(1.12)

    # Resize to the micro-grid dimensions
    grid_img = color_boost.resize((COLS, ROWS), Image.LANCZOS)
    edges = cropped.convert("L").filter(ImageFilter.FIND_EDGES).resize((COLS, ROWS), Image.LANCZOS)

    bg_mask = build_background_mask(grid_img)

    # Create Retina canvas
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Rounded outer frame border
    draw.rounded_rectangle([(14, 12), (746, 1122)], radius=16, outline=BORDER_COLOR, width=2)

    font = load_font()

    for r in range(ROWS):
        y = OFFSET_Y + r * CELL_H
        for c in range(COLS):
            x = OFFSET_X + c * CELL_W

            if bg_mask[r][c]:
                # Background dot
                draw.text((x + 1, y), "·", fill=DOT_COLOR, font=font)
            else:
                pr, pg, pb = grid_img.getpixel((c, r))
                edge_val = edges.getpixel((c, r))
                lum = (0.299 * pr + 0.587 * pg + 0.114 * pb) / 255.0

                idx = int(lum * (len(RAMP) - 1))
                idx = max(0, min(idx, len(RAMP) - 1))
                char = RAMP[idx]

                # Classify regions for fine-tuned coloring
                is_shirt = lum > 0.72 and max(pr, pg, pb) - min(pr, pg, pb) < 30 and r > 115
                is_skin = (pr > pg > pb) and (pr > 60) and r < 140
                is_dark_feature = (lum < 0.28) and r < 125
                is_glasses_edge = edge_val > 65 and 50 < r < 95 and 35 < c < 105

                if is_shirt:
                    # White shirt collar
                    cr = min(255, int(225 + lum * 30))
                    cg = min(255, int(230 + lum * 25))
                    cb = min(255, int(245 + lum * 10))
                elif is_glasses_edge:
                    # Spectacles frame reflection
                    char = "=" if edge_val > 90 else "-"
                    cr, cg, cb = 175, 215, 245
                elif is_dark_feature and r < 125:
                    # Eyes, eyebrows, mustache, smile shadows
                    char = "@" if lum < 0.18 else "%" if lum < 0.24 else "8"
                    cr = max(42, int(pr * 1.35 + 24))
                    cg = max(38, int(pg * 1.25 + 20))
                    cb = max(38, int(pb * 1.25 + 20))
                elif is_skin:
                    # Warm skin tone with natural highlights
                    cr = min(255, int(pr * 1.18 + 12))
                    cg = min(255, int(pg * 1.06 + 6))
                    cb = min(255, int(pb * 0.92))
                elif r < 60 and lum < 0.35:
                    # Hair: dark slate texture with defined hair shape
                    char = RAMP[min(len(RAMP) - 1, int(lum * 1.5 * len(RAMP)))]
                    cr = max(38, int(pr * 1.45 + 24))
                    cg = max(48, int(pg * 1.45 + 30))
                    cb = max(68, int(pb * 1.55 + 44))
                else:
                    # Suit jacket & tie: deep navy / steel blue
                    cr = max(28, min(255, int(pr * 1.35 + 18)))
                    cg = max(45, min(255, int(pg * 1.40 + 28)))
                    cb = max(78, min(255, int(pb * 1.55 + 52)))

                draw.text((x, y), char, fill=(cr, cg, pb), font=font)

    canvas.save(OUTPUT, "PNG", optimize=True)
    print(f"Generated ultra-high resolution micro-ASCII portrait: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    generate()
