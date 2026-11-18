"""Generate clearly-placeholder studio-lit silhouette photos for testing the comparison layout.
  python make_sample_photos.py OUT_DIR   -> before_front.jpg, after_front.jpg, before_side.jpg, after_side.jpg
These are renders, not people. A small PLACEHOLDER tag is drawn in each corner.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, S = 1200, 1600, 2  # output size, supersample


def _font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",):
        if Path(p).exists():
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default(sz)


def figure_mask(view, sw, ww, hw):
    m = Image.new("L", (W * S, H * S), 0)
    d = ImageDraw.Draw(m)
    s = lambda v: v * S
    cx = 600
    if view == "front":
        d.ellipse([s(cx - 76), s(240), s(cx + 76), s(440)], fill=255)  # head
        d.rectangle([s(cx - 42), s(420), s(cx + 42), s(500)], fill=255)  # neck
        torso = [(cx - sw * .55, 505), (cx - sw, 540), (cx - sw + 8, 660), (cx - ww, 880), (cx - hw, 1010),
                 (cx + hw, 1010), (cx + ww, 880), (cx + sw - 8, 660), (cx + sw, 540), (cx + sw * .55, 505)]
        d.polygon([(s(x), s(y)) for x, y in torso], fill=255)
        for sgn in (-1, 1):
            d.line([(s(cx + sgn * (sw - 8)), s(560)), (s(cx + sgn * (ww + 95)), s(980))], fill=255, width=s(60))
            for x, y, r in ((cx + sgn * (sw - 8), 560, 36), (cx + sgn * (ww + 95), 980, 27)):
                d.ellipse([s(x - r), s(y - r), s(x + r), s(y + r)], fill=255)
            d.line([(s(cx + sgn * (hw * .52)), s(1000)), (s(cx + sgn * 62), s(1490))], fill=255, width=s(int(hw * .72)))
            d.ellipse([s(cx + sgn * 62 - 34), s(1480), s(cx + sgn * 62 + 34), s(1530)], fill=255)
    else:  # side: narrower depth, gentle S-curve
        d.ellipse([s(cx - 82 + 10), s(240), s(cx + 82 + 10), s(440)], fill=255)
        d.rectangle([s(cx - 46), s(400), s(cx + 56), s(530)], fill=255)
        depth = lambda w_: w_ * .55
        torso = [(cx - depth(sw) * .8, 520), (cx + depth(sw) * .9, 540), (cx + depth(ww) + 18, 760),
                 (cx + depth(ww) + 10, 880), (cx + depth(hw) + 30, 1010), (cx - depth(hw) - 36, 1010),
                 (cx - depth(ww) - 22, 880), (cx - depth(sw) * .8 - 10, 640)]
        d.polygon([(s(x), s(y)) for x, y in torso], fill=255)
        d.line([(s(cx + 4), s(570)), (s(cx + 28), s(940))], fill=255, width=s(54))
        d.line([(s(cx - 4), s(1000)), (s(cx + 6), s(1490))], fill=255, width=s(int(hw * .6)))
        d.ellipse([s(cx - 40), s(1478), s(cx + 120), s(1530)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(S * 17)).point(lambda v: 255 if v > 120 else 0)  # round the joins
    return m.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))


def render(view, sw, ww, hw, tint, seed):
    """Cinematic studio placeholder: teal-slate backdrop with bokeh, a soft-focus figure, warm rim light from the left."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - 700) / 760, (yy - 620) / 1000)
    t = np.clip(r, 0, 1.4)[..., None]
    c_in, c_out = np.array([92, 104, 126], np.float32), np.array([20, 24, 32], np.float32)
    base = c_in * np.exp(-t ** 2 * 1.5) + c_out * (1 - np.exp(-t ** 2 * 1.5))
    base *= np.array(tint, np.float32)
    # bokeh discs
    bk = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(bk)
    for _ in range(26):
        x, y, rad = int(rng.uniform(0, W)), int(rng.uniform(0, H * 0.85)), int(rng.uniform(26, 78))
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=int(rng.uniform(14, 40)))
    bk = np.asarray(bk.filter(ImageFilter.GaussianBlur(16)), dtype=np.float32)[..., None] / 255
    base = base + bk * np.array([150, 170, 200], np.float32)
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse([240, 1490, 960, 1580], fill=230)
    sh = np.asarray(sh.filter(ImageFilter.GaussianBlur(36)), dtype=np.float32) / 255
    base *= (1 - 0.6 * sh)[..., None]
    mask = figure_mask(view, sw, ww, hw).filter(ImageFilter.GaussianBlur(3.5))
    m = np.asarray(mask, dtype=np.float32) / 255
    soft = np.asarray(mask.filter(ImageFilter.GaussianBlur(40)), dtype=np.float32) / 255
    edge = np.clip(m - np.asarray(mask.filter(ImageFilter.GaussianBlur(14)), dtype=np.float32) / 255, 0, 1) * 1.9
    left = np.clip((640 - xx) / 330, 0, 1) ** 1.6 + 0.06  # key light from the left only
    body = np.stack([14 + soft * 34 + edge * 255 * left, 17 + soft * 38 + edge * 196 * left, 24 + soft * 48 + edge * 150 * left], -1)
    out = base * (1 - m[..., None]) + body * m[..., None]
    out *= 1 - 0.28 * np.clip(np.hypot((xx - 600) / 700, (yy - 800) / 1000) - 0.7, 0, 1)[..., None]
    out += rng.normal(0, 1.4, out.shape)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    ImageDraw.Draw(img).text((W // 2 + 10, 860), "PLACEHOLDER", font=_font(30), fill=(150, 160, 182), anchor="mm")
    return img


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    specs = {"before_front": ("front", 238, 168, 206, (1.0, 1.0, 1.02), 1), "after_front": ("front", 242, 148, 198, (0.98, 1.0, 1.04), 2),
             "before_side": ("side", 238, 176, 206, (1.0, 1.0, 1.02), 3), "after_side": ("side", 242, 150, 198, (0.98, 1.0, 1.04), 4)}
    for name, (v, sw, ww, hw, tint, seed) in specs.items():
        render(v, sw, ww, hw, tint, seed).save(out / f"{name}.jpg", quality=92)
        print(out / f"{name}.jpg")
