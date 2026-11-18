"""Shared rendering core for Grok Life visuals: HTML/CSS/SVG -> PNG with headless Chromium (Playwright).

One token set for every image: type, spacing, colour, radius, elevation. Fonts are bundled in fonts/ (all SIL OFL)
and embedded as base64 into every page, so renders are identical on every box.
"""
import base64
import json as _json
import math
import os
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).parent
FONT_DIR = HERE / "fonts"

# ---- spacing -------------------------------------------------------------------
# One scale. Every margin, gap and height in the images comes from it (4 only inside small parts).
SP = dict(xs=4, s=8, m=16, l=24, xl=32, xxl=48)
PAGE_PAD = 24          # outer margin; content column is 480 - 2 x 24 = 432 wide
ROW_H = 52             # one list row (icon, name, value, percent), its 2 px progress rule sits on the bottom edge
RADIUS = 16            # the only corner radius (photo frames, chips). Bars and dots are fully round.

# ---- colour --------------------------------------------------------------------
# Tokens come from themes.py (palette x light or dark) and are swapped by set_theme(). Every renderer reads these names at
# call time, so one call re-skins every image. No glow, no glass, no gradients on text. Pillar hues are flat.
import sys
import themes as _themes

BG = SURFACE = TEXT = TEXT2 = TEXT3 = HAIR = TRACK = ON_ACCENT = GOOD = MODE = PALETTE = ""
SOLID = {}
TOKEN_NAMES = ("BG", "SURFACE", "TEXT", "TEXT2", "TEXT3", "HAIR", "TRACK", "ON_ACCENT", "GOOD", "MODE", "PALETTE")
_PATCH_MODULES = ("render", "render_meds", "render_modules", "compare_photos", "__main__")


def set_theme(mode="light", palette=None):
    """Select light or dark (and a palette). Updates this module and every renderer module that imported the names."""
    global BG, SURFACE, TEXT, TEXT2, TEXT3, HAIR, TRACK, ON_ACCENT, GOOD, MODE, PALETTE
    t = _themes.tokens(palette, mode)
    BG, SURFACE, TEXT, TEXT2, TEXT3 = t["bg"], t["surface"], t["text"], t["text2"], t["text3"]
    HAIR, TRACK, ON_ACCENT, MODE, PALETTE = t["hair"], t["track"], t["onAccent"], t["mode"], t["palette"]
    h = t["hues"]
    SOLID.clear()
    SOLID.update(recovery=h["recovery"], sleep=h["sleep"], nutrition=h["nutrition"], hydration=h["hydration"],
                 activity=h["activity"], medication=h["medication"], weight=TEXT,
                 protein=h["nutrition"], carbs=h["nutrition"], fat=h["nutrition"],
                 cal=h["nutrition"], water=h["hydration"], steps=h["activity"], workouts=h["activity"])
    GOOD = h["recovery"]
    here = sys.modules[__name__]
    for name in _PATCH_MODULES:
        m = sys.modules.get(name)
        if name == "__main__" and Path(getattr(m, "__file__", "") or "").stem not in ("render", "render_modules", "render_meds", "compare_photos"):
            continue  # e.g. charts.py running its own fallback: leave its colours alone
        if m is not None:
            for n in TOKEN_NAMES:
                if hasattr(m, n):
                    setattr(m, n, getattr(here, n))
    return t


def ink(a):
    """The text colour at alpha a: hairlines, segment fills, tracks that must work in both modes."""
    return rgba(TEXT if TEXT.startswith("#") else "#000000", a)


set_theme(os.environ.get("GROKLIFE_THEME", "light") if os.environ.get("GROKLIFE_THEME") in ("light", "dark") else "light")
ICON_PATH = HERE / "icons" / "lucide.json"
_ICONS = _json.loads(ICON_PATH.read_text()) if ICON_PATH.exists() else {}

# ---- fonts ---------------------------------------------------------------------
# Three pairings were rendered and compared (see SKILL.md section 8). The default is FONT_SET below.
#   display = hero numbers, big values, wordmark. text = labels and sentences. mono = small data labels.
FONT_SETS = {
    "condensed": dict(   # Barlow Condensed + Hanken Grotesk
        faces=[("SwDisplay", "BarlowCondensed-Medium.ttf", 500, None), ("SwDisplay", "BarlowCondensed-SemiBold.ttf", 600, None),
               ("SwDisplay", "BarlowCondensed-Bold.ttf", 700, None), ("SwText", "HankenGrotesk.ttf", "100 900", None)],
        disp="font-weight:600;font-stretch:100%", hero_weight=600, hero_ls="-0.01em", hero_size=1.0,
        text_ff="'SwText'", mono_ff="'SwText'", text_extra=""),
    "bricolage": dict(   # Bricolage Grotesque (condensed width) + Instrument Sans
        faces=[("SwDisplay", "BricolageGrotesque.ttf", "200 800", "75% 100%"), ("SwText", "InstrumentSans.ttf", "400 700", "75% 100%")],
        disp="font-weight:700;font-stretch:80%", hero_weight=700, hero_ls="-0.02em", hero_size=0.9,
        text_ff="'SwText'", mono_ff="'SwText'", text_extra=""),
    "archivo": dict(     # Archivo (extra condensed numerals, normal width text) + JetBrains Mono data labels
        faces=[("SwDisplay", "Archivo.ttf", "100 900", "62% 125%"), ("SwMono", "JetBrainsMono.ttf", "100 800", None)],
        disp="font-weight:800;font-stretch:68%", hero_weight=800, hero_ls="-0.03em", hero_size=1.0,
        text_ff="'SwDisplay'", mono_ff="'SwMono'", text_extra="font-stretch:100%;"),
}
FONT_SET = os.environ.get("GROKLIFE_FONTS") or os.environ.get("SWOLE_FONTS") or "condensed"


def font_set():
    return FONT_SETS[FONT_SET]


def font_css():
    fs = font_set()
    out = []
    for fam, fname, wt, st in fs["faces"]:
        b64 = base64.b64encode((FONT_DIR / fname).read_bytes()).decode()
        out.append(f"@font-face{{font-family:'{fam}';font-weight:{wt};{'font-stretch:' + st + ';' if st else ''}font-style:normal;"
                   f"src:url(data:font/ttf;base64,{b64}) format('truetype');}}")
    return "".join(out)


def base_css():
    fs = font_set()
    return f"""
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--hero-ls:{fs['hero_ls']};--hero-w:{fs['hero_weight']}}}
html,body{{background:{BG};color:{TEXT};color-scheme:{MODE};}}
body{{font-family:{fs['text_ff']},sans-serif;{fs['text_extra']}font-size:14px;line-height:20px;font-weight:500;
  -webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;position:relative;overflow:hidden}}
.t2{{color:{TEXT2}}} .t3{{color:{TEXT3}}}
.disp{{font-family:'SwDisplay',sans-serif;{fs['disp']};font-variant-numeric:tabular-nums;font-feature-settings:'tnum' 1,'lnum' 1;line-height:1}}
.hero{{font-family:'SwDisplay',sans-serif;font-stretch:{fs['disp'].split('font-stretch:')[1]};font-weight:var(--hero-w);letter-spacing:var(--hero-ls);
  font-variant-numeric:tabular-nums;font-feature-settings:'tnum' 1,'lnum' 1;line-height:1}}
.mono{{font-family:{fs['mono_ff']},sans-serif;font-variant-numeric:tabular-nums;font-feature-settings:'tnum' 1;font-stretch:100%}}
.lab{{font-size:14px;line-height:20px;font-weight:500;color:{TEXT2}}}
.sm{{font-size:12px;line-height:16px;font-weight:500;color:{TEXT3}}}
svg{{display:block;overflow:visible}}
svg text{{font-family:{fs['mono_ff']},sans-serif;font-variant-numeric:tabular-nums;font-stretch:100%}}
"""


BASE_CSS = None  # kept for callers that import it; use base_css()


def rgba(hex_color, a):
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def icon(name, size=16, color="currentColor", sw=2):
    """Inline Lucide icon (ISC license, bundled in icons/lucide.json)."""
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" '
            f'style="display:inline-block;vertical-align:middle;flex:none">{_ICONS.get(name, "")}</svg>')


def ring(size, stroke, frac, key, track_alpha=0.12):
    """Flat progress ring: solid arc, round caps, quiet track. A value over 100% fills the ring (the number says the rest)."""
    c = SOLID[key]
    r = size / 2 - stroke / 2
    circ = 2 * math.pi * r
    f = max(0.0, min(frac or 0, 1.0))
    arc = ""
    if f > 0.004:
        arc = (f'<circle cx="{size / 2}" cy="{size / 2}" r="{r:.2f}" fill="none" stroke="{c}" stroke-width="{stroke}" stroke-linecap="round" '
               f'stroke-dasharray="{circ * f:.2f} {circ:.2f}" transform="rotate(-90 {size / 2} {size / 2})"/>')
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"><circle cx="{size / 2}" cy="{size / 2}" r="{r:.2f}" fill="none" '
            f'stroke="{c}" stroke-opacity="{track_alpha}" stroke-width="{stroke}"/>{arc}</svg>')


def smooth_path(pts):
    """Monotone cubic (Fritsch-Carlson) through points [(x,y)...] as an SVG path string. No overshoot."""
    n = len(pts)
    if n == 0:
        return ""
    if n == 1:
        return f"M{pts[0][0]:.2f} {pts[0][1]:.2f}"
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    dx = [xs[i + 1] - xs[i] for i in range(n - 1)]
    dy = [ys[i + 1] - ys[i] for i in range(n - 1)]
    m = [dy[i] / dx[i] if dx[i] else 0 for i in range(n - 1)]
    t = [m[0]] + [0 if m[i - 1] * m[i] <= 0 else (m[i - 1] + m[i]) / 2 for i in range(1, n - 1)] + [m[-1]]
    for i in range(n - 1):
        if m[i] == 0:
            t[i] = t[i + 1] = 0
        else:
            a, b = t[i] / m[i], t[i + 1] / m[i]
            s = a * a + b * b
            if s > 9:
                k = 3 / math.sqrt(s)
                t[i], t[i + 1] = k * a * m[i], k * b * m[i]
    d = [f"M{xs[0]:.2f} {ys[0]:.2f}"]
    for i in range(n - 1):
        h = dx[i] / 3
        d.append(f"C{xs[i] + h:.2f} {ys[i] + t[i] * h:.2f} {xs[i + 1] - h:.2f} {ys[i + 1] - t[i + 1] * h:.2f} {xs[i + 1]:.2f} {ys[i + 1]:.2f}")
    return " ".join(d)


W, H45, SCALE = 480, 600, 2.25  # CSS px; x2.25 = 1080 px wide, 1350 px tall (4:5)


def page_html(body, extra_css="", width=W):
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{font_css()}{base_css()}"
            f"body{{width:{width}px}}{extra_css}</style></head><body>{body}</body></html>")


class Renderer:
    """Reusable headless Chromium. Use as a context manager."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._b = self._pw.chromium.launch()
        return self

    def __exit__(self, *a):
        self._b.close()
        self._pw.stop()

    def shot(self, html, out, width=W, min_height=H45, scale=SCALE, fmt=None, quality=92, fixed_height=None):
        """Render html to `out`. Height is the content height, at least min_height, or fixed_height."""
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        pg = self._b.new_page(viewport={"width": width, "height": fixed_height or min_height}, device_scale_factor=scale)
        pg.set_content(html, wait_until="load")
        pg.evaluate("document.fonts.ready")
        if fixed_height:
            h = fixed_height
        else:
            h = max(min_height, pg.evaluate("Math.ceil(document.documentElement.scrollHeight)"))
        over = pg.evaluate("(()=>{const e=document.querySelector('.pbody');return e?e.scrollHeight-e.clientHeight:0})()")
        if over and over > 1 and fixed_height is None:
            import sys
            print(f"warning: layout overflows by {over}px in {out.name}", file=sys.stderr)
        pg.set_viewport_size({"width": width, "height": h})
        kind = fmt or ("jpeg" if out.suffix.lower() in (".jpg", ".jpeg") else "png")
        kw = dict(path=str(out), type=kind, clip={"x": 0, "y": 0, "width": width, "height": h})
        if kind == "jpeg":
            kw["quality"] = quality
        pg.screenshot(**kw)
        pg.close()
        return out


def chromium_available():
    import os
    if os.environ.get("GROKLIFE_NO_CHROMIUM") or os.environ.get("SWOLE_NO_CHROMIUM"):  # force the fallbacks (used by tests)
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            b.close()
        return True
    except Exception:
        return False
