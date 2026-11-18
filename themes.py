"""Grok Life colour themes: palettes x light/dark, built in OKLCH so every hue sits at the same perceived lightness.

A palette is a set of rules (neutral tint, one lightness and chroma for the pillar hues, one hue per pillar). `tokens(palette, mode)`
resolves it to hex for one mode. The renderers read the result through render_core.set_theme(); the dashboard gets both modes as data.
Nothing here is personal data. Contrast figures are computed, not asserted: `python themes.py` prints them.
"""
import math

MODES = ("light", "dark")
PILLARS = ("recovery", "sleep", "nutrition", "hydration", "activity", "medication")


# ---- colour math ---------------------------------------------------------------------------------------------------
def _enc(v):
    v = max(0.0, min(1.0, v))
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def _dec(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _lin_rgb(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_, m_, s_ = L + 0.3963377774 * a + 0.2158037573 * b, L - 0.1055613458 * a - 0.0638541728 * b, L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def oklch(L, C, h):
    """OKLCH to #rrggbb. Chroma is reduced until the colour is inside sRGB, so lightness and hue are kept."""
    c = C
    while c > 0:
        r, g, b = _lin_rgb(L, c, h)
        if all(-0.001 <= v <= 1.001 for v in (r, g, b)):
            break
        c -= 0.002
    r, g, b = _lin_rgb(L, max(c, 0), h)
    return "#%02X%02X%02X" % tuple(round(_enc(v) * 255) for v in (r, g, b))


def _rgb(hexc):
    h = hexc.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def luminance(hexc):
    r, g, b = (_dec(v) for v in _rgb(hexc))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def to_oklab(hexc):
    r, g, b = (_dec(v) for v in _rgb(hexc))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def hue_of(hexc):
    """OKLCH hue angle of a hex colour, degrees 0-360."""
    _, a, b = to_oklab(hexc)
    return math.degrees(math.atan2(b, a)) % 360


def _deuteranopia(hexc):
    """Approximate red-green (deuteranopia) view of a colour (Machado et al. 2009, severity 1.0, applied in linear RGB)."""
    r, g, b = (_dec(v) for v in _rgb(hexc))
    m = ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881))
    out = [max(0.0, min(1.0, row[0] * r + row[1] * g + row[2] * b)) for row in m]
    return "#%02X%02X%02X" % tuple(round(_enc(v) * 255) for v in out)


def delta_e(a, b):
    """OKLab distance. Around 0.04 is a just-noticeable difference; 0.08 and up reads as clearly different."""
    la, lb = to_oklab(a), to_oklab(b)
    return math.dist(la, lb)


# ---- palettes ------------------------------------------------------------------------------------------------------
# Each palette: neutral hue and chroma (the tint of the grey), one lightness and chroma for the pillar hues in each mode,
# and one hue per pillar. Lightness is what keeps the hues equals: none shouts, none disappears.
PALETTES = {
    "lagoon": dict(
        label="Lagoon", tagline="Cool, mineral, clear",
        why="Teal-tinted neutrals and a green that leans blue read as clean and clinical without looking like a hospital. "
            "Six hues sit 40 to 55 degrees apart at one lightness, so none shouts and each pillar reads at a glance. "
            "Medication is leaf green, not pink or purple. Dark mode is deep teal, not black.",
        neutral=dict(hue=205, c_light=0.005, c_dark=0.030),
        light=dict(bg=0.978, surface=0.948, text=0.22, text2=0.44, text3=0.50, L=0.60, C=0.125),
        dark=dict(bg=0.245, surface=0.295, text=0.97, text2=0.80, text3=0.69, L=0.80, C=0.125),
        hues=dict(recovery=172, sleep=258, nutrition=78, hydration=218, activity=30, medication=132),
        adj=dict(medication=(0.02, 0.03), nutrition=(0.0, 0.01))),
    "meadow": dict(
        label="Meadow", tagline="Soft, organic, grounded",
        why="Green-grey neutrals with lower-chroma earth tones: sage, ochre, terracotta, dusty blue. Gentlest on the eye, "
            "but the earth hues sit close together, so the pillars separate less and the page reads flatter.",
        neutral=dict(hue=145, c_light=0.008, c_dark=0.030),
        light=dict(bg=0.975, surface=0.945, text=0.23, text2=0.44, text3=0.50, L=0.58, C=0.10),
        dark=dict(bg=0.25, surface=0.30, text=0.965, text2=0.80, text3=0.69, L=0.78, C=0.10),
        hues=dict(recovery=150, sleep=240, nutrition=82, hydration=195, activity=42, medication=118),
        adj=dict(medication=(0.02, 0.03))),
    "harbor": dict(
        label="Harbor", tagline="Crisp, confident, blue-led",
        why="Slate-blue neutrals and a blue lead hue, the most familiar colour for health and trust. "
            "It is also the closest to what other health apps already use, so it feels the least distinct.",
        neutral=dict(hue=262, c_light=0.008, c_dark=0.040),
        light=dict(bg=0.978, surface=0.950, text=0.22, text2=0.44, text3=0.50, L=0.58, C=0.14),
        dark=dict(bg=0.25, surface=0.30, text=0.97, text2=0.80, text3=0.69, L=0.78, C=0.14),
        hues=dict(recovery=252, sleep=205, nutrition=82, hydration=170, activity=28, medication=130),
        adj=dict(medication=(0.02, 0.03))),
}
DEFAULT_PALETTE = "lagoon"


def tokens(palette=None, mode="light"):
    """Resolve a palette and mode to flat hex tokens. Keys: bg, surface, text, text2, text3, hair, track, onAccent, hues{...}."""
    p = PALETTES[palette or DEFAULT_PALETTE]
    m = p[mode]
    nh = p["neutral"]["hue"]
    nc = p["neutral"]["c_light" if mode == "light" else "c_dark"]
    t = dict(
        mode=mode, palette=palette or DEFAULT_PALETTE,
        bg=oklch(m["bg"], nc, nh), surface=oklch(m["surface"], nc, nh),
        text=oklch(m["text"], nc * 1.2, nh), text2=oklch(m["text2"], nc * 1.2, nh), text3=oklch(m["text3"], nc * 1.2, nh),
        hues={k: oklch(m["L"] + p.get("adj", {}).get(k, (0, 0))[0], m["C"] + p.get("adj", {}).get(k, (0, 0))[1], h) for k, h in p["hues"].items()})
    ink = _rgb(t["text"])
    t["hair"] = "rgba(%d,%d,%d,0.11)" % tuple(round(v * 255) for v in ink)
    t["track"] = "rgba(%d,%d,%d,0.07)" % tuple(round(v * 255) for v in ink)
    t["onAccent"] = oklch(0.20, nc, nh) if mode == "dark" else oklch(0.99, 0.004, nh)
    return t


def report(palette):
    """Computed accessibility figures for one palette, both modes."""
    out = {}
    for mode in MODES:
        t = tokens(palette, mode)
        hv = t["hues"]
        names = list(hv)
        pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
        out[mode] = dict(
            text=round(contrast(t["text"], t["bg"]), 1), text2=round(contrast(t["text2"], t["bg"]), 1),
            text3=round(contrast(t["text3"], t["bg"]), 1),
            hue_min=round(min(contrast(h, t["bg"]) for h in hv.values()), 1),
            sep=round(min(delta_e(hv[a], hv[b]) for a, b in pairs), 3),
            sep_deut=round(min(delta_e(_deuteranopia(hv[a]), _deuteranopia(hv[b])) for a, b in pairs), 3))
    return out


if __name__ == "__main__":
    for k in PALETTES:
        print(k, report(k))
        for mode in MODES:
            print("  ", mode, tokens(k, mode))
