#!/usr/bin/env python3
"""High-fidelity ASCII-art portrait generator matching the exact design of portrait_old.png.

Features:
- Exact 380x567 canvas with rounded rectangle border and corner radius
- Matrix-style dot grid for background
- Clean silhouette segmentation (removes passport background, preserves white shirt collar)
- Rich ASCII / code glyphs with enhanced local contrast for eyes, glasses, mustache, and hair
- Faithful color sampling with contrast boost for terminal display
"""

import collections
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "assets" / "new_photo.png"
OUTPUT = ROOT / "assets" / "portrait.png"

# Canvas dimensions matching portrait_old.png exactly
W, H = 380, 567

# Grid sizing: 54 columns x 80 rows
COLS = 54
ROWS = 80

# Cell step
CELL_W = 348.0 / COLS
CELL_H = 540.0 / ROWS
OFFSET_X = 16.0
OFFSET_Y = 13.0

# Colors
BG_COLOR = (1, 5, 12)          # canvas background
BORDER_COLOR = (24, 38, 52)     # rounded frame border
DOT_COLOR = (18, 30, 44)        # faint dot grid

# ASCII character ramps
# From darkest to brightest
GLYPH_RAMP = [
    ".", ":", ";", "+", "=", "*", 
    "x", "s", "z", "u", "v", 
    "c", "a", "e", "3", "5", "9",
    "0", "A", "C", "D", "E", "F",
    "Q", "O", "8", "B", "%", "&", "#", "@"
]


def load_font():
    """Load bold monospace font for crisp ASCII rendering."""
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
    """Segment background from subject using flood-fill from border.
    
    Identifies the bright off-white passport photo background without
    touching the white shirt inside the suit.
    """
    cols, rows = img_small.size
    is_bg = [[False] * cols for _ in range(rows)]
    queue = collections.deque()

    # Seed all border cells
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
            # Background is bright (>160) and neutral cream/gray (spread < 35)
            if brightness > 160 and color_spread < 35:
                is_bg[r][c] = True
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    queue.append((r + dr, c + dc))

    return is_bg


def generate():
    print(f"Loading input photo from: {INPUT}")
    orig = Image.open(INPUT).convert("RGB")
    orig_w, orig_h = orig.size

    # Crop to portrait ratio (380 / 567)
    target_ratio = W / H
    current_ratio = orig_w / orig_h

    if current_ratio > target_ratio:
        crop_w = int(orig_h * target_ratio)
        left = (orig_w - crop_w) // 2
        cropped = orig.crop((left, 0, left + crop_w, orig_h))
    else:
        crop_h = int(orig_w / target_ratio)
        cropped = orig.crop((0, 0, orig_w, crop_h))

    # Pre-process image to enhance facial contrast and details
    # 1. Sharpen
    sharpened = cropped.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    # 2. Boost contrast
    contrast = ImageEnhance.Contrast(sharpened).enhance(1.25)
    # 3. Boost color saturation slightly
    color_boost = ImageEnhance.Color(contrast).enhance(1.15)

    # Resize to the ASCII grid size
    grid_img = color_boost.resize((COLS, ROWS), Image.LANCZOS)
    bg_mask = build_background_mask(grid_img)

    # Create canvas
    canvas = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Draw rounded outer border matching original
    draw.rounded_rectangle([(7, 6), (366, 556)], radius=8, outline=BORDER_COLOR, width=1)

    font = load_font()

    # Render each cell
    for r in range(ROWS):
        y = OFFSET_Y + r * CELL_H
        for c in range(COLS):
            x = OFFSET_X + c * CELL_W
            cell_is_bg = bg_mask[r][c]

            if cell_is_bg:
                # Faint background dot
                draw.text((x + 2, y), "·", fill=DOT_COLOR, font=font)
            else:
                # Subject pixel
                pr, pg, pb = grid_img.getpixel((c, r))
                lum = 0.299 * pr + 0.587 * pg + 0.114 * pb
                norm_lum = lum / 255.0

                # Select glyph from ramp based on luminance
                glyph_idx = int(norm_lum * (len(GLYPH_RAMP) - 1))
                glyph_idx = max(0, min(glyph_idx, len(GLYPH_RAMP) - 1))
                char = GLYPH_RAMP[glyph_idx]

                # Fine-tuned color enhancement:
                # 1. White shirt / collar: high luminance + neutral color
                if norm_lum > 0.70 and max(pr, pg, pb) - min(pr, pg, pb) < 32:
                    cr = min(255, int(220 + norm_lum * 35))
                    cg = min(255, int(225 + norm_lum * 30))
                    cb = min(255, int(238 + norm_lum * 17))
                # 2. Skin (face, ears, neck): warm golden / peach
                elif pr > pg and pr > pb and norm_lum > 0.28:
                    cr = min(255, int(pr * 1.20 + 10))
                    cg = min(255, int(pg * 1.05 + 5))
                    cb = min(255, int(pb * 0.90))
                # 3. Facial features (eyes, glasses, mustache, eyebrows): dark with good definition
                elif norm_lum < 0.28 and r < 48:
                    cr = max(35, int(pr * 1.5 + 25))
                    cg = max(45, int(pg * 1.5 + 30))
                    cb = max(60, int(pb * 1.5 + 40))
                # 4. Suit & tie (lower torso): navy / steel blue
                else:
                    cr = max(26, min(255, int(pr * 1.30 + 18)))
                    cg = max(42, min(255, int(pg * 1.35 + 28)))
                    cb = max(70, min(255, int(pb * 1.55 + 50)))

                draw.text((x, y), char, fill=(cr, cg, pb), font=font)

    # Save output
    canvas.save(OUTPUT, "PNG", optimize=True)
    print(f"Generated high-fidelity ASCII portrait: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    generate()
