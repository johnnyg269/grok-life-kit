"""Overview and module detail images for Grok Life.

The overview is one image: the recovery hero (when Health is shown) and one block per module the user opted into. Each block
opens its own detail image (`charts.py detail <module>`) which starts with a back link to the Overview. A module that is
disabled, or has no data yet, is not drawn at all: no placeholder, no empty block (config.py decides, section 0.1).

Same system as render.py: Barlow Condensed + Hanken Grotesk, the 4/8/16/24/32 scale, hairline rows, flat colour, no glow. Colours
come from the active theme (render_core.set_theme), so every function here works in light and dark.
"""
import datetime as dt

import config as CFG
import meds as M
import render as R
import render_meds as RM
import scoring as S
from render_core import *  # noqa

INNER = R.INNER
LABEL = {k: v["label"] for k, v in CFG.MODULES.items()}
ICON = dict(workouts="dumbbell", nutrition="utensils", activity="footprints", health="heart-pulse", peptides="syringe")
HUE = dict(workouts="activity", nutrition="nutrition", activity="activity", health="recovery", peptides="medication")
DAYL = "MTWTFSS"


# ------------------------------------------------------------------ parts ----
def nav(key):
    """Back link to the Overview on the left, the module's name on the right. First row of every detail image."""
    hue = SOLID[HUE[key]]
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;height:32px;flex:none">'
            f'<div style="display:flex;align-items:center;gap:4px;margin-left:-4px;color:{TEXT2}">{icon("chevron-left", 22, TEXT2, 2.2)}'
            f'<span style="font-size:16px;line-height:24px;font-weight:500">Overview</span></div>'
            f'<div style="display:flex;align-items:center;gap:8px">{icon(ICON[key], 20, hue, 2)}'
            f'<span style="font-size:16px;line-height:24px;font-weight:600">{LABEL[key]}</span></div></div>')


def block(key, inner):
    """One module on the overview: title with a chevron (it opens the detail image), hairline above."""
    hue = SOLID[HUE[key]]
    head = (f'<div style="display:flex;justify-content:space-between;align-items:center;height:28px">'
            f'<div style="display:flex;align-items:center;gap:8px">{icon(ICON[key], 20, hue, 2)}'
            f'<span style="font-size:16px;line-height:24px;font-weight:600">{LABEL[key]}</span></div>'
            f'{icon("chevron-right", 22, TEXT3, 2)}</div>')
    return (f'<div style="padding:{SP["l"]}px 0;border-top:1px solid {HAIR};flex:none">{head}'
            f'<div style="margin-top:{SP["m"]}px">{inner}</div></div>')


def big(value, unit, label, size=44, color=None):
    """Display numeral with its unit, a label under it."""
    col = f"color:{color};" if color else ""
    return (f'<div style="white-space:nowrap"><div style="display:flex;align-items:baseline;gap:4px;height:{round(size * .86)}px">'
            f'<span class="disp" style="font-size:{size}px;line-height:{round(size * .86)}px;{col}">{value}</span>'
            f'<span class="lab" style="font-size:16px">{unit}</span></div><div class="lab" style="margin-top:{SP["xs"]}px">{label}</div></div>')


def hero_value(label, value, unit, key, frac, ic, sub_html, size=96, ring_size=120):
    """Detail-page hero: label, big numeral and unit, one line under it, one flat ring at the right."""
    nh = round(size * .78)
    c = SOLID[key]
    rg = (f'<div style="position:relative;width:{ring_size}px;height:{ring_size}px;flex:none">{ring(ring_size, 12, frac, key)}'
          f'<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center">{icon(ic, 28, c, 1.75)}</div></div>')
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:{SP["m"]}px;flex:none"><div>'
            f'<div class="lab" style="height:20px">{label}</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-top:{SP["s"]}px;height:{nh}px;white-space:nowrap"><span class="hero" style="font-size:{size}px;line-height:{nh}px">{value}</span>'
            f'<span class="disp" style="font-size:28px;color:{TEXT2}">{unit}</span></div>'
            f'<div style="margin-top:{SP["m"]}px;white-space:nowrap">{sub_html}</div></div>{rg}</div>')


def stats(*cols):
    return f'<div style="display:flex;gap:{SP["m"]}px;margin-top:{SP["l"]}px">{"".join(R.stat_col(*c) for c in cols)}</div>'


def sec(title):
    return R.section_label(title)


def cols_svg(vals, labels, key, ref=None, ref_label="", w=INNER, h=132, value_fmt=lambda v: f"{v:,.0f}", ymax=None):
    """Column chart on the page background: older columns at 55%, the latest at full colour with its value, optional dashed reference."""
    n = len(vals)
    top = 20
    base = h - 24
    nums = [v for v in vals if v is not None]
    ymax = ymax or max(nums + ([ref] if ref else []) + [1]) * 1.12
    gap = 6 if n <= 14 else 3
    bw = (w - gap * (n - 1)) / n
    c = SOLID[key]
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><line x1="0" x2="{w}" y1="{base}" y2="{base}" stroke="{HAIR}"/>']
    for i, v in enumerate(vals):
        x = i * (bw + gap)
        last = i == n - 1
        if v is not None and v > 0:
            bh = max(3, (base - top) * v / ymax)
            s.append(f'<rect x="{x:.1f}" y="{base - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="{min(bw / 2, 4):.1f}" fill="{c}" fill-opacity="{1 if last else .55}"/>')
            if last:
                s.append(f'<text x="{x + bw / 2:.1f}" y="{base - bh - 8:.1f}" text-anchor="middle" font-size="13" font-weight="600" fill="{TEXT}" stroke="{BG}" stroke-width="4" paint-order="stroke">{value_fmt(v)}</text>')
        else:
            s.append(f'<rect x="{x:.1f}" y="{base - 3}" width="{bw:.1f}" height="3" rx="1.5" fill="{HAIR}"/>')
        if labels[i] and (n <= 14 or i % 7 == 0 or last):
            s.append(f'<text x="{x + bw / 2:.1f}" y="{h - 4}" text-anchor="middle" font-size="12" fill="{TEXT3}">{labels[i]}</text>')
    if ref:
        ry = base - (base - top) * ref / ymax
        s.append(f'<line x1="0" x2="{w}" y1="{ry:.1f}" y2="{ry:.1f}" stroke="{GOOD}" stroke-width="1.5" stroke-dasharray="6 6"/>'
                 f'<text x="0" y="{ry - 6:.1f}" font-size="12" font-weight="600" fill="{GOOD}" stroke="{BG}" stroke-width="4" paint-order="stroke">{ref_label}</text>')
    s.append("</svg>")
    return "".join(s)


def list_row(left, mid, right, sub=None, h=52):
    sb = f'<div class="sm" style="color:{TEXT2}">{sub}</div>' if sub else ""
    return (f'<div style="display:flex;align-items:center;gap:{SP["m"]}px;min-height:{h}px;border-bottom:1px solid {HAIR};flex:none">'
            f'<span class="lab" style="width:76px;flex:none">{left}</span><div style="flex:1;min-width:0"><div style="font-size:16px;line-height:24px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{mid}</div>{sb}</div>'
            f'<span style="white-space:nowrap">{right}</span></div>')


def wrap(day, data, body, label, key=None):
    return R.page_html(R.frame(body, day.strftime("%a, %b %-d"), R.streak_of(data, day), R.foot_time(day, label), fixed=False))


# ------------------------------------------------------------------- data ----
def week_days(day, n=7):
    return [day - dt.timedelta(i) for i in range(n - 1, -1, -1)]


def minutes(data, d):
    return sum(C_num(s.get("duration_min")) for s in data.workout_sessions(d))


def C_num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def workouts_info(data, day):
    days = week_days(day)
    ses = [(d, s) for d in days for s in data.workout_sessions(d)]
    t = data.target(day)
    return dict(days=days, n=len(ses), planned=int(t["sessions_per_week"]), minutes=sum(C_num(s.get("duration_min")) for _, s in ses),
                kcal=sum(C_num(s.get("est_kcal")) for _, s in ses), ses=ses, active={d for d, _ in ses})


# --------------------------------------------------------------- overview ----
def b_workouts(data, day, units):
    w = workouts_info(data, day)
    dots = []
    for d in w["days"]:
        on = d in w["active"]
        today = d == day
        dots.append(f'<div style="display:flex;flex-direction:column;align-items:center;gap:{SP["xs"]}px">'
                    f'<div style="width:24px;height:24px;border-radius:12px;box-sizing:border-box;background:{SOLID["workouts"] if on else "transparent"};'
                    f'border:2px solid {SOLID["workouts"] if on else ink(.22)};display:flex;align-items:center;justify-content:center">'
                    f'{icon("check", 14, ON_ACCENT, 3) if on else ""}</div>'
                    f'<span class="sm" style="{"color:" + TEXT + ";font-weight:700" if today else ""}">{DAYL[d.weekday()]}</span></div>')
    last = w["ses"][-1] if w["ses"] else None
    ll = (f'<div class="lab" style="margin-top:{SP["m"]}px">Last: {(last[1].get("name") or last[1].get("type") or "Workout").strip()}, {last[0].strftime("%a")} \u00b7 '
          f'{C_num(last[1].get("duration_min")):.0f} min</div>') if last else ""
    left = big(f'{w["n"]}<span class="lab" style="font-size:20px;margin-left:6px">of {w["planned"]}</span>' if w["planned"] else str(w["n"]),
               "", "sessions this week")
    return block("workouts", f'<div style="display:flex;justify-content:space-between;align-items:center">{left}'
                 f'<div style="display:flex;gap:{SP["s"]}px">{"".join(dots)}</div></div>{ll}')


def b_nutrition(data, day, units):
    t, f, _, _ = R.day_ctx(data, day)
    left = t["calories"] - f["cal"]
    frac = f["cal"] / t["calories"] if t["calories"] else 0
    c = SOLID["nutrition"]
    macros = []
    for lab, k, tk in (("Protein", "p", "protein_g"), ("Carbs", "c", "carbs_g"), ("Fat", "f", "fat_g")):
        fr = min(f[k] / t[tk], 1) if t[tk] else 0
        macros.append(f'<div style="flex:1;min-width:0"><div class="lab">{lab}</div>'
                      f'<div style="display:flex;align-items:baseline;gap:4px;white-space:nowrap;margin-top:{SP["xs"]}px"><span class="disp" style="font-size:24px">{R.fmt(f[k])}</span>'
                      f'<span class="sm">/ {R.fmt(t[tk])} g</span></div>'
                      f'<div style="height:4px;border-radius:2px;background:{HAIR};margin-top:{SP["s"]}px"><div style="height:4px;width:{fr * 100:.0f}%;border-radius:2px;background:{c}"></div></div></div>')
    top = (f'<div style="display:flex;justify-content:space-between;align-items:flex-end">{big(R.fmt(abs(left)), "kcal", "left today" if left >= 0 else "over today")}'
           f'<span class="disp" style="font-size:28px;color:{c}">{frac * 100:.0f}%</span></div>')
    return block("nutrition", f'{top}<div style="display:flex;gap:{SP["l"]}px;margin-top:{SP["l"]}px">{"".join(macros)}</div>')


def b_activity(data, day, units):
    t = data.target(day)
    days = week_days(day)
    steps = data.steps.get(day, 0)
    vals = [min(100, 100 * data.steps[d] / t["step_goal"]) if d in data.steps and t["step_goal"] else None for d in days]
    pct = round(100 * steps / t["step_goal"]) if t["step_goal"] else 0
    return block("activity", f'<div style="display:flex;justify-content:space-between;align-items:flex-end">'
                 f'{big(R.fmt(steps) if steps else "\u2013", "steps", f"{pct}% of {R.fmt(t["step_goal"])}")}{R.bars_html(vals, "activity", 168, 56)}</div>')


def b_health(data, day, units):
    t = data.target(day)
    p = S.pillars(data, day)
    cols = []
    sl = data.sleep.get(day)
    if sl is not None:
        cols.append((icon("moon", 16, SOLID["sleep"], 2), "Sleep", f"{sl:.1f}", "h", "sleep", (p["sleep"] or 0) / 100, f'{p["sleep"]}% of goal'))
    days28 = week_days(day, 28)
    av = C.rolling_weight(data.weight, days28) if hasattr(C, "rolling_weight") else {}
    if av:
        first, last = av[min(av)], av[max(av)]
        d = units.wt(last) - units.wt(first)
        sub = "steady" if abs(d) < 0.1 else f'{"down" if d < 0 else "up"} {abs(d):.1f} in 28 days'
        cols.append((icon("scale", 16, TEXT, 2), "Weight", f"{units.wt(last):.1f}", units.w, None, None, sub))
    if day in data.water:
        cols.append((icon("droplet", 16, SOLID["hydration"], 2), "Water", R.water_txt(units, data.water[day]), R.water_unit(units), "hydration", (p["hydration"] or 0) / 100, f'{p["hydration"]}% of goal'))
    cells = []
    for ic, name, v, u, key, fr, sub in cols:
        bar = (f'<div style="height:4px;border-radius:2px;background:{HAIR};margin-top:{SP["s"]}px"><div style="height:4px;width:{fr * 100:.0f}%;border-radius:2px;background:{SOLID[key]}"></div></div>'
               if key else f'<div style="height:4px;margin-top:{SP["s"]}px"></div>')
        cells.append(f'<div style="flex:1;min-width:0"><div style="display:flex;align-items:center;gap:6px" class="lab">{ic}{name}</div>'
                     f'<div style="display:flex;align-items:baseline;gap:4px;white-space:nowrap;margin-top:{SP["xs"]}px"><span class="disp" style="font-size:28px">{v}</span><span class="lab">{u}</span></div>'
                     f'{bar}<div class="sm" style="margin-top:{SP["xs"]}px;white-space:nowrap">{sub}</div></div>')
    return block("health", f'<div style="display:flex;gap:{SP["l"]}px">{"".join(cells)}</div>')


def b_peptides(data, day, units):
    now = RM.default_now(day)
    st = M.status(data.root, now, None)
    if not st:
        return ""
    nxt = st["next"]
    sub = f'{st["label"]} \u00b7 {st["last"]["mg"]:g} mg {RM.cadence(st["interval_days"])}'
    left = big(nxt["countdown"], "", f'Next dose {nxt["t"].strftime("%a")}, {RM.short_time(nxt["t"])}', color=SOLID["medication"])
    return block("peptides", f'<div style="display:flex;justify-content:space-between;align-items:flex-end">{left}{RM.spark(st)}</div>'
                 f'<div class="lab" style="margin-top:{SP["m"]}px">{sub} \u00b7 {st["level_now"]:.1f} mg estimated now</div>')


BLOCKS = dict(workouts=b_workouts, nutrition=b_nutrition, activity=b_activity, health=b_health, peptides=b_peptides)


def overview_html(data, day, units, coach_text=None, shown=None):
    shown = shown if shown is not None else CFG.visible(data.root)
    parts = []
    if "health" in shown:
        p = S.pillars(data, day)
        rec = p["recovery"]
        dl = R.vs_avg(data, day, "recovery")
        parts.append(R.hero("Recovery", rec, "recovery", S.state_word(rec), R.delta(dl, "vs 7-day avg", True) if dl is not None else "", None)
                     if rec is not None else "")
        line = coach_text if coach_text is not None else S.coach_line(data, day, "daily", units)
        parts.append(f'<div style="margin-top:{SP["m"]}px;margin-bottom:{SP["l"]}px">{R.coach(line)}</div>')
    elif coach_text:
        parts.append(f'<div style="margin-bottom:{SP["l"]}px">{R.coach(coach_text, 1)}</div>')
    parts += [BLOCKS[k](data, day, units) for k in CFG.ORDER if k in shown]
    return R.page_html(R.frame("".join(parts), day.strftime("%a, %b %-d"), R.streak_of(data, day), R.foot_time(day, "Overview"), fixed=False))


# ----------------------------------------------------------------- detail ----
def d_workouts(data, day, units, coach_text=None):
    w = workouts_info(data, day)
    c = SOLID["workouts"]
    sub = f'<span class="lab">{w["n"]} of {w["planned"]} planned this week</span>' if w["planned"] else '<span class="lab">this week</span>'
    h = hero_value("Sessions this week", str(w["n"]), f'of {w["planned"]}' if w["planned"] else "", "workouts", w["n"] / w["planned"] if w["planned"] else 0, "dumbbell", sub)
    strip = []
    for d in w["days"]:
        m = minutes(data, d)
        on = m > 0 or d in w["active"]
        strip.append(f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:{SP["s"]}px"><span class="sm" style="{"color:" + TEXT + ";font-weight:700" if d == day else ""}">{DAYL[d.weekday()]}</span>'
                     f'<div style="width:32px;height:32px;border-radius:16px;box-sizing:border-box;background:{c if on else "transparent"};border:2px solid {c if on else ink(.22)};display:flex;align-items:center;justify-content:center">'
                     f'{icon("check", 16, ON_ACCENT, 3) if on else ""}</div><span class="sm" style="color:{TEXT2}">{f"{m:.0f}" if m else ""}&nbsp;</span></div>')
    avg = w["minutes"] / w["n"] if w["n"] else 0
    st = stats(("Minutes", f'{w["minutes"]:.0f}', "min"), ("Estimated burn", R.fmt(w["kcal"]), "kcal"), ("Average session", f"{avg:.0f}", "min"))
    weeks = [[day - dt.timedelta(7 * k + i) for i in range(6, -1, -1)] for k in range(7, -1, -1)]
    wm = [sum(minutes(data, d) for d in wk) for wk in weeks]
    labels = [wk[-1].strftime("%b %-d") if i in (0, 4, 7) else "" for i, wk in enumerate(weeks)]
    ch = cols_svg(wm, [l for l in labels], "workouts", ref=None, value_fmt=lambda v: f"{v:.0f}")
    recent = []
    for d in [day - dt.timedelta(i) for i in range(0, 28)]:
        for s in data.workout_sessions(d):
            recent.append((d, s))
    rows = "".join(list_row(d.strftime("%b %-d"), (s.get("name") or s.get("type") or "Workout").strip(),
                            f'<span class="disp" style="font-size:20px">{C_num(s.get("duration_min")):.0f}</span><span class="lab"> min</span>'
                            + (f'<span class="lab" style="margin-left:12px">{C_num(s.get("est_kcal")):.0f} kcal</span>' if s.get("est_kcal") else ""),
                            (s.get("type") or "").strip().capitalize() or None) for d, s in recent[:7])
    line = coach_text or f'{w["n"]} of {w["planned"]} sessions done this week.' if w["planned"] else ""
    body = (f'{nav("workouts")}{h}{st}{sec("This week")}<div style="display:flex;gap:{SP["xs"]}px;margin-top:{SP["m"]}px">{"".join(strip)}</div>'
            f'{sec("Minutes per week, last 8 weeks")}<div style="margin-top:{SP["m"]}px">{ch}</div>{sec("Recent sessions")}'
            f'<div style="margin-top:{SP["s"]}px;border-top:1px solid {HAIR}">{rows}</div>')
    return wrap(day, data, body, "Workouts")


def d_nutrition(data, day, units, coach_text=None):
    t, f, _, _ = R.day_ctx(data, day)
    left = t["calories"] - f["cal"]
    frac = f["cal"] / t["calories"] if t["calories"] else 0
    sub = f'<span class="lab">{R.fmt(f["cal"])} of {R.fmt(t["calories"])} kcal eaten</span>'
    h = hero_value("Calories left" if left >= 0 else "Calories over", R.fmt(abs(left)), "kcal", "nutrition", frac, "utensils", sub)
    mac = "".join(R.row(ic, "nutrition", name, R.fmt(f[k]), f'/ {R.fmt(t[tk])} g', min(100, round(100 * f[k] / t[tk])) if t[tk] else None)
                  for ic, name, k, tk in (("beef", "Protein", "p", "protein_g"), ("wheat", "Carbs", "c", "carbs_g"), ("nut", "Fat", "f", "fat_g"))
                  )
    if t.get("fiber_g"):
        mac += R.row("wheat", "nutrition", "Fiber", R.fmt(f["fib"]), f'/ {R.fmt(t["fiber_g"])} g', min(100, round(100 * f["fib"] / t["fiber_g"])))
    meals = []
    order = [m for m in ("breakfast", "lunch", "dinner", "snack") if f["meals"].get(m)] + [m for m in f["meals"] if m not in ("breakfast", "lunch", "dinner", "snack")]
    tot = max(sum(f["meals"].values()), 1)
    for m in order:
        v = f["meals"][m]
        meals.append(f'<div style="display:flex;align-items:center;gap:{SP["m"]}px;height:40px"><span style="width:92px;flex:none;font-size:16px;font-weight:500">{m.capitalize()}</span>'
                     f'<div style="flex:1;height:8px;border-radius:4px;background:{HAIR}"><div style="height:8px;width:{v / tot * 100:.0f}%;border-radius:4px;background:{SOLID["nutrition"]}"></div></div>'
                     f'<span style="width:84px;text-align:right;white-space:nowrap"><span class="disp" style="font-size:20px">{R.fmt(v)}</span><span class="lab"> kcal</span></span></div>')
    days = week_days(day)
    cal = [data.food[d]["cal"] if d in data.food else None for d in days]
    ch = cols_svg(cal, [DAYL[d.weekday()] for d in days], "nutrition", ref=t["calories"], ref_label=f'Target {R.fmt(t["calories"])}')
    lg = [d for d in days if S.logged(data, d)]
    avg_c = S.avg([data.food[d]["cal"] for d in lg])
    avg_p = S.avg([data.food[d]["p"] for d in lg])
    hit = sum(1 for d in lg if data.food[d]["p"] >= 0.9 * data.target(d)["protein_g"])
    st = stats(("Average intake", R.fmt(avg_c) if avg_c else "\u2013", "kcal"), ("Average protein", R.fmt(avg_p) if avg_p else "\u2013", "g"), ("Protein days", f"{hit}/{len(lg)}", ""))
    body = (f'{nav("nutrition")}{h}{sec("Macros today")}<div style="margin-top:{SP["s"]}px;border-top:1px solid {HAIR}">{mac}</div>'
            + (f'{sec("By meal")}<div style="margin-top:{SP["s"]}px">{"".join(meals)}</div>' if meals else "")
            + f'{sec("Calories, last 7 days")}<div style="margin-top:{SP["m"]}px">{ch}</div>{st}')
    return wrap(day, data, body, "Diet and macros")


def d_activity(data, day, units, coach_text=None):
    t = data.target(day)
    goal = t["step_goal"]
    steps = data.steps.get(day, 0)
    pct = round(100 * steps / goal) if goal else 0
    h = hero_value("Steps today", R.fmt(steps) if steps else "\u2013", "", "activity", steps / goal if goal else 0, "footprints",
                   f'<span class="lab">{pct}% of your {R.fmt(goal)} goal</span>')
    days = week_days(day)
    vals = [data.steps.get(d) for d in days]
    ch7 = cols_svg(vals, [DAYL[d.weekday()] for d in days], "activity", ref=goal, ref_label=f"Goal {R.fmt(goal)}")
    d30 = week_days(day, 30)
    v30 = [data.steps.get(d) for d in d30]
    ch30 = cols_svg(v30, [d.strftime("%b %-d") if i in (0, 15, 29) else "" for i, d in enumerate(d30)], "activity", ref=goal, ref_label="", h=120)
    got = [v for v in v30 if v]
    hit = sum(1 for v in got if goal and v >= goal)
    cardio = sum(C_num(s.get("duration_min")) for d in days for s in data.workouts.get(d, []) if (s.get("type") or "").strip().lower() in ("walk", "cardio"))
    st = stats(("30-day average", R.fmt(S.avg(got)) if got else "\u2013", "steps"), ("Goal days", f"{hit}/{len(got)}", ""), ("Best day", R.fmt(max(got)) if got else "\u2013", ""))
    extra = (f'<div class="lab" style="margin-top:{SP["m"]}px">{cardio:.0f} walking and cardio minutes this week</div>') if cardio else ""
    body = (f'{nav("activity")}{h}{sec("Last 7 days")}<div style="margin-top:{SP["m"]}px">{ch7}</div>{extra}{st}'
            f'{sec("Last 30 days")}<div style="margin-top:{SP["m"]}px">{ch30}</div>')
    return wrap(day, data, body, "Steps and activity")


def d_health(data, day, units, coach_text=None):
    t = data.target(day)
    p = S.pillars(data, day)
    rec = p["recovery"]
    dl = R.vs_avg(data, day, "recovery")
    parts = [nav("health")]
    if rec is not None:
        parts.append(f'<div style="margin-top:{SP["m"]}px">{R.hero("Recovery", rec, "recovery", S.state_word(rec), R.delta(dl, "vs 7-day avg", True) if dl is not None else "", None)}</div>')
        parts.append(f'<div style="margin-top:{SP["m"]}px">{R.coach(coach_text if coach_text is not None else S.coach_line(data, day, "daily", units))}</div>')
    days = week_days(day)
    # sleep
    sl = [data.sleep.get(d) for d in days]
    if any(v is not None for v in sl):
        got = [v for v in sl if v is not None]
        parts.append(f'{sec("Sleep")}<div style="display:flex;align-items:baseline;gap:8px;margin-top:{SP["s"]}px"><span class="disp" style="font-size:44px">{sl[-1]:.1f}</span><span class="lab">h last night</span>'
                     f'<span class="lab" style="margin-left:auto">{S.avg(got):.1f} h average</span></div>'
                     f'<div style="margin-top:{SP["m"]}px">{cols_svg(sl, [DAYL[d.weekday()] for d in days], "sleep", ref=t["sleep_goal_h"], ref_label=f"Goal {t["sleep_goal_h"]:g} h", value_fmt=lambda v: f"{v:.1f}") if sl[-1] else cols_svg(sl, [DAYL[d.weekday()] for d in days], "sleep", ref=t["sleep_goal_h"], ref_label=f"Goal {t["sleep_goal_h"]:g} h", value_fmt=lambda v: f"{v:.1f}")}</div>')
    # weight
    wsvg, winfo = R.weight_svg(data, day, units, 28, INNER, 152, t["goal_weight_kg"], xticks=2, extremes=False, compact=True, top_pad=16, bottom_pad=28, goal_label=False)
    if winfo:
        wd = winfo["last"] - winfo["first"]
        parts.append(f'{sec("Weight, last 28 days")}<div style="display:flex;align-items:baseline;gap:8px;margin-top:{SP["s"]}px"><span class="disp" style="font-size:44px">{winfo["last"]:.1f}</span><span class="lab">{units.w}, 7-day average</span>'
                     f'<span class="lab" style="margin-left:auto">{R.sgn(wd)} {units.w}</span></div><div style="margin-top:{SP["m"]}px">{wsvg}</div>')
    # water
    wv = [data.water.get(d) for d in days]
    if any(v for v in wv):
        conv = (lambda v: v / 29.5735) if units.imp else (lambda v: v / 1000)
        wl = [conv(v) if v else None for v in wv]
        parts.append(f'{sec("Water, last 7 days")}<div style="display:flex;align-items:baseline;gap:8px;margin-top:{SP["s"]}px"><span class="disp" style="font-size:44px">{R.water_txt(units, wv[-1] or 0)}</span>'
                     f'<span class="lab">{R.water_unit(units)} today</span></div>'
                     f'<div style="margin-top:{SP["m"]}px">{cols_svg(wl, [DAYL[d.weekday()] for d in days], "hydration", ref=conv(t["water_ml"]), ref_label=f"Goal {R.water_txt(units, t["water_ml"])} {R.water_unit(units)}", value_fmt=lambda v: f"{v:.0f}" if units.imp else f"{v:.1f}")}</div>')
    return wrap(day, data, "".join(parts), "Health")


def d_peptides(data, day, units, coach_text=None, window=30, compound=None):
    return RM.treatment_html(data, day, units, window, compound, coach_text)


DETAIL = dict(workouts=d_workouts, nutrition=d_nutrition, activity=d_activity, health=d_health, peptides=d_peptides)

import charts as C  # noqa: E402  (rolling_weight and Data live there; imported last to avoid a cycle)
