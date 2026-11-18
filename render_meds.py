"""Peptides and meds visuals for Grok Life: the peptides detail page (the old Treatment image) and the overview sparkline.

Same system as render.py: Barlow Condensed + Hanken Grotesk, the 4/8/16/24/32 spacing scale, hairline rows, flat colours, no glow.
Medication has its own pillar hue (SOLID["medication"]). Everything shown is an ESTIMATE from published half-lives.
"""
import datetime as dt
import math

import meds as M
from render_core import *  # noqa
import render as R


def default_now(day):
    return dt.datetime.now() if day == dt.date.today() else dt.datetime.combine(day, dt.time(23, 59))


def fmt_when(t, now=None):
    """'Mon, Nov 16, 7:30 pm'."""
    return t.strftime("%a, %b %-d, %-I:%M %p").replace("AM", "am").replace("PM", "pm")


def short_time(t):
    return t.strftime("%-I:%M %p").replace("AM", "am").replace("PM", "pm")


# ------------------------------------------------------------------ chart ----
def curve(st, window, now=None, points=220):
    """Window domain and sampled level curve: (t0, t1, past, future, extra_doses).
    The future part assumes the schedule is kept (same mg at the same interval)."""
    now = now or st["now"]
    ka, ke = st["ka"], st["ke"]
    nxt = st["next"]["t"]
    to_next = (nxt - now).total_seconds() / 86400
    fut = max(window * 0.2, min(window * 0.5, to_next + 1))
    t0, t1 = now - dt.timedelta(days=window - fut), now + dt.timedelta(days=fut)
    past_doses = [d for d in st["doses"] if d["t"] <= now]
    if past_doses:  # a new user's first weeks: start the axis just before the first dose instead of drawing a month of flat zero
        t0 = max(t0, min(min(d["t"] for d in past_doses) - dt.timedelta(days=3), now - dt.timedelta(days=7)))
    iv = dt.timedelta(days=st["interval_days"])
    extra, t = [], nxt
    while st["scheduled"] and t <= t1:  # no schedule given: project the decay only, never invent future doses
        extra.append(dict(t=t, mg=st["last"]["mg"]))
        t += iv
    step = max(0.5, window * 24 / points)
    past = M.series(past_doses, t0, now, ka, ke, step) + [(now, M.level_at(past_doses, now, ka, ke))]
    futs = [(now, past[-1][1])] + M.series(past_doses, now + dt.timedelta(hours=step), t1, ka, ke, step, extra)
    return t0, t1, past, futs, extra


def level_svg(st, window, w=432, h=216, now=None):
    """Estimated level curve: solid filled past, dashed projection if the schedule is kept, now-dot with callout, date axis."""
    c = SOLID["medication"]
    now = now or st["now"]
    t0, t1, past, futs, extra = curve(st, window, now)
    past_doses = [d for d in st["doses"] if d["t"] <= now]
    ymax = max([v for _, v in past + futs] + [0.01]) * 1.22
    ticks = R.nice_ticks(0, ymax * 0.92, 4)
    ymax = max(ymax, ticks[-1] * 1.08)
    L, B, T = 32, 28, 44
    px = lambda tt: L + (w - L) * ((tt - t0).total_seconds() / (t1 - t0).total_seconds())  # noqa: E731
    py = lambda v: T + (h - T - B) * (1 - v / ymax)  # noqa: E731
    base = py(0)
    pp = " ".join(f'{"M" if i == 0 else "L"}{px(tt):.1f} {py(v):.1f}' for i, (tt, v) in enumerate(past))
    fp = " ".join(f'{"M" if i == 0 else "L"}{px(tt):.1f} {py(v):.1f}' for i, (tt, v) in enumerate(futs))
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><linearGradient id="lv" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{c}" stop-opacity=".30"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient></defs>']
    for v in ticks:
        lab = f"{v:g}"
        s.append(f'<line x1="{L}" x2="{w}" y1="{py(v):.1f}" y2="{py(v):.1f}" stroke="{TEXT}" stroke-opacity="{.16 if v == 0 else .08}"/>'
                 f'<text x="{L - 8}" y="{py(v) + 4:.1f}" text-anchor="end" font-size="12" fill="{TEXT3}">{lab}</text>')
    xn = px(now)
    s.append(f'<path d="{pp} L{xn:.1f} {base:.1f} L{px(past[0][0]):.1f} {base:.1f} Z" fill="url(#lv)"/>')
    s.append(f'<path d="{fp}" fill="none" stroke="{c}" stroke-width="2.5" stroke-dasharray="7 6" stroke-linecap="round"/>')
    s.append(f'<path d="{pp}" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    for d in past_doses:   # dose ticks on the axis
        if t0 <= d["t"] <= now:
            s.append(f'<line x1="{px(d["t"]):.1f}" x2="{px(d["t"]):.1f}" y1="{base:.1f}" y2="{base - 8:.1f}" stroke="{c}" stroke-width="2" stroke-linecap="round"/>')
    for d in extra:
        s.append(f'<line x1="{px(d["t"]):.1f}" x2="{px(d["t"]):.1f}" y1="{base:.1f}" y2="{base - 8:.1f}" stroke="{c}" stroke-opacity=".55" stroke-width="2" stroke-dasharray="2 3" stroke-linecap="round"/>')
    cur = past[-1][1]
    yn = py(cur)
    s.append(f'<line x1="{xn:.1f}" x2="{xn:.1f}" y1="{yn:.1f}" y2="{base:.1f}" stroke="{TEXT}" stroke-opacity=".28" stroke-dasharray="2 4"/>')
    s.append(f'<circle cx="{xn:.1f}" cy="{yn:.1f}" r="6.5" fill="{c}" stroke="{BG}" stroke-width="2.5"/>')
    rising = len(past_doses) <= 1 and max(v for _, v in futs) > cur * 1.03  # first dose only: the dashed curve climbs right of the dot, keep the label on its left
    anchor = "end" if (xn > w - 84 or rising) else ("start" if xn < L + 60 else "middle")
    cx = xn + (-12 if rising and anchor == "end" and xn <= w - 84 else 8 if anchor == "end" else -8 if anchor == "start" else 0)
    cy = max(yn - (14 if rising else 36), 18)
    s.append(f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="{anchor}" font-size="22" font-weight="600" fill="{TEXT}" style="font-family:\'SwDisplay\',sans-serif;font-stretch:100%">{cur:.2f} mg</text>'
             f'<text x="{cx:.1f}" y="{cy + 16:.1f}" text-anchor="{anchor}" font-size="12" fill="{TEXT2}">Now, {short_time(now)}</text>')
    d0 = dt.datetime.combine(t0.date() + dt.timedelta(days=1), dt.time(0, 0))
    stepd = max(1, math.ceil(window / 4))
    tt = d0
    while tt <= t1:
        x = px(tt)
        if 24 <= x <= w - 24 and abs(x - xn) > 36:
            s.append(f'<text x="{x:.1f}" y="{h - 4}" text-anchor="middle" font-size="12" fill="{TEXT3}">{tt.strftime("%b %-d")}</text>')
        tt += dt.timedelta(days=stepd)
    s.append("</svg>")
    return "".join(s)


def cadence(days):
    return "weekly" if days == 7 else "daily" if days == 1 else f"every {days:g} days"


def spark(st, w=176, h=64, window=30):
    """Small level curve for the overview: solid past, dashed projection, now-dot. No axes, no labels."""
    c = SOLID["medication"]
    t0, t1, past, futs, extra = curve(st, window, None, points=90)
    ymax = max(v for _, v in past + futs) * 1.12 or 1
    span = (t1 - t0).total_seconds()
    px = lambda t: 3 + (w - 6) * (t - t0).total_seconds() / span  # noqa: E731
    py = lambda v: 4 + (h - 8) * (1 - v / ymax)  # noqa: E731
    line = lambda pts: " ".join(f'{"M" if i == 0 else "L"}{px(t):.1f} {py(v):.1f}' for i, (t, v) in enumerate(pts))  # noqa: E731
    nx, ny = px(past[-1][0]), py(past[-1][1])
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><path d="{line(past)} L{nx:.1f} {h - 4} L{px(past[0][0]):.1f} {h - 4} Z" fill="{c}" fill-opacity=".14"/>'
            f'<path d="{line(past)}" fill="none" stroke="{c}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<path d="{line(futs)}" fill="none" stroke="{c}" stroke-width="2.5" stroke-dasharray="4 5" stroke-linecap="round"/>'
            f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="4.5" fill="{c}" stroke="{BG}" stroke-width="2"/></svg>')


def toggle(active):
    seg = "".join(
        f'<span style="display:inline-flex;align-items:center;justify-content:center;width:44px;height:32px;border-radius:8px;font-size:14px;font-weight:600;'
        f'{"background:" + ink(.12) + ";color:" + TEXT if d == active else "color:" + TEXT2}">{d}d</span>' for d in (7, 30, 90))
    return f'<div style="display:inline-flex;gap:0;padding:0;border-radius:8px;background:{ink(.06)}">{seg}</div>'


# --------------------------------------------------------------- body map ----
SITE_XY = {"abdomen_ul": (94, 116), "abdomen_ur": (66, 116), "abdomen_ll": (94, 142), "abdomen_lr": (66, 142),
           "thigh_l": (97, 214), "thigh_r": (63, 214), "arm_l": (129, 94), "arm_r": (31, 94)}


def body_map(last_site, next_site, used, scale=0.82):
    """Front view, drawn facing the viewer, so the person's left is on the right of the picture. Last site filled, next suggested dashed."""
    c = SOLID["medication"]
    ol, fl = ink(.34), SURFACE
    parts = [f'<rect x="47" y="170" width="32" height="118" rx="16" fill="{fl}" stroke="{ol}" stroke-width="1.5"/>',
             f'<rect x="81" y="170" width="32" height="118" rx="16" fill="{fl}" stroke="{ol}" stroke-width="1.5"/>',
             f'<rect x="-10" y="0" width="20" height="104" rx="10" transform="translate(38 62) rotate(8)" fill="{fl}" stroke="{ol}" stroke-width="1.5"/>',
             f'<rect x="-10" y="0" width="20" height="104" rx="10" transform="translate(122 62) rotate(-8)" fill="{fl}" stroke="{ol}" stroke-width="1.5"/>',
             f'<path d="M46 56 Q46 50 56 49 L104 49 Q114 50 114 56 L118 118 Q119 138 110 152 L108 178 Q80 186 52 178 L50 152 Q41 138 42 118 Z" fill="{fl}" stroke="{ol}" stroke-width="1.5"/>',
             f'<rect x="72" y="36" width="16" height="16" rx="7" fill="{fl}" stroke="{ol}" stroke-width="1.5"/>',
             f'<circle cx="80" cy="22" r="17" fill="{fl}" stroke="{ol}" stroke-width="1.5"/>',
             f'<circle cx="80" cy="129" r="1.8" fill="{ol}"/>',
             f'<text x="4" y="20" font-size="12" font-weight="600" fill="{TEXT3}">R</text><text x="156" y="20" text-anchor="end" font-size="12" font-weight="600" fill="{TEXT3}">L</text>']
    for k, (x, y) in SITE_XY.items():
        used_here = k in used
        parts.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{TEXT}" fill-opacity="{.30 if used_here else .14}"/>')
    if next_site in SITE_XY:
        x, y = SITE_XY[next_site]
        parts.append(f'<circle cx="{x}" cy="{y}" r="10" fill="none" stroke="{c}" stroke-width="2" stroke-dasharray="3 3"/><circle cx="{x}" cy="{y}" r="2.5" fill="{c}"/>')
    if last_site in SITE_XY:
        x, y = SITE_XY[last_site]
        parts.append(f'<circle cx="{x}" cy="{y}" r="13" fill="none" stroke="{c}" stroke-opacity=".4" stroke-width="2"/><circle cx="{x}" cy="{y}" r="7" fill="{c}"/>')
    return f'<svg width="{160 * scale:.0f}" height="{292 * scale:.0f}" viewBox="0 0 160 292">{"".join(parts)}</svg>'


# ------------------------------------------------------------- side effects ----
def effect_row(e):
    c = SOLID["medication"]
    v = e["latest"]
    frac = 0 if v is None else v / 10
    val = f'<span class="disp" style="font-size:20px">{v:.0f}</span><span class="sm" style="margin-left:2px">/10</span>' if v is not None else f'<span class="disp" style="font-size:20px;color:{TEXT3}">\u2013</span>'
    tr = ""
    if e["avg"] is not None and e["prev"] is not None:
        d = e["avg"] - e["prev"]
        if abs(d) >= 0.5:
            col = GOOD if d < 0 else TEXT2   # a falling side effect is the good direction
            tr = (f'<span style="display:inline-flex;align-items:center;gap:2px;font-size:14px;font-weight:600;color:{col}">'
                  f'{icon("arrow-up" if d > 0 else "arrow-down", 14, col, 2.4)}{abs(d):.0f}</span>')
    return (f'<div style="display:flex;align-items:center;gap:{SP["m"]}px;height:44px;flex:none">'
            f'<span style="width:140px;flex:none;font-size:16px;line-height:24px;font-weight:500;white-space:nowrap">{e["label"]}</span>'
            f'<div style="flex:1;height:8px;border-radius:4px;background:{ink(.10)}"><div style="height:8px;width:{frac * 100:.0f}%;border-radius:4px;background:{c}"></div></div>'
            f'<div style="width:48px;text-align:right;white-space:nowrap">{val}</div><div style="width:32px;display:flex;justify-content:flex-end">{tr}</div></div>')


# -------------------------------------------------------------- treatment ----
def treatment_html(data, day, units, window=30, compound=None, coach_text=None, now=None):
    now = now or default_now(day)
    st = M.status(data.root, now, compound)
    if not st:
        return None
    c = SOLID["medication"]
    eff = M.effects_summary(data.root, now)
    line = coach_text if coach_text is not None else M.treatment_line(st, eff, data, now)
    last, nxt = st["last"], st["next"]
    size = 96
    nh = round(size * .78)
    sub = f'{st["brand"]} \u00b7 ' if st["brand"] else ""
    top = (f'<div style="display:flex;justify-content:space-between;align-items:center;height:32px"><div style="display:flex;align-items:baseline;gap:8px">'
           f'<span style="font-size:20px;line-height:24px;font-weight:600">{st["label"]}</span><span class="lab">{sub}{last["mg"]:g} mg{(" " + cadence(st["interval_days"])) if st["scheduled"] else ""}</span></div>'
           f'{toggle(window)}</div>')
    hero = (f'<div class="lab" style="height:20px;margin-top:{SP["m"]}px">Estimated level now</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-top:{SP["s"]}px;height:{nh}px"><span class="hero" style="font-size:{size}px;line-height:{nh}px;color:{TEXT}">{st["level_now"]:.2f}</span>'
            f'<span class="disp" style="font-size:28px;color:{TEXT2};font-weight:600">mg</span></div>')
    chart = f'<div style="margin-top:{SP["m"]}px">{level_svg(st, window, now=now)}</div>'
    legend = (f'<div class="sm" style="display:flex;gap:{SP["m"]}px;margin-top:{SP["s"]}px;color:{TEXT2}"><span>Solid: estimated so far</span><span>{"Dashed: if the schedule is kept" if st["scheduled"] else "Dashed: fading, if no further dose"}</span></div>')
    stats = "" if not st["scheduled"] else (f'<div style="display:flex;gap:{SP["m"]}px;margin-top:{SP["m"]}px">'
             f'{R.stat_col("At next dose", f"{st["level_next"]:.2f}", "mg")}{R.stat_col("Steady-state high", f"{st["ss_peak"]:.1f}", "mg")}'
             f'{R.stat_col("Steady-state low", f"{st["ss_trough"]:.1f}", "mg")}</div>')
    # last dose and next dose
    prog = nxt["elapsed"] if not nxt["overdue"] else 1.0
    ring_inner = (f'<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                  f'<span class="disp" style="font-size:{26 if len(nxt["countdown"]) > 5 else 30}px;white-space:nowrap">{nxt["countdown"]}</span></div>')
    left = (f'<div style="flex:1;min-width:0"><div class="lab" style="height:20px">Last dose</div>'
            f'<div style="display:flex;align-items:baseline;gap:4px;margin-top:{SP["s"]}px"><span class="hero" style="font-size:64px;line-height:50px;height:50px">{last["mg"]:g}</span>'
            f'<span class="disp" style="font-size:24px;color:{TEXT2};font-weight:600">mg</span></div>'
            f'<div style="margin-top:{SP["m"]}px;font-size:16px;line-height:24px;font-weight:500">{st["label"]}{(", " + st["brand"]) if st["brand"] else ""}</div>'
            f'<div class="lab">{fmt_when(last["t"])}</div>'
            f'<div class="lab">{last["site_label"] or "Site not logged"}</div></div>')
    panel = f'<div style="width:176px;flex:none;padding-left:{SP["l"]}px;border-left:1px solid {HAIR}"><div class="lab" style="height:20px">Next dose</div>'
    if st["scheduled"]:
        right = (f'{panel}<div style="position:relative;width:112px;height:112px;margin-top:{SP["s"]}px">{ring(112, 12, prog, "medication")}{ring_inner}</div>'
                 f'<div style="margin-top:{SP["m"]}px;font-size:16px;line-height:24px;font-weight:500">{nxt["t"].strftime("%a, %b %-d")}</div>'
                 f'<div class="lab">{short_time(nxt["t"])}</div></div>')
    else:  # no schedule given: no date, no countdown, just a calm empty ring and what to do about it
        right = (f'{panel}<div style="position:relative;width:112px;height:112px;margin-top:{SP["s"]}px">{ring(112, 12, 0, "medication")}'
                 f'<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center"><span class="disp" style="font-size:30px;color:{TEXT3}">\u2013</span></div></div>'
                 f'<div style="margin-top:{SP["m"]}px;font-size:16px;line-height:24px;font-weight:500">Not set yet</div>'
                 f'<div class="lab">Tell me your schedule</div></div>')
    dose_block = f'<div style="display:flex;margin-top:{SP["xl"]}px;padding-top:{SP["l"]}px;border-top:1px solid {HAIR}">{left}{right}</div>'
    # injection site
    used = {d["site"] for d in st["all_doses"][-8:]}
    recent = "".join(f'<div style="display:flex;justify-content:space-between;height:24px;font-size:14px;line-height:24px"><span class="lab">{d["t"].strftime("%b %-d")}</span>'
                     f'<span>{M.SITE_LABEL.get(d["site"], "Not logged")}</span></div>' for d in reversed(st["all_doses"][-4:]))
    site_txt = (f'<div style="flex:1;min-width:0;padding-left:{SP["l"]}px"><div class="lab">Last site</div>'
                f'<div style="display:flex;align-items:center;gap:8px;font-size:18px;line-height:24px;font-weight:600"><span style="width:10px;height:10px;border-radius:5px;background:{c}"></span>{last["site_label"] or "Not logged"}</div>'
                f'<div class="lab" style="margin-top:{SP["m"]}px">Suggested next</div>'
                f'<div style="display:flex;align-items:center;gap:8px;font-size:18px;line-height:24px;font-weight:600"><span style="width:10px;height:10px;border-radius:5px;border:2px dashed {c}"></span>{st["next_site_label"]}</div>'
                f'<div style="margin-top:{SP["l"]}px;border-top:1px solid {HAIR};padding-top:{SP["s"]}px">{recent}</div></div>')
    sites = (f'{R.section_label("Injection site")}<div style="display:flex;margin-top:{SP["m"]}px">{body_map(last["site"], st["next_site"], used)}{site_txt}</div>'
             f'<div class="sm" style="margin-top:{SP["s"]}px;color:{TEXT2}">Left and right are yours. Rotating sites is a suggestion from the usual label advice.</div>')
    effs = (f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:{SP["xl"]}px"><span class="lab">Side effects</span>'
            f'<span class="sm" style="color:{TEXT2}">{"Arrows: this week against last" if any(e["avg"] is not None and e["prev"] is not None and abs(e["avg"] - e["prev"]) >= 0.5 for e in eff) else "Latest rating, 0 to 10"}</span></div>'
            f'<div style="margin-top:{SP["s"]}px;border-top:1px solid {HAIR}">{"".join(effect_row(e) for e in eff)}</div>')
    import render_modules as RMOD
    body = (f'{RMOD.nav("peptides")}<div style="margin-top:{SP["m"]}px">{top}</div>{hero}{chart}{legend}{stats}<div style="margin-top:{SP["l"]}px">{R.coach(line)}</div>{dose_block}{sites}{effs}')
    return page_html(R.frame(body, day.strftime("%a, %b %-d"), R.streak_of(data, day), R.foot_time(day, "Peptides and meds") + " \u00b7 Estimated", fixed=False))
