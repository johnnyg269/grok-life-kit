#!/usr/bin/env python3
"""Grok Life progress photos: save, log, and stitch side-by-side comparisons.

Folder layout (under the data dir, default /workspace/macro-coach):
  photos/<pose>/YYYY-MM-DD.jpg          one photo per pose per day (pose: front|side|back)
  photos.csv                            date,pose,path,weight_kg   (path is relative to the data dir)
  photos/comparisons/<pose>/prev_<d1>_to_<d2>.jpg    previous photo vs new one
  photos/comparisons/<pose>/first_<d1>_to_<d2>.jpg   all-time first vs latest

Commands:
  add     --src FILE --pose front [--date YYYY-MM-DD] [--weight-kg 82.4]
          Saves the photo, logs it, and builds previous-vs-new automatically.
  compare --pose front              Rebuild previous-vs-latest for a pose.
  alltime [--pose front|side|back]  First-vs-latest for one pose, or all poses that have 2+ photos.
Options: --data DIR  --units auto|imperial|metric (label units only; storage is always kg)
         --theme light|dark (default: the saved preference in config.json)
         --theme light|dark (default: the saved preference in config.json)

Exit code 2 with "POSE_NEEDED" means the pose is missing or unclear: ask the user
"front, side, or back?" and rerun. Prints one output path per line.
"""
import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image, ImageDraw, ImageFont, ImageOps

POSES = ("front", "side", "back")
DEFAULT_DATA = Path("/workspace/macro-coach")
FIELDS = ["date", "pose", "path", "weight_kg"]
BG, INK, MUTED, TEAL, BLUE, RED, GREEN = "#FFFFFF", "#111827", "#6B7280", "#0F766E", "#2563EB", "#DC2626", "#16A34A"
PHOTO_H, MAX_W, PAD = 1200, 1600, 40


def font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    dirs = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/Library/Fonts",
            "/System/Library/Fonts/Supplemental", "C:/Windows/Fonts"]
    try:
        import matplotlib
        dirs.append(str(Path(matplotlib.get_data_path()) / "fonts" / "ttf"))
    except ImportError:
        pass
    for d in dirs:
        for n in names + (["Arial Bold.ttf", "arialbd.ttf"] if bold else ["Arial.ttf", "arial.ttf"]):
            p = Path(d) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def read_log(root):
    p = root / "photos.csv"
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_log(root, rows):
    rows = sorted(rows, key=lambda r: (r["date"], r["pose"]))
    with open(root / "photos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in FIELDS} for r in rows)


def need_pose(pose):
    if pose is None or pose.strip().lower() not in POSES:
        print(f"POSE_NEEDED: pose must be one of {', '.join(POSES)} (got {pose!r}). Ask the user.", file=sys.stderr)
        sys.exit(2)
    return pose.strip().lower()


def weight_on(root, day):
    """Latest weigh-in on or before `day` within 7 days, from weight.csv (kg), else ''."""
    p = root / "weight.csv"
    if not p.exists():
        return ""
    best = None
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d = dt.date.fromisoformat(r["date"][:10])
                w = float(r["weight_kg"])
            except (ValueError, KeyError, TypeError):
                continue
            if d <= day and (day - d).days <= 7 and (best is None or d >= best[0]):
                best = (d, w)
    return f"{best[1]:.1f}" if best else ""


def wunits(root, arg):
    if arg in ("imperial", "metric"):
        return arg == "imperial"
    p = root / "targets.csv"
    if p.exists():
        with open(p, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            return (rows[-1].get("units") or "imperial").strip().lower() != "metric"
    return True


def add_photo(root, src, pose, day, weight_kg):
    pose = need_pose(pose)
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    img.thumbnail((2400, 2400))  # keep files phone-friendly
    rel = f"photos/{pose}/{day.isoformat()}.jpg"
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=90)
    w = f"{weight_kg:.1f}" if weight_kg else weight_on(root, day)
    rows = [r for r in read_log(root) if not (r["date"] == day.isoformat() and r["pose"] == pose)]
    rows.append(dict(date=day.isoformat(), pose=pose, path=rel, weight_kg=w))
    write_log(root, rows)
    return dest


def pose_rows(root, pose):
    rows = [r for r in read_log(root) if r["pose"] == pose and (root / r["path"]).exists()]
    return sorted(rows, key=lambda r: r["date"])


def stitch_pillow(root, a, b, kind, imperial):
    """Fallback when Chromium is unavailable. a = earlier row, b = later row. Returns output path."""
    da, db = dt.date.fromisoformat(a["date"]), dt.date.fromisoformat(b["date"])
    ia, ib = (Image.open(root / r["path"]).convert("RGB") for r in (a, b))
    h = PHOTO_H
    wa, wb = round(ia.width * h / ia.height), round(ib.width * h / ib.height)
    if wa + wb + 3 * PAD > MAX_W:  # keep the whole image phone-readable
        k = (MAX_W - 3 * PAD) / (wa + wb)
        h, wa, wb = round(h * k), round(wa * k), round(wb * k)
    ia, ib = ia.resize((wa, h), Image.LANCZOS), ib.resize((wb, h), Image.LANCZOS)
    W = wa + wb + 3 * PAD
    top, foot = 230, 210
    canvas = Image.new("RGB", (W, top + h + foot), BG)
    d = ImageDraw.Draw(canvas)
    pose = a["pose"].capitalize()
    title = "First vs latest" if kind == "first" else "Progress"
    d.text((PAD, 34), f"{title} \u2022 {pose}", font=font(54, True), fill=INK)
    xa, xb = PAD, 2 * PAD + wa
    for x, r, dd, lab, col in ((xa, a, da, "BEFORE", MUTED), (xb, b, db, "AFTER", BLUE)):
        d.text((x, 124), lab, font=font(30, True), fill=col)
        d.text((x, 164), dd.strftime("%b %-d, %Y"), font=font(40, True), fill=INK)
    canvas.paste(ia, (xa, top))
    canvas.paste(ib, (xb, top))
    days = (db - da).days
    unit = "lb" if imperial else "kg"
    wa_, wb_ = (float(r["weight_kg"]) if r.get("weight_kg") else None for r in (a, b))
    if wa_ is not None and wb_ is not None:
        diff = (wb_ - wa_) * (2.20462 if imperial else 1)
        wtxt = f"{diff:+.1f} {unit}"
        sub = "  ".join(f"{(x * (2.20462 if imperial else 1)):.1f} {unit}" for x in (wa_, wb_))
        sub = f"{sub.split('  ')[0]}  \u2192  {sub.split('  ')[1]}"
        wcol = TEAL
    else:
        wtxt, sub, wcol = "weight n/a", "log a weigh-in on photo day to see the change", MUTED
    y = top + h + 30
    d.text((PAD, y), f"{days} day{'s' if days != 1 else ''}", font=font(64, True), fill=INK)
    wf = font(64, True)
    tw = d.textlength(wtxt, font=wf)
    d.text((W - PAD - tw, y), wtxt, font=wf, fill=wcol)
    sf = font(32)
    d.text((PAD, y + 92), "between photos", font=sf, fill=MUTED)
    d.text((W - PAD - d.textlength(sub, font=sf), y + 92), sub, font=sf, fill=MUTED)
    out_dir = root / "photos" / "comparisons" / a["pose"]
    out_dir.mkdir(parents=True, exist_ok=True)
    if kind == "first":
        for old in out_dir.glob("first_*.jpg"):
            old.unlink()
    out = out_dir / f"{'first' if kind == 'first' else 'prev'}_{a['date']}_to_{b['date']}.jpg"
    canvas.save(out, "JPEG", quality=90)
    return out


def goal_type(root):
    p = root / "targets.csv"
    if p.exists():
        with open(p, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            return (rows[-1].get("goal_type") or "").strip().lower()
    return ""


def _data_uri(path, max_h=1100):
    import base64
    import io
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if im.height > max_h:
        im = im.resize((round(im.width * max_h / im.height), max_h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def comparison_html(a, b, uri_a, uri_b, kind, imperial, gtype, streak_n=0):
    """1080x1080 side-by-side comparison on a 480 CSS px square (rendered at 2.25x), same frame as the other images.

    One hero line (the weight change and the day count), two photo frames, solid date chips. No glass, no gradients.
    """
    import render as R
    import render_core as rc
    da, db = dt.date.fromisoformat(a["date"]), dt.date.fromisoformat(b["date"])
    days = (db - da).days
    unit = "lb" if imperial else "kg"
    k = 2.20462 if imperial else 1
    wa = float(a["weight_kg"]) * k if a.get("weight_kg") else None
    wb = float(b["weight_kg"]) * k if b.get("weight_kg") else None
    span = f'in {days} day{"s" if days != 1 else ""}'
    if wa is not None and wb is not None:
        diff = wb - wa
        good = (gtype == "lose" and diff < 0) or (gtype == "gain" and diff > 0)
        col = rc.GOOD if good else rc.TEXT
        hero = (f'<span class="hero" style="font-size:48px;line-height:40px;color:{col}">{R.sgn(diff)}</span>'
                f'<span class="disp" style="font-size:24px;color:{rc.TEXT2};font-weight:600;margin-left:4px">{unit}</span>'
                f'<span class="lab" style="margin-left:8px">{span}</span>')
    else:
        hero = f'<span class="lab">Weight not logged \u00b7 {span}</span>'

    def frame_one(uri, row, label, accent):
        d = dt.date.fromisoformat(row["date"])
        w = (f'<span class="disp" style="font-size:16px;color:{rc.TEXT2};margin-left:8px">{float(row["weight_kg"]) * k:.1f} {unit}</span>') if row.get("weight_kg") else ""
        return (f'<div style="position:relative;flex:1;border-radius:{rc.RADIUS}px;overflow:hidden;background:{rc.SURFACE}">'
                f'<img src="{uri}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 38%">'
                f'<div style="position:absolute;left:8px;bottom:8px;padding:8px 12px;border-radius:8px;background:{rc.rgba(rc.BG, .92)}">'
                f'<div style="font-size:12px;line-height:16px;font-weight:600;color:{accent}">{label}</div>'
                f'<div style="display:flex;align-items:baseline;margin-top:4px"><span class="disp" style="font-size:22px">{d.strftime("%b %-d")}</span>'
                f'<span class="sm" style="margin-left:4px">{d.year}</span></div>{("<div style=margin-top:4px;line-height:16px>" + w.replace("margin-left:8px", "margin-left:0") + "</div>") if w else ""}</div></div>')

    body = (f'<div style="display:flex;align-items:baseline;height:40px;flex:none;white-space:nowrap">{hero}</div>'
            f'<div style="flex:1;display:flex;gap:{rc.SP["s"]}px;margin-top:{rc.SP["m"]}px;min-height:0">{frame_one(uri_a, a, "Before", rc.TEXT2)}'
            f'{frame_one(uri_b, b, "After", rc.GOOD)}</div>')
    label = "First vs latest" if kind == "first" else "Progress"
    html = R.frame(body, f'{a["pose"].capitalize()} view', streak_n, f'{label} \u00b7 {db.strftime("%b %-d")}', height=480)
    return rc.page_html(html, width=480)


def stitch(root, a, b, kind, imperial):
    """Premium comparison (Chromium). Falls back to the Pillow layout when Chromium is unavailable."""
    try:
        import os
        if os.environ.get("GROKLIFE_NO_CHROMIUM") or os.environ.get("SWOLE_NO_CHROMIUM"):
            raise RuntimeError("Chromium disabled")
        import render_core as rc
        try:
            import charts as _C
            from dashboard_data import streak as _streak
            sn = _streak(_C.Data(root), dt.date.fromisoformat(b["date"]))
        except Exception:
            sn = 0
        html = comparison_html(a, b, _data_uri(root / a["path"]), _data_uri(root / b["path"]), kind, imperial, goal_type(root), sn)
        out_dir = root / "photos" / "comparisons" / a["pose"]
        out_dir.mkdir(parents=True, exist_ok=True)
        if kind == "first":
            for old in out_dir.glob("first_*.jpg"):
                old.unlink()
        out = out_dir / f"{'first' if kind == 'first' else 'prev'}_{a['date']}_to_{b['date']}.jpg"
        with rc.Renderer() as r:
            r.shot(html, out, width=480, scale=2.25, fixed_height=480, fmt="jpeg", quality=93)
        return out
    except Exception as e:  # Chromium or Playwright missing
        print(f"warning: Chromium render failed ({e.__class__.__name__}), using the Pillow layout", file=sys.stderr)
        return stitch_pillow(root, a, b, kind, imperial)


def compare_prev(root, pose, imperial):
    rows = pose_rows(root, pose)
    if len(rows) < 2:
        return None
    return stitch(root, rows[-2], rows[-1], "prev", imperial)


def compare_first(root, pose, imperial):
    rows = pose_rows(root, pose)
    if len(rows) < 2:
        return None
    return stitch(root, rows[0], rows[-1], "first", imperial)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["add", "compare", "alltime"])
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--src")
    ap.add_argument("--pose")
    ap.add_argument("--date")
    ap.add_argument("--weight-kg", type=float)
    ap.add_argument("--units", default="auto", choices=["auto", "imperial", "metric"])
    ap.add_argument("--theme", default=None, choices=["light", "dark"], help="default: the saved preference in config.json")
    a = ap.parse_args()
    root = Path(a.data)
    root.mkdir(parents=True, exist_ok=True)
    try:
        import config as CFG
        import render_core as rc
        rc.set_theme(CFG.resolve_theme(root, a.theme), CFG.load(root).get("palette"))
    except Exception:  # the Pillow fallback has its own colours
        pass
    imp = wunits(root, a.units)
    outs = []
    if a.cmd == "add":
        pose = need_pose(a.pose)
        if not a.src or not Path(a.src).exists():
            sys.exit("--src must be an existing image file")
        day = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
        outs.append(add_photo(root, a.src, pose, day, a.weight_kg))
        out = compare_prev(root, pose, imp)
        if out:
            outs.append(out)
        else:
            print(f"first {pose} photo saved; comparison starts with the next one", file=sys.stderr)
    elif a.cmd == "compare":
        out = compare_prev(root, need_pose(a.pose), imp)
        if out:
            outs.append(out)
        else:
            print("need at least two photos in this pose", file=sys.stderr)
    else:
        for pose in ([need_pose(a.pose)] if a.pose else POSES):
            out = compare_first(root, pose, imp)
            if out:
                outs.append(out)
    for o in outs:
        print(o)


if __name__ == "__main__":
    main()
