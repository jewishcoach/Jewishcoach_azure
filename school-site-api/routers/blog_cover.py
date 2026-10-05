"""Blog Cover SVG Generator — deterministic abstract covers in BSD design system."""

import hashlib
import math

from fastapi import APIRouter
from fastapi.responses import Response

import db

router = APIRouter(tags=["blog-cover"])


def _hash_floats(slug: str, count: int, seed: str = "") -> list[float]:
    h = hashlib.sha256(f"{slug}:{seed}".encode()).hexdigest()
    floats = []
    for i in range(count):
        chunk = h[(i * 4) % len(h):(i * 4 + 4) % len(h)] or h[:4]
        floats.append(int(chunk, 16) / 65535.0)
    return floats


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


COLORS = {
    "bg_dark": "#0F1B26",
    "bg_mid": "#1a2838",
    "navy": "#1a2838",
    "navy_deep": "#0F1B26",
    "cyan": "#03ffe6",
    "cyan_soft": "#03ffe680",
    "teal": "#008577",
    "teal_light": "#00d6c0",
    "cream": "#faf7f0",
    "cream_warm": "#fdfaf4",
    "gold_soft": "#d4a843",
}

CATEGORY_COLORS = {
    "coaching": ("cyan", "teal_light"),
    "leadership": ("teal", "cyan"),
    "methodology": ("teal_light", "gold_soft"),
    "parasha": ("gold_soft", "cream"),
    "business": ("cyan", "teal"),
}


def _render_title_text(title: str, W: int, H: int, c: dict) -> str:
    """Render title text + BSD branding on the cover SVG."""
    if not title:
        return ""
    lines = _wrap_title(title, max_chars=28)
    num_lines = len(lines)
    font_size = 42 if num_lines <= 2 else 36
    line_height = font_size * 1.4
    total_height = num_lines * line_height
    start_y = (H / 2) - (total_height / 2) + font_size * 0.35

    text_els = []
    for i, line in enumerate(lines):
        from html import escape
        y = start_y + i * line_height
        text_els.append(
            f'<text x="{W/2}" y="{y:.0f}" text-anchor="middle" direction="rtl" '
            f'font-family="\'Heebo\', \'Arial Hebrew\', sans-serif" font-weight="700" '
            f'font-size="{font_size}" fill="white" opacity="0.95">{escape(line)}</text>'
        )

    brand_y = H - 30
    text_els.append(
        f'<text x="{W/2}" y="{brand_y}" text-anchor="middle" '
        f'font-family="\'Heebo\', sans-serif" font-weight="400" '
        f'font-size="16" fill="{c["cyan"]}" opacity="0.7">בית הספר לאימון יהודי · BSD</text>'
    )

    return "\n  ".join(text_els)


def _wrap_title(title: str, max_chars: int = 28) -> list[str]:
    """Split Hebrew title into lines of max_chars, breaking on spaces."""
    words = title.split()
    lines, current = [], ""
    for w in words:
        test = f"{current} {w}".strip() if current else w
        if len(test) <= max_chars:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines[:3]


def generate_cover_svg(slug: str, category: str = "coaching", title: str = "") -> str:
    W, H = 1200, 630
    vals = _hash_floats(slug, 32)
    c = COLORS
    cat_pair = CATEGORY_COLORS.get(category.lower(), ("cyan", "teal_light"))
    accent1 = c[cat_pair[0]]
    accent2 = c[cat_pair[1]]

    mesh_stops = []
    for i in range(4):
        cx = _lerp(200, 1000, vals[i])
        cy = _lerp(100, 530, vals[i + 4])
        r = _lerp(250, 500, vals[i + 8])
        opacity = _lerp(0.25, 0.6, vals[i + 12])
        grad_colors = [c["navy"], c["teal"], accent1, accent2]
        mesh_stops.append((cx, cy, r, opacity, grad_colors[i % 4]))

    shapes_svg = _generate_shapes(category, vals, W, H, c, accent1, accent2)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c["bg_dark"]}"/>
      <stop offset="50%" stop-color="{c["bg_mid"]}"/>
      <stop offset="100%" stop-color="{c["bg_dark"]}"/>
    </linearGradient>
    <radialGradient id="m0" cx="{mesh_stops[0][0]/W*100:.1f}%" cy="{mesh_stops[0][1]/H*100:.1f}%" r="{mesh_stops[0][2]/W*100:.1f}%">
      <stop offset="0%" stop-color="{mesh_stops[0][4]}" stop-opacity="{mesh_stops[0][3]:.2f}"/>
      <stop offset="100%" stop-color="{mesh_stops[0][4]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="m1" cx="{mesh_stops[1][0]/W*100:.1f}%" cy="{mesh_stops[1][1]/H*100:.1f}%" r="{mesh_stops[1][2]/W*100:.1f}%">
      <stop offset="0%" stop-color="{mesh_stops[1][4]}" stop-opacity="{mesh_stops[1][3]:.2f}"/>
      <stop offset="100%" stop-color="{mesh_stops[1][4]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="m2" cx="{mesh_stops[2][0]/W*100:.1f}%" cy="{mesh_stops[2][1]/H*100:.1f}%" r="{mesh_stops[2][2]/W*100:.1f}%">
      <stop offset="0%" stop-color="{mesh_stops[2][4]}" stop-opacity="{mesh_stops[2][3]:.2f}"/>
      <stop offset="100%" stop-color="{mesh_stops[2][4]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="m3" cx="{mesh_stops[3][0]/W*100:.1f}%" cy="{mesh_stops[3][1]/H*100:.1f}%" r="{mesh_stops[3][2]/W*100:.1f}%">
      <stop offset="0%" stop-color="{mesh_stops[3][4]}" stop-opacity="{mesh_stops[3][3]:.2f}"/>
      <stop offset="100%" stop-color="{mesh_stops[3][4]}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{accent1}" stop-opacity="0.35"/>
      <stop offset="60%" stop-color="{c['teal']}" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="{c['navy_deep']}" stop-opacity="0"/>
    </radialGradient>
    <filter id="grain" x="0%" y="0%" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" result="n"/>
      <feColorMatrix type="saturate" values="0" in="n" result="g"/>
      <feBlend in="SourceGraphic" in2="g" mode="overlay"/>
    </filter>
    <filter id="blur_s"><feGaussianBlur stdDeviation="20"/></filter>
    <filter id="blur_m"><feGaussianBlur stdDeviation="40"/></filter>
    <radialGradient id="vig" cx="50%" cy="50%" r="70%">
      <stop offset="0%" stop-color="white" stop-opacity="0"/>
      <stop offset="100%" stop-color="black" stop-opacity="0.45"/>
    </radialGradient>
  </defs>

  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <rect width="{W}" height="{H}" fill="url(#m0)" filter="url(#blur_m)"/>
  <rect width="{W}" height="{H}" fill="url(#m1)" filter="url(#blur_m)"/>
  <rect width="{W}" height="{H}" fill="url(#m2)" filter="url(#blur_s)"/>
  <rect width="{W}" height="{H}" fill="url(#m3)" filter="url(#blur_s)"/>
  <ellipse cx="{W/2 + (vals[20]-0.5)*200:.0f}" cy="{H/2 + (vals[21]-0.5)*100:.0f}" rx="350" ry="250" fill="url(#glow)" filter="url(#blur_s)"/>
  {shapes_svg}
  <rect width="{W}" height="{H}" fill="transparent" filter="url(#grain)" opacity="0.03"/>
  <rect width="{W}" height="{H}" fill="url(#vig)"/>
  <line x1="0" y1="0" x2="{W}" y2="0" stroke="{c['cyan']}" stroke-width="1.5" opacity="0.3"/>
  {_render_title_text(title, W, H, c)}
</svg>'''
    return svg


def _generate_shapes(category: str, vals: list, W: int, H: int, c: dict, accent1: str, accent2: str) -> str:
    cat = (category or "coaching").lower()
    if cat == "coaching":
        return _shapes_orbs(vals, W, H, accent1, accent2)
    elif cat == "leadership":
        return _shapes_peaks(vals, W, H, accent1, accent2)
    elif cat == "methodology":
        return _shapes_steps(vals, W, H, accent1, accent2)
    elif cat == "parasha":
        return _shapes_waves(vals, W, H, accent1, accent2)
    elif cat == "business":
        return _shapes_grid(vals, W, H, accent1, accent2)
    return _shapes_orbs(vals, W, H, accent1, accent2)


def _shapes_orbs(vals: list, W: int, H: int, a1: str, a2: str) -> str:
    shapes = []
    cx, cy = W * 0.5 + (vals[16] - 0.5) * 200, H * 0.5 + (vals[17] - 0.5) * 80
    r = _lerp(80, 140, vals[18])
    shapes.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r*2.2:.0f}" fill="none" stroke="{a1}" stroke-width="0.5" opacity="0.15"/>')
    shapes.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r*1.6:.0f}" fill="none" stroke="{a2}" stroke-width="0.8" opacity="0.2"/>')
    shapes.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="{a1}" opacity="0.2" filter="url(#blur_s)"/>')
    shapes.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r*0.5:.0f}" fill="{a2}" opacity="0.3" filter="url(#blur_s)"/>')
    for i in range(3):
        angle = vals[19 + i] * math.pi * 2
        dist = _lerp(180, 300, vals[22 + i])
        sx, sy = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist * 0.6
        sr = _lerp(20, 50, vals[25 + i])
        op = _lerp(0.1, 0.25, vals[28 + i])
        shapes.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="{sr:.0f}" fill="{a1}" opacity="{op:.2f}" filter="url(#blur_s)"/>')
    return "\n  ".join(shapes)


def _shapes_peaks(vals: list, W: int, H: int, a1: str, a2: str) -> str:
    shapes = []
    for i in range(5):
        x = _lerp(100, W - 100, vals[16 + i])
        peak_h = _lerp(100, 350, vals[21 + i])
        w = _lerp(60, 150, vals[26 + i])
        op = _lerp(0.08, 0.2, vals[i])
        shapes.append(f'<polygon points="{x:.0f},{H} {x-w:.0f},{H} {x-w/2:.0f},{H-peak_h:.0f}" fill="{a1 if i%2==0 else a2}" opacity="{op:.2f}"/>')
    return "\n  ".join(shapes)


def _shapes_steps(vals: list, W: int, H: int, a1: str, a2: str) -> str:
    shapes = []
    step_w = W / 6
    for i in range(6):
        x = i * step_w
        h = _lerp(80, H * 0.7, (i + 1) / 6 * vals[16 + i])
        op = _lerp(0.06, 0.15, vals[22 + i])
        shapes.append(f'<rect x="{x:.0f}" y="{H-h:.0f}" width="{step_w-8:.0f}" height="{h:.0f}" fill="{a1 if i%2==0 else a2}" opacity="{op:.2f}" rx="4"/>')
    return "\n  ".join(shapes)


def _shapes_waves(vals: list, W: int, H: int, a1: str, a2: str) -> str:
    shapes = []
    for layer in range(3):
        points = []
        y_base = H * 0.4 + layer * 80
        for i in range(13):
            x = i * (W / 12)
            y = y_base + math.sin(i * 0.8 + vals[16 + layer] * 6) * _lerp(30, 80, vals[20 + layer])
            points.append(f"{x:.0f},{y:.0f}")
        points.append(f"{W},{H}")
        points.append(f"0,{H}")
        op = _lerp(0.06, 0.15, vals[25 + layer])
        shapes.append(f'<polygon points="{" ".join(points)}" fill="{a1 if layer%2==0 else a2}" opacity="{op:.2f}"/>')
    return "\n  ".join(shapes)


def _shapes_grid(vals: list, W: int, H: int, a1: str, a2: str) -> str:
    shapes = []
    cols, rows = 8, 5
    cw, ch = W / cols, H / rows
    for r in range(rows):
        for col in range(cols):
            idx = r * cols + col
            if vals[idx % 32] > 0.6:
                x, y = col * cw + 4, r * ch + 4
                op = _lerp(0.04, 0.12, vals[(idx + 5) % 32])
                shapes.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{cw-8:.0f}" height="{ch-8:.0f}" rx="6" fill="{a1 if idx%3==0 else a2}" opacity="{op:.2f}"/>')
    return "\n  ".join(shapes)


@router.get("/api/public/blog-cover/{slug}")
async def get_cover(slug: str, category: str = "coaching"):
    title = slug.replace("-", " ")
    try:
        post = db.get_post(slug)
        if post:
            title = post.title
            category = post.category or category
    except Exception:
        pass
    svg = generate_cover_svg(slug, category, title=title)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
