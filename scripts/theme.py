"""Shared colours for every generated SVG. Change the accent here and rerun the scripts."""

THEMES = {
    "dark": {
        "bg": "#0A101F",
        "panel": "#0D1628",
        "panel2": "#101B30",
        "line": "#25344C",
        "muted": "#8291A8",
        "text": "#DDE7F5",
        "accent": "#AA9BEF",   # lavender - main accent
        "accent2": "#22D3EE",  # cyan - keys, highlights
        "ok": "#34D399",       # green - status
        "dim_dot": "#1A2740",
    },
    "light": {
        "bg": "#F6F8FB",
        "panel": "#FFFFFF",
        "panel2": "#F3F5FA",
        "line": "#D8DEE9",
        "muted": "#65748B",
        "text": "#1E293B",
        "accent": "#6D5BD0",
        "accent2": "#0E7490",
        "ok": "#059669",
        "dim_dot": "#E4E8F1",
    },
}

MONO = "ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def esc(text) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
