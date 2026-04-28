#!/usr/bin/env python3
from __future__ import annotations

"""Rebuild PWA / apple-touch icons: navy blue square + white circle + red bird from public/bsd-logo.png."""

# Matches frontend theme_color / BSD navy
APP_NAVY = (46, 58, 86, 255)  # #2E3A56

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "public" / "bsd-logo.png"
OUT = ROOT / "public"


def bird_sprite_from_logo() -> Image.Image:
    logo = Image.open(LOGO).convert("RGBA")
    a = np.array(logo)
    h, w = a.shape[:2]
    rgb = a[:, :, :3].astype(np.float32)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    red_mask = (r > 115) & (r > g + 25) & (r > b + 25) & (r > 90)

    sy, sx = 222, 711
    bird_mask = np.zeros((h, w), dtype=bool)
    stack = [(sy, sx)]
    while stack:
        y, x = stack.pop()
        if bird_mask[y, x] or not red_mask[y, x]:
            continue
        bird_mask[y, x] = True
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                stack.append((ny, nx))

    sprite = np.zeros_like(a)
    sprite[:] = a
    sprite[~bird_mask, 3] = 0
    ys, xs = np.where(bird_mask)
    ymin, ymax = ys.min(), ys.max()
    xmin, xmax = xs.min(), xs.max()
    return Image.fromarray(sprite[ymin : ymax + 1, xmin : xmax + 1])


def make_icon(size: int, bird_img: Image.Image) -> Image.Image:
    # Full square: branded navy (icons show bird inside white circle on blue)
    canvas = Image.new("RGBA", (size, size), APP_NAVY)
    cx = cy = size // 2
    # Circle radius as fraction of canvas edge length (target ~5% per request)
    r = max(1, round(size * 0.05))
    disk = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(disk).ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 255))
    canvas.alpha_composite(disk)

    bw, bh = bird_img.size
    max_side = int(2 * r * 0.78)
    scale = min(max_side / bw, max_side / bh)
    nw, nh = max(1, int(bw * scale)), max(1, int(bh * scale))
    scaled = bird_img.resize((nw, nh), Image.Resampling.LANCZOS)

    canvas.alpha_composite(scaled, (cx - nw // 2, cy - nh // 2))
    return canvas


def main() -> None:
    bird = bird_sprite_from_logo()
    for name, sz in [("pwa-512.png", 512), ("pwa-192.png", 192)]:
        make_icon(sz, bird).save(OUT / name, format="PNG", optimize=True)
        print("wrote", OUT / name)

    apple = make_icon(180, bird)
    apple.convert("RGB").save(OUT / "apple-touch-icon.png", format="PNG", optimize=True)
    print("wrote", OUT / "apple-touch-icon.png")


if __name__ == "__main__":
    main()
