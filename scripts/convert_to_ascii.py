#!/usr/bin/env python3
"""Refined zoomed ASCII-art portrait generator with sharp facial recognition.

Features:
- Closer zoom (head, face, collar, tie, shoulders) matching GitHub avatar scale
- Edge and contrast enhancement so glasses, eyes, mustache, smile are sharply recognizable
- Rich natural color shading (warm skin gradients, deep hair, bright white collar, navy suit)
- Matrix dot background and rounded border
"""

import collections
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "assets" / "new_photo.png"
OUTPUT = ROOT / "assets" / "portrait.png"

# Canvas dimensions
W, H = 380, 567

# Grid sizing: 56 columns x 82 rows
COLS = 56
ROWS = 82

# Cell step
CELL_W = 348.0 / COLS
CELL_H = 540.0 / ROWS
OFFSET_X = 16.0
OFFSET_Y = 13.0

# Colors
BG_COLOR = (1, 5, 12)
BORDER_COLOR = (24, 38, 52)
DOT_COLOR = (18, 30, 44)

# Glyphs
GLYPH_RAMP = [
    ".", ":", ";", "+", "=", "*", 
    "x", "s", "z", "u", "v", 
    "c", "a", "e", "3", "5", "9",
    "0", "A", "C", "D", "E", "F",
    "Q", "O", "8", "B", "%", "&", "#", "@"
]


def load_font():
    candidates = [
        ("C:/Windows/Fonts/courbd.ttf", 9),
        ("C:/Windows/Fonts/consola.ttf", 9),
        ("C:/Windows/Fonts/lucon.ttf", 8),
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
            if brightness > 155 and color_spread < 40:
                is_bg[r][c] = True
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    queue.append((r + dr, c + dc))

    return is_bg


def generate():
    orig = Image.open(INPUT).convert("RGB")
    
    # ── Closer crop: zoom in on head, face, collar & shoulders ──
    # Dimensions of original: 1824 x 2346
    # Target aspect ratio: 380 / 567 = 0.6702
    # Framing from test_zoom2: (269, 80, 1555, 2000)
    cropped = orig.crop((269, 80, 1555, 2000))

    # Enhance sharpness and contrast so eyes, glasses frames, and facial hair are crisp
    sharpened = cropped.filter(ImageFilter.UnsharpMask(radius=3, percent=180, threshold=2))
    contrast = ImageEnhance.Contrast(sharpened).enhance(1.3)
    color_boost = ImageEnhance.Color(contrast).enhance(1.1)

    # Resize to grid
    grid_img = color_boost.resize((COLS, ROWS), Image.LANCZOS)
    # Also get edge map for glasses and facial contours
    edges = cropped.convert("L").filter(ImageFilter.FIND_EDGES).resize((COLS, ROWS), Image.LANCZOS)

    bg_mask = build_background_mask(grid_img)

    canvas = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Rounded outer border
    draw.rounded_rectangle([(7, 6), (366, 556)], radius=8, outline=BORDER_COLOR, width=1)

    font = load_font()

    for r in range(ROWS):
        y = OFFSET_Y + r * CELL_H
        for c in range(COLS):
            x = OFFSET_X + c * CELL_W

            if bg_mask[r][c]:
                # Background dot
                draw.text((x + 2, y), "·", fill=DOT_COLOR, font=font)
            else:
                pr, pg, pb = grid_img.getpixel((c, r))
                edge_val = edges.getpixel((c, r))
                lum = 0.299 * pr + 0.587 * pg + 0.114 * pb
                norm_lum = lum / 255.0

                # Determine glyph index
                glyph_idx = int(norm_lum * (len(GLYPH_RAMP) - 1))
                glyph_idx = max(0, min(glyph_idx, len(GLYPH_RAMP) - 1))
                char = GLYPH_RAMP[glyph_idx]

                # Special feature tuning:
                is_shirt = norm_lum > 0.72 and max(pr, pg, pb) - min(pr, pg, pb) < 30 and r > 50
                is_skin = (pr > pg > pb) and (pr > 60) and r < 60
                is_dark_feature = (norm_lum < 0.28 or edge_val > 55) and r < 60

                if is_shirt:
                    # White shirt collar
                    cr = min(255, int(220 + norm_lum * 35))
                    cg = min(255, int(225 + norm_lum * 30))
                    cb = min(255, int(240 + norm_lum * 15))
                elif is_dark_feature and r < 52:
                    # Eyes, glasses, eyebrows, mustache: crisp dark definition
                    char = "@" if norm_lum < 0.18 else "%" if norm_lum < 0.24 else "8"
                    # Deep warm charcoal / dark amber
                    cr = max(40, int(pr * 1.3 + 20))
                    cg = max(35, int(pg * 1.2 + 18))
                    cb = max(35, int(pb * 1.2 + 18))
                elif is_skin:
                    # Warm skin tone with natural lighting gradient
                    cr = min(255, int(pr * 1.15 + 10))
                    cg = min(255, int(pg * 1.02 + 5))
                    cb = min(255, int(pb * 0.90))
                elif r < 24 and norm_lum < 0.35:
                    # Hair: dark slate / charcoal
                    cr = max(28, int(pr * 1.3 + 18))
                    cg = max(36, int(pg * 1.3 + 24))
                    cb = max(52, int(pb * 1.4 + 36))
                else:
                    # Suit jacket & tie: navy / steel blue
                    cr = max(24, min(255, int(pr * 1.30 + 15)))
                    cg = max(38, min(255, int(pg * 1.35 + 24)))
                    cb = max(68, min(255, int(pb * 1.50 + 48)))

                draw.text((x, y), char, fill=(cr, cg, pb), font=font)

    canvas.save(OUTPUT, "PNG", optimize=True)
    print(f"Generated zoomed ASCII portrait: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    generate()
