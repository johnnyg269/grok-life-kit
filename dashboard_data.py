#!/usr/bin/env python3
"""Build the data blocks for the Grok Life dashboard canvas from the CSVs.

  python dashboard_data.py full   --name Alex   # print the complete canvas source (for WriteCanvas at onboarding)
  python dashboard_data.py update --name Alex   # write dashboard/*.new.txt blocks and print the paths
  python dashboard_data.py commit               # after a successful EditCanvas, promote .new -> .live

Reads DATA/config.json: modules that are off, or on with no data yet, are null in DATA and the canvas never draws them
(no tab, no tile, no empty card). Re-enabling a module and running `update` brings it back. The palette comes from the same config.

Files live in DATA/dashboard/: data_block.live.txt and photo_block.live.txt hold exactly what the canvas
currently contains, so an update is EditCanvas(old_string=<live block>, new_string=<new block>).
Options: --data DIR  --date YYYY-MM-DD  --units auto|imperial|metric
"""
import argparse
import base64
import datetime as dt
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charts import DEFAULT_DATA, Data, pick_units, rolling_weight, num, pdate  # noqa: E402
from compare_photos import read_log  # noqa: E402

TEMPLATE = Path(__file__).parent / "dashboard.canvas.tsx.template"
THUMB_MAX_BYTES = 45_000


def logged_day(data, d, t):
    return data.food.get(d, {}).get("cal", 0) >= 0.6 * t["calories"]


def streak(data, day):
    t = data.target(day)
    d = day if logged_day(data, day, t) else day - dt.timedelta(1)  # today can still be logged
    n = 0
    while logged_day(data, d, data.target(d)):
        n += 1
        d -= dt.timedelta(1)
    return n


def thumb(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    for width in (640, 560, 480, 400):
        im2 = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        for q in (70, 60, 50, 40):
            buf = io.BytesIO()
            im2.save(buf, "JPEG", quality=q, optimize=True)
            if buf.tell() <= THUMB_MAX_BYTES:
                return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return None


def build_treatment(root, data, day, u):
    """Medication block for the dashboard, or None when no doses are logged."""
    import meds as M
    import render_meds as RM
    if not (Path(root) / "meds.csv").exists():
        return None
    now = RM.default_now(day)
    st = M.status(Path(root), now, None)
    if not st or not st.get("last"):
        return None
    t0, t1, past, futs, extra = RM.curve(st, 30, now, points=90)
    span = (t1 - t0).total_seconds()
    fx = lambda t: round((t - t0).total_seconds() / span, 4)  # noqa: E731
    pts = lambda xs: [[fx(t), round(v, 3)] for t, v in xs]  # noqa: E731
    ticks = []
    for i in range(0, 31, 10):
        t = t0 + dt.timedelta(days=i)
        ticks.append([fx(t), t.strftime("%b %-d")])
    eff = M.effects_summary(Path(root), now)
    effects = []
    for e in eff:
        v, sub = e["latest"], ""
        if e["avg"] is not None and e["prev"] is not None and abs(e["avg"] - e["prev"]) >= 0.5:
            sub = "rising" if e["avg"] > e["prev"] else "easing"
        effects.append(dict(key=e["key"], label=e["label"], value=v or 0, target=10,
                            shown=f"{v:.0f}/10" if v is not None else "\u2013", sub=sub))
    return dict(
        compound=st["label"], brand=st.get("brand") or "", cadence=RM.cadence(st["interval_days"]) if st["scheduled"] else "", scheduled=st["scheduled"],
        levelNow=round(st["level_now"], 2), levelNext=round(st["level_next"], 2),
        ssHigh=round(st["ss_peak"], 1), ssLow=round(st["ss_trough"], 1),
        lastMg=f"{st['last']['mg']:g} mg", lastWhen=RM.fmt_when(st["last"]["t"], now),
        lastSite=st["last"]["site_label"], nextSite=st["next_site_label"],
        nextCountdown=st["next"]["countdown"] if st["scheduled"] else "\u2013", nextWhen=RM.fmt_when(st["next"]["t"], now) if st["scheduled"] else "not set yet",
        elapsed=round(st["next"]["elapsed"], 3), lastSiteKey=st["last"]["site"], nextSiteKey=st["next_site"],
        past=pts(past), future=pts(futs), doseX=[fx(d["t"]) for d in st["doses"] if t0 <= d["t"] <= now] + [fx(d["t"]) for d in extra],
        nowX=fx(now), ticks=ticks, effects=effects, coach=M.treatment_line(st, eff, data, now) or "")


def build_photo(root, u):
    photo = None
    rows = read_log(root)
    poses = {}
    for r in rows:
        poses.setdefault(r["pose"], []).append(r)
    best = None
    for pose, rs in poses.items():
        rs = sorted(rs, key=lambda r: r["date"])
        if len(rs) >= 2 and (best is None or rs[-1]["date"] > best[1][-1]["date"]):
            best = (pose, rs)
    if best:
        pose, rs = best
        comps = sorted((Path(root) / "photos" / "comparisons" / pose).glob(f"prev_*_to_{rs[-1]['date']}.jpg"))
        src = thumb(comps[-1]) if comps else None
        if src:
            a, b = rs[-2], rs[-1]
            wa, wb = num(a.get("weight_kg")), num(b.get("weight_kg"))
            wtxt = f"{u.wt(wb) - u.wt(wa):+.1f} {u.w}" if wa and wb else "not logged"
            photo = dict(src=src, pose=pose, before=pdate(a["date"]).strftime("%b %-d, %Y"),
                         after=pdate(b["date"]).strftime("%b %-d, %Y"),
                         days=(pdate(b["date"]) - pdate(a["date"])).days, weight=wtxt)
    return photo


def series(days, getter, ndigits=0):
    return [None if (v := getter(d)) is None else round(v, ndigits) for d in days]


def build(root, day, name, units_arg):
    """Returns (dash, photo). Modules that are off, or have no data yet, come back as None and are never drawn."""
    import config as CFG
    import scoring as S
    import themes as T
    root = Path(root)
    cfg = CFG.load(root)
    data = Data(root)
    data.off = {k for k in CFG.ORDER if not cfg["modules"].get(k)}
    shown = CFG.visible(root)
    u = pick_units(data, units_arg, day)
    t = data.target(day)
    f = data.food.get(day, dict(cal=0, p=0, c=0, f=0, fib=0, n=0, meals={}))
    water_ml = data.water.get(day, 0)
    steps = data.steps.get(day, 0)
    days7 = [day - dt.timedelta(i) for i in range(6, -1, -1)]
    lab7 = [d.strftime("%a") for d in days7]

    def water(ml):
        return ml / 29.5735 if u.imp else ml / 1000

    wunit = "oz" if u.imp else "L"
    wfmt = (lambda v: f"{v:,.0f}") if u.imp else (lambda v: f"{v:.1f}")
    pal = {m: T.tokens(cfg.get("palette") or T.DEFAULT_PALETTE, m)["hues"] for m in T.MODES}
    pal = {m: [h[k] for k in ("recovery", "sleep", "nutrition", "hydration", "activity", "medication")] for m, h in pal.items()}
    mods = {k: None for k in CFG.ORDER}

    if "workouts" in shown:
        ses = [(d, x) for d in days7 for x in data.workout_sessions(d)]
        mins = lambda d: sum(num(x.get("duration_min"), 0) for x in data.workout_sessions(d))  # noqa: E731
        total = round(sum(num(x.get("duration_min"), 0) for _, x in ses))
        wk = [day - dt.timedelta(7 * i) for i in range(7, -1, -1)]
        weeks = [round(sum(mins(e - dt.timedelta(j)) for j in range(7))) for e in wk]
        recent = []
        for d in sorted(data.workouts, reverse=True):
            for x in data.workout_sessions(d):
                recent.append(dict(when=d.strftime("%b %-d"), name=(x.get("name") or x.get("type") or "Workout").strip(),
                                   mins=round(num(x.get("duration_min"), 0)), kcal=round(num(x.get("est_kcal"), 0))))
            if len(recent) >= 6:
                break
        ld, lx = ses[-1] if ses else (None, None)
        mods["workouts"] = dict(
            sessions=len(ses), planned=int(t["sessions_per_week"]), minutes=total,
            kcal=round(sum(num(x.get("est_kcal"), 0) for _, x in ses)), avg=round(total / len(ses)) if ses else 0,
            last=f"Last: {(lx.get('name') or lx.get('type') or 'Workout').strip()}, {ld.strftime('%a')}" if ld else "",
            days=[dict(label=d.strftime("%a")[:1], done=bool(data.workout_sessions(d)), mins=round(mins(d))) for d in days7],
            weeks=dict(labels=[d.strftime("%b %-d") for d in wk], values=weeks), recent=recent[:6])

    if "nutrition" in shown:
        rings = [
            dict(key="calories", label="Calories", value=round(f["cal"]), target=round(t["calories"]),
                 shown=f"{f['cal']:,.0f}", sub=f"of {t['calories']:,.0f}"),
            dict(key="protein", label="Protein", value=round(f["p"]), target=round(t["protein_g"]),
                 shown=f"{f['p']:,.0f} g", sub=f"of {t['protein_g']:,.0f} g"),
            dict(key="carbs", label="Carbs", value=round(f["c"]), target=round(t["carbs_g"]),
                 shown=f"{f['c']:,.0f} g", sub=f"of {t['carbs_g']:,.0f} g"),
            dict(key="fat", label="Fat", value=round(f["f"]), target=round(t["fat_g"]),
                 shown=f"{f['f']:,.0f} g", sub=f"of {t['fat_g']:,.0f} g")]
        logged = [d for d in days7 if S.logged(data, d)]  # same rule as the PNG: a day counts once it holds 30% of the calorie target
        avg = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
        ac, ap = avg([data.food[d]["cal"] for d in logged]), avg([data.food[d]["p"] for d in logged])
        hit = sum(1 for d in logged if data.food[d]["p"] >= 0.9 * t["protein_g"])
        mods["nutrition"] = dict(
            kcalLeft=round(t["calories"] - f["cal"]), rings=rings,
            meals=[dict(label=k.capitalize(), value=round(v)) for k, v in f["meals"].items()],
            cal7=dict(labels=lab7, values=[round(data.food[d]["cal"]) if d in data.food else 0 for d in days7], target=round(t["calories"])),
            avgIntake=f"{ac:,.0f}" if ac else "\u2013", avgProtein=f"{ap:,.0f} g" if ap else "\u2013", proteinDays=f"{hit}/{len(logged)}")

    if "activity" in shown:
        d30 = [day - dt.timedelta(i) for i in range(29, -1, -1)]
        got = [data.steps[d] for d in d30 if d in data.steps]
        goal = t["step_goal"]
        mods["activity"] = dict(
            steps=round(steps), goal=round(goal), pct=round(100 * steps / goal) if goal else 0,
            week=dict(labels=lab7, values=[round(data.steps.get(d, 0)) for d in days7]),
            avg30=f"{sum(got) / len(got):,.0f}" if got else "\u2013",
            goalDays=f"{sum(1 for v in got if goal and v >= goal)}/{len(got)}", best=f"{max(got):,.0f}" if got else "\u2013")

    if "health" in shown:
        sc = S.pillars(data, day)
        rec = dict(value=sc["recovery"], state=S.state_word(sc["recovery"]), coach=S.coach_line(data, day, "daily", u))
        days28 = [day - dt.timedelta(i) for i in range(27, -1, -1)]
        avg = rolling_weight(data.weight, days28)
        weight = None
        if any(d in data.weight for d in days28) and avg:
            first, last = min(avg), max(avg)
            weight = dict(
                unit=u.w, labels=[d.strftime("%b %-d") for d in days28],
                daily=[round(u.wt(data.weight[d]), 1) if d in data.weight else None for d in days28],
                avg=[round(u.wt(avg[d]), 2) if d in avg else None for d in days28],
                goal=round(u.wt(t["goal_weight_kg"]), 1) if t["goal_weight_kg"] else None,
                current=round(u.wt(avg[last]), 1),
                change=round(u.wt(avg[last]) - u.wt(avg[first]), 1) if first != last else None)
        sl = [data.sleep[d] for d in days7 if d in data.sleep]
        sleep = dict(labels=lab7, values=[round(data.sleep.get(d, 0), 1) for d in days7], avg=round(sum(sl) / len(sl), 1), n=len(sl),
                     last=round(data.sleep[day], 1) if day in data.sleep else None, goal=round(t["sleep_goal_h"], 1) if t.get("sleep_goal_h") else 7.5,
                     pct=sc["sleep"]) if sl else None
        wl = [d for d in days7 if d in data.water]
        wat = dict(labels=lab7, values=[round(water(data.water.get(d, 0)), 0 if u.imp else 1) for d in days7], unit=wunit,
                   today=wfmt(water(water_ml)), goal=round(water(t["water_ml"]), 0 if u.imp else 1), pct=sc["hydration"]) if wl else None
        mods["health"] = dict(recovery=rec, sleep=sleep, weight=weight, water=wat)

    if "peptides" in shown:
        mods["peptides"] = build_treatment(root, data, day, u)
        if mods["peptides"] is None:
            shown = [k for k in shown if k != "peptides"]

    photo = build_photo(root, u) if "health" in shown else None
    dash = dict(name=name, dateLabel=day.strftime("%A, %b %-d"), updated=dt.datetime.now().strftime("%-I:%M %p"),
                streak=streak(data, day), pal=pal, shown=shown,
                titles={k: CFG.MODULES[k]["label"] for k in CFG.ORDER}, **mods)
    return dash, photo


def blocks(dash, photo):
    body = ",\n".join(f"  {json.dumps(k)}: {json.dumps(v, separators=(',', ':'))}" for k, v in dash.items())  # one key per line: small EditCanvas diffs
    d = "// DATA-START\nconst DATA: Dash = {\n" + body + "\n};\n// DATA-END"
    p = "// PHOTO-START\nconst PHOTO = " + json.dumps(photo) + " as PhotoData | null;\n// PHOTO-END"
    return d, p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["full", "update", "commit"])
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--name", default="Your")
    ap.add_argument("--date")
    ap.add_argument("--units", default="auto", choices=["auto", "imperial", "metric"])
    a = ap.parse_args()
    root = Path(a.data)
    out = root / "dashboard"
    out.mkdir(parents=True, exist_ok=True)
    if a.cmd == "commit":
        for k in ("data_block", "photo_block"):
            new = out / f"{k}.new.txt"
            if new.exists():
                new.replace(out / f"{k}.live.txt")
        print("committed")
        return
    day = pdate(a.date) if a.date else dt.date.today()
    dash, photo = build(root, day, a.name, a.units)
    d, p = blocks(dash, photo)
    if a.cmd == "full":
        src = TEMPLATE.read_text()
        for blk, new in (("DATA", d), ("PHOTO", p)):
            s, e = src.index(f"// {blk}-START"), src.index(f"// {blk}-END") + len(f"// {blk}-END")
            src = src[:s] + new + src[e:]
        (out / "data_block.live.txt").write_text(d)
        (out / "photo_block.live.txt").write_text(p)
        print(src)
        return
    for k, v in (("data_block", d), ("photo_block", p)):
        live = out / f"{k}.live.txt"
        (out / f"{k}.new.txt").write_text(v)
        print(f"{k}: " + ("changed" if not live.exists() or live.read_text() != v else "same"),
              out / f"{k}.new.txt", "(old: " + str(live) + ")")


if __name__ == "__main__":
    main()
