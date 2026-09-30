#!/usr/bin/env python3
"""Self-hosted GitHub stat cards, so the profile never depends on a shared public
service that can go down (github-readme-stats and friends).

    python scripts/cards.py --user seifeddine2003          # fetch live data (needs GITHUB_TOKEN)
    python scripts/cards.py --user seifeddine2003 --offline  # redraw from assets/stats.json

Writes assets/card-stats-*.svg, assets/card-langs-*.svg and one assets/card-<repo>-*.svg
per project listed in assets/projects.json. The fetched numbers are saved to
assets/stats.json so the cards can be redrawn without network access.
"""

from __future__ import annotations

import argparse
import json
import os
import textwrap
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from theme import MONO, SANS, THEMES, esc

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
API = "https://api.github.com"

LANG_COLOURS = {
    "Java": "#B07219", "Python": "#3572A5", "JavaScript": "#F1E05A", "TypeScript": "#3178C6",
    "Jupyter Notebook": "#DA5B0B", "HTML": "#E34C26", "CSS": "#663399", "SQL": "#E38C00",
    "Shell": "#89E051", "C": "#555555", "C++": "#F34B7D", "C#": "#178600", "Kotlin": "#A97BFF",
    "Go": "#00ADD8", "Rust": "#DEA584", "PHP": "#4F5D95", "Dockerfile": "#384D54", "PLpgSQL": "#336790",
}
FALLBACK = ["#AA9BEF", "#22D3EE", "#34D399", "#F472B6", "#FBBF24", "#60A5FA", "#F87171", "#A3E635"]


# --------------------------------------------------------------------------- data

def _req(url: str, token: str | None, body: dict | None = None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-cards"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as r:
        return json.loads(r.read())


def fetch(user: str, token: str | None) -> dict:
    u = _req(f"{API}/users/{user}", token)
    repos = []
    page = 1
    while True:
        batch = _req(f"{API}/users/{user}/repos?per_page=100&type=owner&page={page}", token)
        repos += batch
        if len(batch) < 100:
            break
        page += 1

    own = [r for r in repos if not r["fork"]]
    langs: dict[str, int] = {}
    for r in own:
        try:
            for lang, size in _req(r["languages_url"], token).items():
                langs[lang] = langs.get(lang, 0) + size
        except Exception as e:  # one repo failing shouldn't kill the card
            print(f"  languages for {r['name']} failed: {e}")

    stats = {
        "user": user,
        "name": u.get("name") or user,
        "public_repos": u.get("public_repos"),
        "followers": u.get("followers"),
        "stars": sum(r["stargazers_count"] for r in own),
        "forks": sum(r["forks_count"] for r in own),
        "contributions": None,
        "commits": None,
        "pull_requests": None,
        "languages": langs,
        "languages_basis": "bytes",
        "repos": {
            r["name"]: {
                "description": r.get("description") or "",
                "language": r.get("language"),
                "stars": r["stargazers_count"],
                "forks": r["forks_count"],
                "fork": r["fork"],
            }
            for r in repos
        },
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    if token:
        q = """query($login:String!){user(login:$login){contributionsCollection{
                 totalCommitContributions totalPullRequestContributions
                 contributionCalendar{totalContributions}}}}"""
        try:
            g = _req(f"{API}/graphql", token, {"query": q, "variables": {"login": user}})
            cc = g["data"]["user"]["contributionsCollection"]
            stats["contributions"] = cc["contributionCalendar"]["totalContributions"]
            stats["commits"] = cc["totalCommitContributions"]
            stats["pull_requests"] = cc["totalPullRequestContributions"]
        except Exception as e:
            print(f"  GraphQL contributions unavailable: {e}")
    return stats


# --------------------------------------------------------------------------- drawing

def fmt(v) -> str:
    if v is None:
        return "—"
    if v >= 10000:
        return f"{v / 1000:.0f}k"
    if v >= 1000:
        return f"{v / 1000:.1f}k"
    return str(v)


def frame(w: int, h: int, theme: dict, title: str, right: str, body: str, label: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
<style>.f{{opacity:0;animation:f .6s ease-out forwards}}@keyframes f{{to{{opacity:1}}}}@media (prefers-reduced-motion: reduce){{.f{{animation:none;opacity:1}}}}</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{theme["panel"]}" stroke="{theme["line"]}"/>
<text x="20" y="32" fill="{theme["accent"]}" font-family="{MONO}" font-size="13" font-weight="600">{esc(title)}</text>
<text x="{w - 20}" y="32" text-anchor="end" fill="{theme["muted"]}" font-family="{MONO}" font-size="11">{esc(right)}</text>
{body}
</svg>
"""


def stats_card(s: dict, theme: dict) -> str:
    tiles = [
        ("contributions", "last 12 months", s.get("contributions")),
        ("commits", "last 12 months", s.get("commits")),
        ("pull requests", "last 12 months", s.get("pull_requests")),
        ("public repos", "on GitHub", s.get("public_repos")),
        ("stars earned", "own repos", s.get("stars")),
        ("followers", "and counting", s.get("followers")),
    ]
    w, h = 480, 226
    tw, th, gap, x0, y0 = 140, 78, 10, 20, 50
    body = []
    for i, (name, sub, val) in enumerate(tiles):
        x = x0 + (i % 3) * (tw + gap)
        y = y0 + (i // 3) * (th + gap)
        body.append(
            f'<g class="f" style="animation-delay:{0.1 + i * 0.08:.2f}s">'
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="8" fill="{theme["panel2"]}" stroke="{theme["line"]}"/>'
            f'<text x="{x + 14}" y="{y + 38}" fill="{theme["text"]}" font-family="{SANS}" font-size="26" font-weight="700">{fmt(val)}</text>'
            f'<text x="{x + 14}" y="{y + 57}" fill="{theme["accent2"]}" font-family="{MONO}" font-size="11.5">{esc(name)}</text>'
            f'<text x="{x + 14}" y="{y + 70}" fill="{theme["muted"]}" font-family="{MONO}" font-size="10">{esc(sub)}</text>'
            f"</g>"
        )
    return frame(w, h, theme, "$ gh stats", f"updated {s.get('updated', '')}", "".join(body), "GitHub statistics")


def lang_colour(lang: str, i: int) -> str:
    return LANG_COLOURS.get(lang, FALLBACK[i % len(FALLBACK)])


def langs_card(s: dict, theme: dict, limit: int = 8) -> str:
    items = sorted(s.get("languages", {}).items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in items) or 1
    if len(items) > limit:
        other = sum(v for _, v in items[limit - 1:])
        items = items[: limit - 1] + [("Other", other)]
    w = 480
    rows = (len(items) + 1) // 2
    h = 86 + rows * 24 + 10
    bx, by, bw = 20, 50, w - 40
    body = [f'<clipPath id="bar"><rect x="{bx}" y="{by}" width="{bw}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">']
    x = bx
    for i, (lang, v) in enumerate(items):
        seg = bw * v / total
        body.append(
            f'<rect x="{x:.2f}" y="{by}" width="{seg + 0.5:.2f}" height="10" fill="{lang_colour(lang, i)}" class="f" '
            f'style="animation-delay:{0.1 + i * 0.07:.2f}s"/>'
        )
        x += seg
    body.append("</g>")
    for i, (lang, v) in enumerate(items):
        cx = 20 + (i % 2) * 225
        cy = 90 + (i // 2) * 24
        body.append(
            f'<g class="f" style="animation-delay:{0.3 + i * 0.06:.2f}s">'
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{lang_colour(lang, i)}"/>'
            f'<text x="{cx + 18}" y="{cy}" fill="{theme["text"]}" font-family="{SANS}" font-size="13">{esc(lang)}</text>'
            f'<text x="{cx + 200}" y="{cy}" text-anchor="end" fill="{theme["muted"]}" font-family="{MONO}" font-size="12">{100 * v / total:.1f}%</text>'
            f"</g>"
        )
    basis = "by code size" if s.get("languages_basis") == "bytes" else "by repo count"
    return frame(w, h, theme, "$ most used languages", basis, "".join(body), "most used languages")


def project_card(repo: str, info: dict, override: str | None, theme: dict) -> str:
    w, h = 400, 150
    desc = override or info.get("description") or "No description yet."
    lines = textwrap.wrap(desc, 54)[:4]
    if len(textwrap.wrap(desc, 54)) > 4:
        lines[-1] = lines[-1][:51].rstrip() + "…"
    body = [
        f'<text x="20" y="58" fill="{theme["muted"]}" font-family="{SANS}" font-size="12.5">'
        + "".join(f'<tspan x="20" dy="{0 if i == 0 else 17}">{esc(line)}</tspan>' for i, line in enumerate(lines))
        + "</text>"
    ]
    lang = info.get("language")
    fy = h - 18
    x = 20
    if lang:
        body.append(
            f'<circle cx="{x + 5}" cy="{fy - 4}" r="5" fill="{lang_colour(lang, 0)}"/>'
            f'<text x="{x + 16}" y="{fy}" fill="{theme["text"]}" font-family="{SANS}" font-size="12">{esc(lang)}</text>'
        )
        x += 30 + 7 * len(lang)
    for icon, val in (("★", info.get("stars")), ("⑂", info.get("forks"))):
        if val is not None:
            body.append(
                f'<text x="{x}" y="{fy}" fill="{theme["muted"]}" font-family="{SANS}" font-size="12">{icon} {val}</text>'
            )
            x += 50
    return frame(w, h, theme, repo, "repo", "".join(body), f"{repo} repository card")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--projects", default=str(ASSETS / "projects.json"))
    ap.add_argument("--out", default=str(ASSETS))
    ap.add_argument("--offline", action="store_true", help="redraw from assets/stats.json")
    args = ap.parse_args()

    snapshot = ASSETS / "stats.json"
    if args.offline:
        s = json.loads(snapshot.read_text(encoding="utf-8"))
    else:
        s = fetch(args.user, os.environ.get("GITHUB_TOKEN"))
        snapshot.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    out = Path(args.out)
    projects = json.loads(Path(args.projects).read_text(encoding="utf-8")).get("projects", [])
    for name, theme in THEMES.items():
        (out / f"card-stats-{name}.svg").write_text(stats_card(s, theme), encoding="utf-8")
        (out / f"card-langs-{name}.svg").write_text(langs_card(s, theme), encoding="utf-8")
        for p in projects:
            info = s.get("repos", {}).get(p["repo"], {})
            (out / f"card-{p['repo']}-{name}.svg").write_text(
                project_card(p["repo"], info, p.get("description"), theme), encoding="utf-8"
            )
    print(f"wrote stats, languages and {len(projects)} project cards")


if __name__ == "__main__":
    main()
