"""Grok Life images: a calm, dark, type-led wellness system (pillars: recovery, sleep, nutrition, hydration, activity).
HTML/CSS/SVG rendered to PNG with headless Chromium at 2.25x.

Commands (same as charts.py): daily, eod, weekly, monthly, weight, treatment, all.
  python render.py daily --data /workspace/macro-coach --date 2026-11-18 [--coach "one sentence"]
Sizes: daily, eod, weight, weight_week are 1080x1350 (4:5). weekly and monthly are 1080 wide and taller.
Set GROKLIFE_FONTS=condensed|bricolage|archivo (SWOLE_FONTS still works) to render a different font pairing (see render_core.FONT_SETS).
"""
import argparse
import datetime as dt
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import charts as C  # data layer (CSV loading, units, weekly score)
import scoring as S
from render_core import *  # noqa
from dashboard_data import streak as streak_of

PAD = PAGE_PAD
INNER = W - 2 * PAD  # 432
DAYL = "MTWTFSS"


def fmt(n, d=0):
    return f"{n:,.{d}f}"


def sgn(v, nd=1):
    """Signed number with a true minus sign."""
    r = round(v, nd)
    return ("\u2212" if r < 0 else "+" if r > 0 else "") + f"{abs(r):.{nd}f}"


def dash(v, f=lambda x: x):
    return "\u2013" if v is None else f(v)


# ---------------------------------------------------------------- frame ------
WORDMARK = os.environ.get("GROKLIFE_WORDMARK", "weights")  # weights | tone (kept for comparison)


def wordmark():
    """Lowercase 'grok life.' in the display face with the green dot. Default: 'grok' at 500, 'life' at 700."""
    if WORDMARK == "tone":   # both bold, 'grok' in secondary text color
        g, l = "font-weight:700;color:" + TEXT2, "font-weight:700"
    else:
        g, l = "font-weight:500", "font-weight:700"
    return (f'<div style="display:flex;align-items:baseline;font-size:26px;line-height:24px;letter-spacing:-0.01em" class="disp">'
            f'<span style="{g}">grok</span><span style="{l};margin-left:6px">life</span>'
            f'<span style="width:6px;height:6px;border-radius:3px;background:{SOLID["recovery"]};margin-left:2px"></span></div>')


def header(day_label, streak_n):
    """Wordmark left; streak and date right. 24 px tall."""
    st = (f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:16px;color:{TEXT2}">{icon("flame", 16, TEXT2, 2)}'
          f'<span class="mono" style="font-size:14px">{streak_n}</span></span>') if streak_n else ""
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;height:24px;flex:none">'
            f'{wordmark()}'
            f'<div style="display:flex;align-items:center">{st}<span class="lab">{day_label}</span></div></div>')


def frame(body, day_label, streak_n, foot_left, fixed=True, height=None):
    """Shared header and footer for every image. Header 24, gap 24, body, gap 16, footer 16."""
    foot = (f'<div class="sm" style="display:flex;justify-content:space-between;align-items:center;height:16px;flex:none">'
            f'<span>{foot_left}</span><span>Grok Life \u00b7 Not medical advice</span></div>')
    h = f"height:{height or H45}px;" if fixed else ""
    return (f'<div class="page" style="position:relative;width:{W}px;{h}padding:{PAD}px;display:flex;flex-direction:column;overflow:hidden">'
            f'{header(day_label, streak_n)}<div class="pbody" style="flex:1;margin-top:{SP["l"]}px;display:flex;flex-direction:column;min-height:0">{body}</div>'
            f'<div style="height:{SP["m"] if fixed else SP["xl"]}px;flex:none"></div>{foot}</div>')


# ------------------------------------------------------------ components -----
def delta(d, suffix="", good_up=True, nd=0):
    """Arrow and signed number as plain text. Empty if d is None."""
    if d is None:
        return ""
    if abs(d) < 0.5 * 10 ** -nd:
        return f'<span class="lab">no change{"" if suffix.strip() in ("pt", "pts") else " " + suffix}</span>'
    up = d > 0
    col = GOOD if up == good_up else TEXT2
    return (f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:14px;font-weight:600;color:{col}">'
            f'{icon("arrow-up" if up else "arrow-down", 14, col, 2.4)}{abs(d):.{nd}f}<span class="lab" style="font-weight:500;margin-left:0"> {suffix}</span></span>')


def rule(frac, key, at="bottom:0"):
    """2 px progress rule: the separator between rows doubles as the pillar's progress bar."""
    f = max(0.0, min(frac or 0, 1.0))
    return (f'<div style="position:absolute;left:0;right:0;{at};height:2px;background:{HAIR}">'
            f'<div style="height:2px;width:{f * 100:.1f}%;background:{SOLID[key]}"></div></div>')


def num_unit(value, unit, size=28, unit_size=14):
    return (f'<div style="display:flex;align-items:baseline;gap:4px;white-space:nowrap"><span class="disp" style="font-size:{size}px">{value}</span>'
            f'<span class="lab" style="font-size:{unit_size}px">{unit}</span></div>')


def row(ic, key, name, value, unit, pct, frac=None, h=ROW_H):
    """List row on the shared column grid: icon | name | value | percent, progress rule underneath."""
    pc = "" if pct is None else f"{pct}%"
    fr = frac if frac is not None else (pct or 0) / 100
    return (f'<div style="position:relative;height:{h}px;display:flex;align-items:center;gap:{SP["m"]}px;flex:none">'
            f'{icon(ic, 20, SOLID[key], 2)}<span style="flex:1;font-size:16px;line-height:24px;font-weight:500">{name}</span>'
            f'{num_unit(value, unit)}<span class="disp" style="width:48px;text-align:right;font-size:20px;color:{SOLID[key]}">{pc}</span>{rule(fr, key)}</div>')


def macro_grid(f, t):
    cols = []
    for lab, k, tk in (("Protein", "p", "protein_g"), ("Carbs", "c", "carbs_g"), ("Fat", "f", "fat_g")):
        cols.append(f'<div style="flex:1;min-width:0"><div class="sm" style="color:{TEXT2}">{lab}</div>'
                    f'<div style="display:flex;align-items:baseline;gap:4px;white-space:nowrap"><span class="disp" style="font-size:20px">{fmt(f[k])}</span>'
                    f'<span class="sm">/ {fmt(t[tk])} g</span></div></div>')
    return f'<div style="display:flex;gap:{SP["m"]}px;padding-left:36px">{"".join(cols)}</div>'


def nutrition_block(f, t, final, pct):
    """Nutrition row plus macros, aligned to the row grid. 80 px (row 36 + gap 8 + macros 36)."""
    left = t["calories"] - f["cal"]
    if final:
        val, unit = fmt(f["cal"]), f'kcal \u00b7 {fmt(abs(left))} {"under" if left >= 0 else "over"}'
    else:
        val, unit = fmt(abs(left)), f'kcal {"left" if left >= 0 else "over"}'
    frac = f["cal"] / t["calories"] if t["calories"] else 0
    top = (f'<div style="display:flex;align-items:center;gap:{SP["m"]}px;height:36px">{icon("utensils", 20, SOLID["nutrition"], 2)}'
           f'<span style="flex:1;font-size:16px;line-height:24px;font-weight:500">Nutrition</span>{num_unit(val, unit)}'
           f'<span class="disp" style="width:48px;text-align:right;font-size:20px;color:{SOLID["nutrition"]}">{"" if pct is None else f"{pct}%"}</span></div>')
    return (f'<div style="position:relative;height:80px;flex:none">{top}<div style="margin-top:8px">{macro_grid(f, t)}</div>'
            f'{rule(frac, "nutrition", "top:34px")}</div>')


def coach(text, min_lines=2):
    if not text:
        return ""
    return f'<div style="font-size:18px;line-height:24px;font-weight:500;color:{TEXT};min-height:{24 * min_lines}px">{text}</div>'


def hero(label, value, key, state, sub_html, frac, size=112, ring_size=136, ring_icon="heart-pulse"):
    """The one hero per image: left-aligned tabular numeral, state word and delta under it, one flat ring at the right."""
    nh = round(size * 0.78)
    if value is None:
        v = f'<span style="color:{TEXT3};font-weight:500">\u2013</span>'
    else:
        v = (f'{value}<span class="disp" style="font-size:{round(size * .36)}px;letter-spacing:0;color:{TEXT2};margin-left:4px;font-weight:600">%</span>')
    col = SOLID[key] if value is not None else TEXT2
    rg = (f'<div style="position:relative;width:{ring_size}px;height:{ring_size}px;flex:none">{ring(ring_size, 14, (value or 0) / 100, key)}'
          f'<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center">{icon(ring_icon, 32, col, 1.75)}</div></div>')
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;flex:none">'
            f'<div><div class="lab" style="height:20px">{label}</div>'
            f'<div class="hero" style="font-size:{size}px;height:{nh}px;line-height:{nh}px;margin-top:{SP["xs"]}px;white-space:nowrap">{v}</div>'
            f'<div style="display:flex;align-items:center;gap:{SP["s"]}px;height:24px;margin-top:{SP["s"]}px;white-space:nowrap">'
            f'<span style="font-size:18px;font-weight:600;color:{col}">{state}</span>{sub_html}</div></div>{rg}</div>')


def day_ctx(data, day):
    t = data.target(day)
    f = data.food.get(day, dict(cal=0, p=0, c=0, f=0, fib=0, n=0, meals={}))
    return t, f, data.water.get(day, 0), data.steps.get(day, 0)


def water_txt(units, ml):
    return f"{ml / 29.5735:,.0f}" if units.imp else f"{ml / 1000:.1f}"


def water_unit(units):
    return "oz" if units.imp else "L"


def vs_avg(data, day, key):
    """Today's pillar minus the average of the previous 7 days (None if either is missing)."""
    cur = S.pillars(data, day).get(key)
    prev = S.avg([S.pillars(data, day - dt.timedelta(i)).get(key) for i in range(1, 8)])
    return None if cur is None or prev is None else cur - prev


def foot_time(day, label):
    if day == dt.date.today():
        return f'{label} \u00b7 {dt.datetime.now().strftime("%-I:%M %p")}'
    return f'{label} \u00b7 {day.strftime("%b %-d")}'


# ------------------------------------------------------------------ recap ----
def eod_html(data, day, units, coach_text=None):
    t, f, water_ml, steps = day_ctx(data, day)
    off = getattr(data, "off", ())
    p = S.pillars(data, day)
    ses = data.workout_sessions(day)
    dl = vs_avg(data, day, "day")
    h = hero("Day score", p["day"], "recovery", S.state_word(p["day"], "day"), delta(dl, "vs 7-day avg", True) if dl is not None else "", None, ring_icon="sun")
    line = coach_text if coach_text is not None else S.coach_line(data, day, "eod", units)
    sleep_h = data.sleep.get(day)
    act = fmt(steps) if steps else dash(None)
    act_u = f'steps \u00b7 {len(ses)} workout{"s" if len(ses) != 1 else ""}' if ses else ""
    rows = ""
    if "health" not in off:
        rows += (row("moon", "sleep", "Sleep", dash(sleep_h, lambda v: f"{v:.1f}"), "h" if sleep_h is not None else "", p["sleep"])
                 + row("droplet", "hydration", "Hydration", water_txt(units, water_ml), water_unit(units), p["hydration"]))
    if "activity" not in off or "workouts" not in off:
        rows += row("footprints", "activity", "Activity", act, act_u, p["activity"])
    nut = nutrition_block(f, t, True, p["nutrition"]) if "nutrition" not in off else ""
    body = (f'{h}<div style="margin-top:{SP["m"]}px">{coach(line)}</div><div style="margin-top:{SP["l"]}px">{rows}</div>{nut}')
    return page_html(frame(body, day.strftime("%a, %b %-d"), streak_of(data, day), foot_time(day, "Day recap")))


# ----------------------------------------------------------------- weight ----
def weight_series(data, day, ndays):
    days = [day - dt.timedelta(i) for i in range(ndays - 1, -1, -1)]
    return days, C.rolling_weight(data.weight, days)


def nice_ticks(lo, hi, want=4):
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / want
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 5, 10) if m * mag >= raw), default=mag)
    t = math.ceil(lo / step) * step
    out = []
    while t <= hi + 1e-9:
        out.append(t)
        t += step
    return out or [(lo + hi) / 2]


def weight_svg(data, day, units, ndays, w, h, goal_kg, left_pad=32, right_pad=6, top_pad=24, bottom_pad=28,
               dots=True, ylabels=True, xticks=4, extremes=True, compact=False, goal_label=True):
    """Weight curve on the page background: faint daily dots, one white 7-day average line, dashed goal line, plain-text labels."""
    days, avg = weight_series(data, day, ndays)
    daily = {d: units.wt(data.weight[d]) for d in days if d in data.weight}
    av = {d: units.wt(v) for d, v in avg.items()}
    if not av:
        return "", None
    vals = list(daily.values()) + list(av.values())
    lo, hi = min(vals), max(vals)
    goal = units.wt(goal_kg) if goal_kg else None
    span = max(hi - lo, 0.6 if units.imp else 0.3)
    goal_in = goal is not None and (lo - goal <= 1.0 * span) and (goal - hi <= 1.0 * span)
    if goal_in:
        lo, hi = min(lo, goal), max(hi, goal)
    pad = max((hi - lo) * 0.22, 0.6 if units.imp else 0.3)
    plo, phi = lo - pad, hi + pad
    n = len(days)
    px = lambda i: left_pad + (w - left_pad - right_pad) * (i / (n - 1) if n > 1 else 0)  # noqa: E731
    py = lambda v: top_pad + (h - top_pad - bottom_pad) * (phi - v) / (phi - plo)  # noqa: E731
    idx = {d: i for i, d in enumerate(days)}
    pts = [(px(idx[d]), py(av[d])) for d in days if d in av]
    keep = max(1, math.ceil(len(pts) / 14))  # thin a dense 7-day average so the curve reads smooth, not wiggly
    tp = pts[::keep]
    if tp[-1] != pts[-1]:
        tp.append(pts[-1])
    line = smooth_path(tp)
    base = h - bottom_pad + 8
    fill = line + f" L{tp[-1][0]:.2f} {base:.2f} L{tp[0][0]:.2f} {base:.2f} Z"
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs>'
         f'<linearGradient id="wf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{TEXT}" stop-opacity=".14"/><stop offset="1" stop-color="{TEXT}" stop-opacity="0"/></linearGradient></defs>']
    ticks = nice_ticks(plo + pad * (0.12 if compact else 0.35), phi - pad * (0.12 if compact else 0.35), 5 if compact else 4) if ylabels else []
    seen = set()
    for v in ticks:
        if f"{v:.0f}" in seen:  # a flat or one-point curve: two ticks would read the same number twice
            continue
        seen.add(f"{v:.0f}")
        s.append(f'<line x1="{left_pad}" x2="{w - right_pad}" y1="{py(v):.1f}" y2="{py(v):.1f}" stroke="{TEXT}" stroke-opacity=".10"/>'
                 f'<text x="{left_pad - 8}" y="{py(v) + 4:.1f}" text-anchor="end" font-size="12" fill="{TEXT3}">{v:.0f}</text>')
    s.append(f'<path d="{fill}" fill="url(#wf)"/>')
    if goal_in:
        gy = py(goal)
        s.append(f'<line x1="{left_pad}" x2="{w - right_pad}" y1="{gy:.1f}" y2="{gy:.1f}" stroke="{GOOD}" stroke-width="1.5" stroke-dasharray="6 6"/>')
        if goal_label:
            s.append(f'<text x="{w}" y="{gy - 8:.1f}" text-anchor="end" font-size="12" font-weight="600" fill="{GOOD}">Goal {goal:.1f}</text>')
    elif goal is not None and goal_label:
        arrow = "\u2193" if goal < lo else "\u2191"
        s.append(f'<text x="{w}" y="10" text-anchor="end" font-size="12" font-weight="600" fill="{GOOD}">{arrow} Goal {goal:.1f}</text>')
    if dots:
        for d, v in daily.items():
            s.append(f'<circle cx="{px(idx[d]):.1f}" cy="{py(v):.1f}" r="2.5" fill="{TEXT}" fill-opacity=".32"/>')
    s.append(f'<path d="{line}" fill="none" stroke="{TEXT}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    if extremes and len(daily) >= 3:
        for which, fn in (("High", max), ("Low", min)):
            d = fn(daily, key=daily.get)
            v = daily[d]
            x, y = px(idx[d]), py(v)
            lab = f"{which} {v:.1f}"
            lw = len(lab) * 7.4
            lx = min(max(x - lw / 2, left_pad), w - right_pad - lw)
            ly = y - 12 if which == "High" else y + 20
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{BG}" stroke="{TEXT}" stroke-width="1.5"/>'
                     f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="12" fill="{TEXT2}">{lab}</text>')
    lx, ly = tp[-1]
    s.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="6" fill="{TEXT}" stroke="{BG}" stroke-width="2"/>')
    for j in (range(xticks + 1) if xticks else []):
        i = round(j * (n - 1) / xticks)
        anchor = "start" if j == 0 else "end" if j == xticks else "middle"
        xx = px(i) if j else left_pad
        s.append(f'<text x="{xx:.1f}" y="{h - 4}" text-anchor="{anchor}" font-size="12" fill="{TEXT3}">{days[i].strftime("%b %-d")}</text>')
    s.append("</svg>")
    ad = sorted(av)
    info = dict(first=av[ad[0]], last=av[ad[-1]], low=min(daily.values()) if daily else min(av.values()),
                high=max(daily.values()) if daily else max(av.values()), goal=goal, goal_in=goal_in,
                n=(ad[-1] - ad[0]).days or 1, win=n, pts=len(av))
    return "".join(s), info


def stat_col(label, value, unit=""):
    return (f'<div style="flex:1;min-width:0"><div class="lab">{label}</div>'
            f'<div style="display:flex;align-items:baseline;gap:4px;margin-top:4px;white-space:nowrap"><span class="disp" style="font-size:28px">{value}</span>'
            f'<span class="lab">{unit}</span></div></div>')


def change_line(delta_v, n, unit, good):
    """'Down 3.5 lb in 29 days' as plain text with an arrow."""
    if abs(delta_v) < 0.05:
        txt, ic, col = f"Flat over {n} days", "minus", TEXT2
    else:
        txt = f'{"Down" if delta_v < 0 else "Up"} {abs(delta_v):.1f} {unit} in {n} days'
        ic = "trending-down" if delta_v < 0 else "trending-up"
        col = GOOD if good else TEXT
    return (f'<div style="display:flex;align-items:center;gap:8px;height:24px;font-size:18px;font-weight:600;color:{col}">{icon(ic, 20, col, 2.2)}{txt}</div>')


def weight_html(data, day, units, ndays=30, coach_text=None, tag="Weight"):
    t = data.target(day)
    svg, info = weight_svg(data, day, units, ndays, INNER, 160, t["goal_weight_kg"])
    if not info or info["pts"] < 2:  # one weigh-in is a starting point, not a trend
        return None
    dv = info["last"] - info["first"]
    gt = (t.get("goal_type") or "").lower()
    good = abs(dv) > 0.05 and ((gt == "lose" and dv < 0) or (gt == "gain" and dv > 0))
    goal = info["goal"]
    stats = [stat_col("Start", f'{info["first"]:.1f}', units.w), stat_col("Low", f'{info["low"]:.1f}', units.w)]
    stats.append(stat_col("To goal", f'{abs(info["last"] - goal):.1f}', units.w) if goal else stat_col("High", f'{info["high"]:.1f}', units.w))
    line = coach_text if coach_text is not None else S.weight_line(dv, info["n"], None, units.w, gt)
    size = 96
    nh = round(size * .78)
    head = (f'<div class="lab" style="height:20px">7-day average</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-top:8px;height:{nh}px"><span class="hero" style="font-size:{size}px;line-height:{nh}px">{info["last"]:.1f}</span>'
            f'<span class="disp" style="font-size:28px;color:{TEXT2};font-weight:600">{units.w}</span></div>'
            f'<div style="margin-top:16px">{change_line(dv, info["n"], units.w, good)}</div>')
    body = (f'{head}<div style="margin-top:{SP["l"]}px">{svg}</div>'
            f'<div style="display:flex;gap:{SP["m"]}px;margin-top:{SP["m"]}px">{"".join(stats)}</div>'
            f'<div style="margin-top:{SP["l"]}px">{coach(line)}</div>')
    return page_html(frame(body, day.strftime("%a, %b %-d"), streak_of(data, day), foot_time(day, f"{tag} \u00b7 last {ndays} days")))


# ---------------------------------------------------------------- windows ----
def window_stats(data, days):
    """Raw averages over a list of days, for the sub-lines under each pillar."""
    ts = [data.target(d) for d in days]
    sl = [data.sleep[d] for d in days if d in data.sleep]
    wa = [data.water[d] for d in days if d in data.water]
    st = [data.steps[d] for d in days if d in data.steps]
    lg = [d for d in days if S.logged(data, d)]
    return dict(sleep=S.avg(sl), water=S.avg(wa), steps=S.avg(st), logged=len(lg), n=len(days),
                cal=S.avg([data.food[d]["cal"] for d in lg]), protein=S.avg([data.food[d]["p"] for d in lg]),
                sessions=sum(len(data.workout_sessions(d)) for d in days),
                prot_hit=sum(1 for d in lg if data.food[d]["p"] >= 0.9 * data.target(d)["protein_g"]),
                sleep_goal=ts[-1]["sleep_goal_h"])


def bars_html(vals, key, w=136, h=48, gap=4):
    """Mini bar strip of 0-100 values. Flat color, the latest bar at full strength, older bars at 55%. None shows a dot."""
    n = len(vals)
    gap = 2 if n > 12 else gap
    bw = max(2.0, (w - gap * (n - 1)) / n)
    cols = []
    for i, v in enumerate(vals):
        if v is None:
            cols.append(f'<div style="width:{bw:.1f}px;height:{h}px;display:flex;align-items:flex-end"><div style="width:100%;height:{min(bw, 4):.1f}px;border-radius:2px;background:{HAIR}"></div></div>')
            continue
        bh = max(v / 100 * h, 4)
        op = 1 if (i == n - 1 or n > 12) else 0.55
        cols.append(f'<div style="width:{bw:.1f}px;height:{h}px;display:flex;align-items:flex-end"><div style="width:100%;height:{bh:.1f}px;border-radius:{min(bw / 2, 3):.1f}px;background:{SOLID[key]};opacity:{op}"></div></div>')
    return f'<div style="display:flex;gap:{gap}px;align-items:flex-end;width:{w}px;height:{h}px">{"".join(cols)}</div>'


def pillar_row(ic, key, name, pct, sub, d_prev, vals, bars_w=136, vs="last week"):
    """Review row, 104 px: name and delta, big percent, one detail line; flat bar strip at the right; hairline below."""
    d = delta(d_prev, "pt" if d_prev is not None and round(abs(d_prev)) == 1 else "pts", True) if d_prev is not None else ""
    return (f'<div style="position:relative;height:104px;display:flex;align-items:center;gap:{SP["m"]}px;flex:none;border-bottom:1px solid {HAIR}">'
            f'<div style="flex:1;min-width:0"><div style="display:flex;align-items:center;gap:8px;height:24px">{icon(ic, 20, SOLID[key], 2)}'
            f'<span style="font-size:16px;line-height:24px;font-weight:500">{name}</span>{d}</div>'
            f'<div style="display:flex;align-items:baseline;gap:2px;margin-top:8px;height:40px"><span class="disp" style="font-size:44px;line-height:40px;color:{SOLID[key] if pct is not None else TEXT3}">{dash(pct, lambda v: f"{v:.0f}")}</span>'
            f'<span class="disp" style="font-size:20px;color:{TEXT2}">{"" if pct is None else "%"}</span></div>'
            f'<div class="sm" style="color:{TEXT2};margin-top:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{sub}</div></div>'
            f'{bars_html(vals, key, bars_w)}</div>')


def pillar_rows(data, units, cur_days, prev_days, bars_vals, cur_stats, bars_w=136):
    cur, series = S.period(data, cur_days)
    prev, _ = S.period(data, prev_days)
    st = cur_stats
    tt = data.target(cur_days[-1])
    dlt = lambda k: None if cur[k] is None or prev[k] is None else cur[k] - prev[k]  # noqa: E731
    subs = dict(
        recovery="Daily readiness",
        sleep=(f'{st["sleep"]:.1f} h avg \u00b7 goal {tt["sleep_goal_h"]:g} h' if st["sleep"] is not None else "No sleep logged"),
        nutrition=(f'{fmt(st["cal"])} kcal \u00b7 protein {st["prot_hit"]}/{st["logged"]} days' if st["cal"] is not None else "No meals logged"),
        hydration=(f'{water_txt(units, st["water"])} {water_unit(units)} a day' if st["water"] is not None else "No water logged"),
        activity=(f'{fmt(st["steps"])} steps \u00b7 {st["sessions"]} session{"s" if st["sessions"] != 1 else ""}' if st["steps"] is not None else f'{st["sessions"]} session{"s" if st["sessions"] != 1 else ""}'))
    rows = [("heart-pulse", "recovery", "Recovery"), ("moon", "sleep", "Sleep"), ("utensils", "nutrition", "Nutrition"),
            ("droplet", "hydration", "Hydration"), ("activity", "activity", "Activity")]
    off = getattr(data, "off", ())
    gone = {"recovery": "health", "sleep": "health", "hydration": "health", "nutrition": "nutrition"}
    rows = [r for r in rows if gone.get(r[1]) not in off and not (r[1] == "activity" and "activity" in off and "workouts" in off)]
    return "".join(pillar_row(ic, k, nm, cur[k], subs[k], dlt(k), bars_vals(series[k]), bars_w) for ic, k, nm in rows)


def section_label(text):
    return f'<div class="lab" style="margin-top:{SP["xl"]}px;height:20px">{text}</div>'


def review_hero(label, score, prev, word, sub, vs_word):
    d = None if prev is None or score is None else score - prev
    return hero(label, score, "recovery", word, delta(d, f"vs {vs_word}", True) if d is not None else "", None, ring_icon="trending-up") + \
        f'<div class="lab" style="margin-top:{SP["m"]}px">{sub}</div>'


def weight_block(winfo, wsvg, units, title, big_is_change=False):
    """Weight section of the reviews: one number, one sentence, the curve. No card."""
    wd = winfo["last"] - winfo["first"]
    big = sgn(wd) if big_is_change else f'{winfo["last"]:.1f}'
    sub = f'{winfo["last"]:.1f} {units.w} now, 7-day average' if big_is_change else f'{sgn(wd)} {units.w} over {winfo["n"]} days'
    return (f'{section_label(title)}<div style="display:flex;align-items:baseline;gap:8px;margin-top:8px"><span class="hero" style="font-size:64px;line-height:56px;height:56px">{big}</span>'
            f'<span class="disp" style="font-size:24px;color:{TEXT2};font-weight:600">{units.w}</span></div>'
            f'<div class="lab" style="margin-top:8px">{sub}</div><div style="margin-top:{SP["m"]}px">{wsvg}</div>')


# ----------------------------------------------------------------- weekly ----
def weekly_html(data, end, units, coach_text=None):
    days = [end - dt.timedelta(i) for i in range(6, -1, -1)]
    prev_days = [d - dt.timedelta(7) for d in days]
    sc = C.week_score(data, end)
    sc_prev = C.week_score(data, end - dt.timedelta(7))
    has_prev = any(d in data.food for d in prev_days)
    st = window_stats(data, days)
    word = "Strong week" if sc["score"] >= 80 else "Solid week" if sc["score"] >= 60 else "Rebuilding week"
    early = st["logged"] < 3  # under three logged days a week score is not a verdict: say so instead of "Rebuilding"
    if early:
        word = "Early days"
    h = review_hero("Week score", sc["score"], sc_prev["score"] if has_prev else None, word,
                    f'{st["logged"]} of 7 days logged \u00b7 {sc["sessions"]} of {sc["planned_sessions"]} sessions', "last week")
    line = coach_text if coach_text is not None else (f'{st["logged"]} of 7 days logged so far. Keep logging and the next review will say more.' if early else sc["focus"])
    rows = pillar_rows(data, units, days, prev_days, lambda v: v, st)
    wsvg, winfo = weight_svg(data, end, units, 28, INNER, 152, data.target(end)["goal_weight_kg"], xticks=2, extremes=False, compact=True, top_pad=16, bottom_pad=28, goal_label=False)
    wb = weight_block(winfo, wsvg, units, "Weight, last 28 days") if winfo and winfo["pts"] > 1 and "health" not in getattr(data, "off", ()) else ""
    body = (f'{h}<div style="margin-top:{SP["l"]}px">{coach(line)}</div>{section_label("Pillars compared with last week")}'
            f'<div style="margin-top:{SP["s"]}px;border-top:1px solid {HAIR}">{rows}</div>{wb}')
    return page_html(frame(body, f'{days[0].strftime("%b %-d")} \u2013 {end.strftime("%-d")}', streak_of(data, end), f'Weekly review \u00b7 {end.strftime("%b %-d")}', fixed=False)), sc


# ---------------------------------------------------------------- monthly ----
def monthly_html(data, end, units, coach_text=None):
    days = [end - dt.timedelta(i) for i in range(29, -1, -1)]
    prev_days = [days[0] - dt.timedelta(i) for i in range(30, 0, -1)]
    cur, series = S.period(data, days)
    prev, _ = S.period(data, prev_days)
    st, pst = window_stats(data, days), window_stats(data, prev_days)
    score = None if cur["day"] is None else round(cur["day"])
    pscore = None if prev["day"] is None else round(prev["day"])
    word = "Strong month" if (score or 0) >= 80 else "Solid month" if (score or 0) >= 60 else "Building month" if score is not None else "No score yet"
    early = st["logged"] < 7
    if early:
        word = "Early days"
    h = review_hero("Month score", score, pscore, word, f'{st["logged"]} of 30 days logged \u00b7 {st["sessions"]} session{"" if st["sessions"] == 1 else "s"}', "last month")
    rate = st["logged"] / 30
    default_line = (f'{st["logged"]} of 30 days logged so far. The month view gets useful after a week of logging.' if early else
                    f"Consistency is the lever: {st['logged']} of 30 days logged. Aim for 27 next month." if rate < 0.9
                    else f"{st['logged']} of 30 days logged. Consistency is your edge, keep it.")
    wk = S.weakest(cur)
    line = coach_text if coach_text is not None else (S.GAP_LINES[wk] if wk and rate >= 0.9 else default_line)
    rows = pillar_rows(data, units, days, prev_days, lambda v: v, st)
    wsvg, winfo = weight_svg(data, end, units, 30, INNER, 184, data.target(end)["goal_weight_kg"], xticks=3, extremes=True, top_pad=24, bottom_pad=28)
    health_on = "health" not in getattr(data, "off", ())
    wb = weight_block(winfo, wsvg, units, "Weight, last 30 days", big_is_change=True) if winfo and winfo["pts"] > 1 and health_on else ""
    sites = [("waist_cm", "Waist"), ("hips_cm", "Hips"), ("chest_cm", "Chest"), ("arm_cm", "Arm"), ("thigh_cm", "Thigh")]
    cells = []
    for col, name in sites:
        ser = [(dd, C.num(x.get(col))) for dd, x in data.measure if C.num(x.get(col)) is not None]
        if len(ser) >= 2:
            dl = units.ln(ser[-1][1] - ser[0][1])
            cells.append(f'<div style="flex:1;min-width:0"><div class="lab">{name}</div><div style="display:flex;align-items:baseline;gap:4px;margin-top:4px">'
                         f'<span class="disp" style="font-size:28px">{sgn(dl)}</span><span class="lab">{units.l}</span></div></div>')
    cells = cells if health_on else []
    meas = (f'{section_label("Measurements, first to latest")}<div style="display:flex;gap:{SP["m"]}px;margin-top:{SP["m"]}px">{"".join(cells)}</div>') if cells else ""
    body = (f'{h}<div style="margin-top:{SP["l"]}px">{coach(line)}</div>{section_label("Pillars compared with the previous 30 days")}'
            f'<div style="margin-top:{SP["s"]}px;border-top:1px solid {HAIR}">{rows}</div>{wb}{meas}')
    html = page_html(frame(body, f'{days[0].strftime("%b %-d")} \u2013 {end.strftime("%b %-d")}', streak_of(data, end), f'Monthly review \u00b7 {end.strftime("%b %-d")}', fixed=False))
    return html, dict(this=dict(score=score, logged=st["logged"], cal=st["cal"], sessions=st["sessions"], **{k: cur[k] for k in S.PILLARS}),
                      last=dict(score=pscore, logged=pst["logged"], cal=pst["cal"], sessions=pst["sessions"], **{k: prev[k] for k in S.PILLARS}))


# ----------------------------------------------------------------- driver ----
KINDS = ["overview", "detail", "daily", "eod", "weekly", "monthly", "weight", "treatment", "all"]


def render_all(kind, data_dir, out_dir, day, units_arg, ndays, coach=None, window=30, compound=None, theme=None, module=None, palette=None):
    """Render images. `theme` is light or dark (default: the saved preference in config.json). Disabled modules, and modules
    with no data yet, are never drawn (config.py)."""
    import config as CFG
    import render_modules as RMOD
    cfg = CFG.load(data_dir)
    set_theme(CFG.resolve_theme(data_dir, theme), palette or cfg.get("palette"))
    data = C.Data(data_dir)
    data.off = {k for k in CFG.ORDER if not cfg["modules"].get(k)}
    shown = CFG.visible(data_dir)
    units = C.pick_units(data, units_arg, day)
    out = Path(out_dir)
    ds = day.isoformat()
    if kind == "daily":
        kind = "overview"          # the old midday image is now the overview
    if kind == "treatment":
        kind, module = "detail", "peptides"
    if kind == "all":
        kinds = ["overview", "detail", "eod", "weekly", "monthly"]
    else:
        kinds = [kind]
    paths, summary = [], {"theme": MODE, "shown": shown}
    with Renderer() as r:
        for k in kinds:
            if k == "overview":
                paths.append(r.shot(RMOD.overview_html(data, day, units, coach, shown), out / f"overview_{ds}.png", min_height=SHORT))
                summary["day"] = S.pillars(data, day)
            elif k == "detail":
                mods = shown if module in (None, "all") else [module]
                for m in mods:
                    if m not in CFG.MODULES:
                        sys.exit(f"unknown module {m!r}; use: {', '.join(CFG.ORDER)}")
                    if m not in shown:
                        why = "turned off" if not cfg["modules"].get(m) else "enabled but has no data yet"
                        print(f"note: {CFG.MODULES[m]['label']} is {why}, no image", file=sys.stderr)
                        continue
                    html = RMOD.DETAIL[m](data, day, units, coach, **(dict(window=window, compound=compound) if m == "peptides" else {}))
                    if html:
                        paths.append(r.shot(html, out / f"detail_{m}_{ds}.png", min_height=SHORT))
                        if m == "peptides":
                            st = RMOD.M.status(data.root, RMOD.RM.default_now(day), compound)
                            summary["peptides"] = st and {k2: v for k2, v in st.items() if k2 in ("compound", "level_now", "level_next", "ss_peak", "ss_trough")}
            elif k == "eod":
                paths.append(r.shot(eod_html(data, day, units, coach), out / f"eod_{ds}.png"))
                summary["day"] = S.pillars(data, day)
            elif k == "weekly":
                html, sc = weekly_html(data, day, units, coach)
                paths.append(r.shot(html, out / f"weekly_{ds}.png"))
                summary["week"] = sc
            elif k == "monthly":
                html, ms = monthly_html(data, day, units, coach)
                paths.append(r.shot(html, out / f"monthly_{ds}.png"))
                summary["month"] = ms
            elif k == "weight":
                if "health" not in shown:
                    print("note: Health is off or has no data, no weight image", file=sys.stderr)
                    continue
                w = weight_html(data, day, units, ndays, coach)
                if w:
                    paths.append(r.shot(w, out / f"weight_{ds}.png"))
                else:
                    print("note: only one weigh-in so far, the weight image needs two. Ask for another weigh-in.", file=sys.stderr)
    return paths, summary


SHORT = 440  # CSS px: a one-module overview should not sit in a mostly empty 4:5 frame


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kind", choices=KINDS)
    ap.add_argument("module", nargs="?", help="detail: workouts, nutrition, activity, health or peptides (default: every module that is shown)")
    ap.add_argument("--data", default=str(C.DEFAULT_DATA))
    ap.add_argument("--out", default=None)
    ap.add_argument("--date", default=None)
    ap.add_argument("--units", default="auto", choices=["auto", "imperial", "metric"])
    ap.add_argument("--theme", default=None, choices=["light", "dark"], help="default: the saved preference in config.json")
    ap.add_argument("--palette", default=None, help="palette name (default: the saved one, else lagoon)")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--window", type=int, default=30, choices=[7, 30, 90], help="peptides detail: level curve window in days")
    ap.add_argument("--compound", default=None, help="peptides detail: compound to show (default: the most recent dose)")
    ap.add_argument("--coach", default=None, help="your own one-sentence coach line (max 140 chars); default is rule-based")
    a = ap.parse_args(argv)
    day = C.pdate(a.date) if a.date else dt.date.today()
    if not day:
        sys.exit("bad --date, use YYYY-MM-DD")
    out = a.out or str(Path(a.data) / "charts")
    coach = None
    if a.coach is not None:
        import html as _h
        coach = _h.escape(" ".join(a.coach.split())[:140])
    paths, summary = render_all(a.kind, a.data, out, day, a.units, a.days, coach, a.window, a.compound, a.theme, a.module, a.palette)
    for p in dict.fromkeys(paths):
        print(p)
    print("SUMMARY:" + json.dumps(summary, default=str))


if __name__ == "__main__":
    main()
