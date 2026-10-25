#!/usr/bin/env python3
"""Artistic ASCII-art portrait generator matching the exact aesthetic of the original portrait_old.png.

Matches:
- Exact 52 cols x 78 rows grid (~7px spacing) identical to portrait_old.png
- High-contrast stylish dark glasses lenses matching the original sunglasses aesthetic
- Luminous golden-peach skin tones with glowing '8', '0', 'B', 'O' characters
- Defined facial structure (mustache, smile, jawline)
- Crisp brilliant white shirt collar
- Rich textured navy suit jacket with steel-blue highlights
- Faint dot grid matrix background and rounded card frame
"""

import collections
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "assets" / "new_photo.png"
OUTPUT = ROOT / "assets" / "portrait.png"

# Canvas dimensions
W, H = 380, 567

# Grid sizing: 52 columns x 78 rows (identical to portrait_old.png)
COLS = 52
ROWS = 78

CELL_W = 348.0 / COLS
CELL_H = 540.0 / ROWS
OFFSET_X = 16.0
OFFSET_Y = 13.0

# Colors
BG_COLOR = (1, 5, 12)
BORDER_COLOR = (24, 38, 52)
DOT_COLOR = (18, 30, 44)

# Character sets
RAMP_BRIGHT = ["8", "0", "B", "O", "&", "%", "#", "@"]
RAMP_MID    = ["9", "5", "3", "A", "C", "D", "E", "F", "Q"]
RAMP_SUIT   = ["X", "8", "0", "%", "&", "#", "*", "+", "=", "~", "s"]
RAMP_SHIRT  = ["0", "8", "B", "O", "&", "%", "#", "@", "W"]


def load_font():
    """Load bold crisp monospace font."""
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
            if brightness > 165 and color_spread < 40:
                is_bg[r][c] = True
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    queue.append((r + dr, c + dc))

    return is_bg


def generate():
    orig = Image.open(INPUT).convert("RGB")
    w, h = orig.size

    # Natural framing: full shoulders across bottom, head centered
    crop_w = int(h * W / H)
    left = (w - crop_w) // 2
    crop = orig.crop((left, 0, left + crop_w, h))

    # Pre-process for sharp contrast
    sharpened = crop.filter(ImageFilter.UnsharpMask(radius=3, percent=170, threshold=2))
    contrast = ImageEnhance.Contrast(sharpened).enhance(1.22)
    color_boost = ImageEnhance.Color(contrast).enhance(1.15)

    small = color_boost.resize((COLS, ROWS), Image.LANCZOS)
    bg_mask = build_background_mask(small)

    canvas = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Frame border
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
                pr, pg, pb = small.getpixel((c, r))
                lum = (0.299 * pr + 0.587 * pg + 0.114 * pb) / 255.0

                # Precise feature coordinates:
                # 1. Glasses lenses (styled like the iconic dark glasses in portrait_old):
                is_left_lens  = (17 <= c <= 22) and (25 <= r <= 29)
                is_right_lens = (26 <= c <= 31) and (25 <= r <= 29)
                is_glasses_rim = (c in (16, 23, 25, 32) and 25 <= r <= 29) or (r in (24, 30) and (17 <= c <= 22 or 26 <= c <= 31))

                # 2. White shirt collar & tie
                is_shirt = lum > 0.68 and max(pr, pg, pb) - min(pr, pg, pb) < 32 and r > 44
                is_tie = 48 < r < 72 and 22 < c < 28 and pb > pr and lum < 0.35

                # 3. Facial features (mustache, lips, nostrils)
                is_mustache = 32 <= r <= 35 and 20 <= c <= 28 and lum < 0.32
                is_skin = (pr > pg > pb) and (pr > 70) and r < 48
                is_hair = r < 23 and lum < 0.35

                if is_left_lens or is_right_lens:
                    # Stylish dark blue glasses lenses matching original sunglasses
                    char = "0" if (c in (19, 20, 28, 29) and r in (26, 27, 28)) else "8"
                    cr, cg, cb = 18, 42, 92
                elif is_glasses_rim:
                    # Subtle steel frame outline
                    char = "=" if r in (24, 30) else "x"
                    cr, cg, cb = 95, 145, 205
                elif is_shirt:
                    # Brilliant crisp white collar
                    char = RAMP_SHIRT[(r * 5 + c * 3) % len(RAMP_SHIRT)]
                    cr, cg, cb = 245, 248, 255
                elif is_tie:
                    # Rich royal blue necktie
                    char = RAMP_SUIT[(r * 7 + c * 3) % len(RAMP_SUIT)]
                    cr, cg, cb = 38, 70, 150
                elif is_mustache:
                    # Defined mustache
                    char = "%" if lum < 0.22 else "8"
                    cr, cg, cb = 68, 48, 38
                elif is_skin:
                    # Luminous warm golden-peach skin tones
                    if lum > 0.52:
                        char = RAMP_BRIGHT[(r * 5 + c * 3) % len(RAMP_BRIGHT)]
                        cr, cg, cb = 255, 215, 172
                    elif lum > 0.35:
                        char = RAMP_MID[(r * 5 + c * 3) % len(RAMP_MID)]
                        cr, cg, cb = 242, 192, 146
                    else:
                        char = "8" if lum < 0.22 else "9"
                        cr, cg, cb = 195, 140, 98
                elif is_hair:
                    # Dark wavy hair texture
                    char = RAMP_SUIT[(r * 11 + c * 7) % len(RAMP_SUIT)]
                    cr, cg, cb = 42, 54, 75
                else:
                    # Navy suit jacket with rich denim/steel highlights
                    char = RAMP_SUIT[(r * 9 + c * 5) % len(RAMP_SUIT)]
                    cr = max(32, min(255, int(pr * 1.35 + 24)))
                    cg = max(52, min(255, int(pg * 1.40 + 36)))
                    cb = max(95, min(255, int(pb * 1.60 + 68)))

                draw.text((x, y), char, fill=(cr, cg, pb), font=font)

    canvas.save(OUTPUT, "PNG", optimize=True)
    print(f"Generated artistic portrait: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    generate()
