#!/usr/bin/env python3
"""Radar (spider) charts from a small JSON file, in dark and light versions.

    python scripts/radar.py --data assets/skills.json    -o assets/radar
    python scripts/radar.py --data assets/languages.json -o assets/radar-langs --values

The JSON looks like {"title": "...", "axes": [{"label": "Java", "value": 75}, ...]},
values from 0 to 100.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from theme import MONO, SANS, THEMES, esc

W, H = 460, 420
CX, CY, R = W / 2, 226, 118
RINGS = 4


def point(i: int, n: int, radius: float) -> tuple[float, float]:
    a = -math.pi / 2 + 2 * math.pi * i / n
    return CX + radius * math.cos(a), CY + radius * math.sin(a)


def build(data: dict, theme: dict, show_values: bool) -> str:
    axes = data["axes"]
    n = len(axes)
    parts = []

    # rings and spokes
    for k in range(1, RINGS + 1):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, n, R * k / RINGS) for i in range(n)))
        parts.append(
            f'<polygon points="{pts}" fill="{theme["panel2"] if k == RINGS else "none"}" '
            f'stroke="{theme["line"]}" stroke-width="1"/>'
        )
    for i in range(n):
        x, y = point(i, n, R)
        parts.append(f'<line x1="{CX}" y1="{CY}" x2="{x:.1f}" y2="{y:.1f}" stroke="{theme["line"]}"/>')

    # data polygon (grows out from the centre)
    vals = [max(0, min(100, a["value"])) / 100 for a in axes]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, n, R * v) for i, v in enumerate(vals)))
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{theme["accent"]}" stroke="{theme["panel"]}" stroke-width="1.5"/>'
        for x, y in (point(i, n, R * v) for i, v in enumerate(vals))
    )
    parts.append(
        f'<g class="grow"><polygon points="{pts}" fill="{theme["accent"]}" fill-opacity=".22" '
        f'stroke="{theme["accent"]}" stroke-width="2" stroke-linejoin="round"/>{dots}</g>'
    )

    # labels
    for i, a in enumerate(axes):
        x, y = point(i, n, R + 22)
        anchor = "middle"
        if x < CX - 8:
            anchor = "end"
        elif x > CX + 8:
            anchor = "start"
        dy = 4
        if y < CY - R:
            dy = -2
        elif y > CY + R:
            dy = 10
        label = a["label"]
        lines = [label]
        if len(label) > 12 and " " in label:
            # break long labels onto two lines at the space nearest the middle
            cut = min((i for i, ch in enumerate(label) if ch == " "), key=lambda i: abs(i - len(label) / 2))
            lines = [label[:cut], label[cut + 1:]]
        if len(lines) == 2 and dy != 10:
            dy -= 7
        value = f'<tspan fill="{theme["accent2"]}" font-family="{MONO}" font-size="11.5"> {a["value"]}</tspan>' if show_values else ""
        spans = "".join(
            f'<tspan x="{x:.1f}" dy="{0 if j == 0 else 15}">{esc(t)}</tspan>' for j, t in enumerate(lines)
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}" fill="{theme["text"]}" '
            f'font-family="{SANS}" font-size="12.5">{spans}{value}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(data.get("title", "radar chart"))}">
<style>
.grow{{transform-origin:{CX}px {CY}px;transform:scale(0);animation:g .9s cubic-bezier(.2,.8,.2,1) .2s forwards;}}
@keyframes g{{to{{transform:scale(1)}}}}
@media (prefers-reduced-motion: reduce){{.grow{{animation:none;transform:none}}}}
</style>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="{theme["panel"]}" stroke="{theme["line"]}"/>
<text x="20" y="32" fill="{theme["accent"]}" font-family="{MONO}" font-size="13" font-weight="600">{esc(data.get("title", ""))}</text>
<text x="{W - 20}" y="32" text-anchor="end" fill="{theme["muted"]}" font-family="{MONO}" font-size="11">{esc(data.get("subtitle", "self-rated · 0-100"))}</text>
{"".join(parts)}
</svg>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("-o", "--out", required=True, help="output prefix, e.g. assets/radar")
    ap.add_argument("--values", action="store_true", help="print the number next to each label")
    args = ap.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    for name, theme in THEMES.items():
        out = Path(f"{args.out}-{name}.svg")
        out.write_text(build(data, theme, args.values), encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
