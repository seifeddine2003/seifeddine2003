#!/usr/bin/env python3
"""Animated terminal-style banner: assets/banner-dark.svg and assets/banner-light.svg.

Edit assets/profile.json and rerun (the GitHub Action does this for you):
    python scripts/banner.py

Drop a photo at assets/source/photo.png (or .jpg) and the left panel turns into a
halftone dot portrait of you. Without one it draws your initials as an LED matrix.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from theme import MONO, THEMES, esc

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PROFILE = json.loads((ASSETS / "profile.json").read_text(encoding="utf-8"))

W, H = 1180, 610
# left "visual" panel
VX, VY, VW, VH = 35, 88, 418, 472
ART_X, ART_Y, ART_W, ART_H = 49, 136, 390, 390
STEP = 7  # dot grid pitch
# right "terminal" panel
TX, TY, TW, TH = 473, 88, 672, 472


def find_font(size: int) -> ImageFont.ImageFont:
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def art_intensity() -> tuple[np.ndarray, str]:
    """Return a 0..1 intensity map the size of the art area, plus a mode label."""
    for name in ("photo.png", "photo.jpg", "photo.jpeg"):
        src = ASSETS / "source" / name
        if src.exists():
            img = Image.open(src).convert("L")
            img = ImageOps.fit(img, (ART_W, ART_H), centering=(0.5, 0.35))
            img = ImageOps.autocontrast(img, cutoff=2)
            return np.asarray(img, dtype=float) / 255.0, "halftone portrait"

    img = Image.new("L", (ART_W, ART_H), 0)
    d = ImageDraw.Draw(img)
    big = find_font(190)
    small = find_font(88)
    initials = PROFILE.get("initials", "SB")
    bb = d.textbbox((0, 0), initials, font=big)
    d.text(((ART_W - (bb[2] - bb[0])) / 2 - bb[0], 40 - bb[1]), initials, font=big, fill=255)
    tag = "</>"
    bb = d.textbbox((0, 0), tag, font=small)
    d.text(((ART_W - (bb[2] - bb[0])) / 2 - bb[0], 262 - bb[1]), tag, font=small, fill=190)
    return np.asarray(img, dtype=float) / 255.0, "led matrix"


def dots(theme: dict, photo_mode: bool, inten: np.ndarray) -> tuple[str, int]:
    rnd = random.Random(2003)
    buckets: dict[int, list[str]] = {}
    twinkle: list[str] = []
    n = 0
    for gy in range(STEP // 2, ART_H, STEP):
        for gx in range(STEP // 2, ART_W, STEP):
            v = inten[gy - 2:gy + 3, gx - 2:gx + 3].mean()
            if v < (0.18 if photo_mode else 0.3):
                continue
            r = (0.9 + 2.3 * v) if photo_mode else (2.6 if v > 0.55 else 1.9)
            x, y = ART_X + gx, ART_Y + gy
            op = 0.55 + 0.45 * v
            colour = theme["accent"]
            circle = f'<circle cx="{x}" cy="{y}" r="{r:.1f}" fill="{colour}" fill-opacity="{op:.2f}"/>'
            # sweep in from top-left, with some jitter so it feels organic
            k = int(((gy / ART_H) * 0.7 + (gx / ART_W) * 0.3) * 14 + rnd.random() * 3)
            buckets.setdefault(k, []).append(circle)
            if rnd.random() < 0.015:
                twinkle.append(
                    f'<circle cx="{x}" cy="{y}" r="{r + 0.8:.1f}" fill="{theme["accent2"]}" opacity="0">'
                    f'<animate attributeName="opacity" values="0;0.9;0" dur="{2.5 + rnd.random() * 3:.1f}s" '
                    f'begin="{3 + rnd.random() * 4:.1f}s" repeatCount="indefinite"/></circle>'
                )
            n += 1
    out = []
    for k in sorted(buckets):
        out.append(f'<g class="sweep" style="animation-delay:{0.25 + k * 0.12:.2f}s">{"".join(buckets[k])}</g>')
    out.extend(twinkle)
    return "".join(out), n


def terminal(theme: dict) -> str:
    rows = PROFILE["rows"]
    out = []
    x0 = TX + 22
    y = TY + 80
    out.append(
        f'<text x="{x0}" y="{TY + 50}" class="t mono" font-size="14">'
        f'<tspan fill="{theme["ok"]}">➜</tspan> <tspan fill="{theme["accent2"]}">~</tspan>'
        f' <tspan fill="{theme["text"]}">./{esc(PROFILE["handle"])}.sh --whoami</tspan></text>'
    )
    line_h = 26
    start = 0.9
    for i, (key, val) in enumerate(rows):
        yy = y + i * line_h
        is_section = "." not in key
        key_col = theme["accent2"] if not is_section else theme["accent"]
        dots_fill = "." * max(2, 17 - len(key))
        begin = start + i * 0.16
        cw = TW - 44
        out.append(
            f'<clipPath id="r{i}"><rect x="{x0}" y="{yy - 17}" width="0" height="{line_h}">'
            f'<animate attributeName="width" from="0" to="{cw}" begin="{begin:.2f}s" dur="0.42s" fill="freeze"/>'
            f"</rect></clipPath>"
            f'<text x="{x0}" y="{yy}" clip-path="url(#r{i})" font-size="14.5" class="mono">'
            f'<tspan fill="{key_col}">{esc(key)}</tspan>'
            f'<tspan fill="{theme["line"]}"> {dots_fill} </tspan>'
            f'<tspan fill="{theme["text"]}">{esc(val)}</tspan></text>'
        )
    # prompt with blinking cursor
    end = start + len(rows) * 0.16 + 0.5
    py = TY + TH - 26
    out.append(
        f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{end:.2f}s" dur="0.3s" fill="freeze"/>'
        f'<text x="{x0}" y="{py}" font-size="14" class="mono">'
        f'<tspan fill="{theme["ok"]}">●</tspan><tspan fill="{theme["muted"]}"> online</tspan>'
        f'<tspan fill="{theme["line"]}">  │  </tspan>'
        f'<tspan fill="{theme["ok"]}">➜</tspan> <tspan fill="{theme["accent2"]}">~</tspan>'
        f'<tspan fill="{theme["text"]}"> {esc(PROFILE.get("prompt", "git push --force-with-curiosity"))}</tspan></text>'
        f'<rect x="{x0 + 3 + 8.4 * (17 + len(PROFILE.get("prompt", "git push --force-with-curiosity"))):.1f}" '
        f'y="{py - 13}" width="9" height="16" fill="{theme["accent"]}">'
        f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" repeatCount="indefinite"/></rect>'
        f"</g>"
    )
    return "".join(out)


def build(name: str, theme: dict) -> str:
    inten, mode = art_intensity()
    art, n = dots(theme, mode.startswith("halftone"), inten)
    pattern = (
        f'<pattern id="grid" width="{STEP}" height="{STEP}" patternUnits="userSpaceOnUse" '
        f'x="{ART_X}" y="{ART_Y}"><circle cx="{STEP / 2}" cy="{STEP / 2}" r="1" fill="{theme["dim_dot"]}"/></pattern>'
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">{esc(PROFILE["name"])} - live profile</title>
<desc id="desc">Animated terminal profile card with a dot-matrix panel and key facts.</desc>
<style>
.mono{{font-family:{MONO};}}
.sweep{{opacity:0;animation:in .5s ease-out forwards;}}
@keyframes in{{from{{opacity:0}}to{{opacity:1}}}}
@media (prefers-reduced-motion: reduce){{.sweep{{animation:none;opacity:1}}}}
</style>
<defs>{pattern}
<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#02050B" flood-opacity="{'.28' if name == 'dark' else '.10'}"/></filter>
</defs>
<rect width="{W}" height="{H}" rx="18" fill="{theme["bg"]}"/>
<rect x="13" y="13" width="{W - 26}" height="{H - 26}" rx="13" fill="{theme["panel"]}" stroke="{theme["line"]}" filter="url(#shadow)"/>
<path d="M13 62H{W - 13}" stroke="{theme["line"]}"/>
<circle cx="38" cy="38" r="6" fill="#FF5F57"/><circle cx="59" cy="38" r="6" fill="#FEBC2E"/><circle cx="80" cy="38" r="6" fill="#28C840"/>
<text x="{W / 2}" y="43" text-anchor="middle" fill="{theme["muted"]}" class="mono" font-size="13" letter-spacing=".4">{esc(PROFILE["handle"])}@github: ~/profile.sh --live</text>

<rect x="{VX}" y="{VY}" width="{VW}" height="{VH}" rx="6" fill="{theme["panel2"]}" stroke="{theme["line"]}"/>
<path d="M{VX} {VY + 36}H{VX + VW}" stroke="{theme["line"]}"/>
<text x="{VX + 14}" y="{VY + 23}" fill="{theme["muted"]}" class="mono" font-size="12">render/{mode.replace(" ", "_")}.svg</text>
<text x="{VX + VW - 14}" y="{VY + 23}" text-anchor="end" fill="{theme["accent"]}" class="mono" font-size="12">{n:,} px</text>
<rect x="{ART_X}" y="{ART_Y}" width="{ART_W}" height="{ART_H}" fill="url(#grid)"/>
{art}
<text x="{VX + 14}" y="{VY + VH - 14}" fill="{theme["muted"]}" class="mono" font-size="11.5">{esc(PROFILE.get("location", ""))}</text>

<rect x="{TX}" y="{TY}" width="{TW}" height="{TH}" rx="6" fill="{theme["panel2"]}" stroke="{theme["line"]}"/>
{terminal(theme)}
</svg>
"""


def main() -> None:
    for name, theme in THEMES.items():
        (ASSETS / f"banner-{name}.svg").write_text(build(name, theme), encoding="utf-8")
        print(f"wrote assets/banner-{name}.svg")


if __name__ == "__main__":
    main()
