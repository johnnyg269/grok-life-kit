#!/usr/bin/env python3
"""Grok Life charts. Reads CSVs from a data dir (default /workspace/macro-coach)
and writes phone-friendly PNGs (1080 px wide).

Usage:
  python charts.py overview [--date YYYY-MM-DD]       # the single home screen: one block per module that is on
  python charts.py detail [MODULE]                     # full page for workouts | nutrition | activity | health | peptides
                                                       #   (no MODULE = every module that is shown)
  python charts.py eod     [--date YYYY-MM-DD]         # end-of-day recap (modules that are on)
  python charts.py weekly  [--date YYYY-MM-DD]         # 7 days ending at date
  python charts.py monthly [--date YYYY-MM-DD]         # 30 days ending at date
  python charts.py weight  [--days N]                  # weight chart only
  python charts.py all                                 # overview, every detail page, eod, weekly, monthly
  (daily = overview and treatment = detail peptides, kept as aliases)
Options: --data DIR  --out DIR (default DATA/charts)  --units auto|imperial|metric
         --theme light|dark   (default: the saved preference in DATA/config.json, else light)
         --palette NAME       (default: the saved one, else lagoon)
         --window 7|30|90 --compound NAME   (peptides detail)
Modules come from DATA/config.json (python config.py); a module that is off, or on with no data yet, is not drawn.
Prints one PNG path per line, then a JSON summary line (prefixed SUMMARY:).
Needs headless Chromium for overview, detail, themes and module gating. Without it only the basic matplotlib
fallback below runs (eod, weekly, monthly, weight; light only, no module gating).
CSV schemas are documented in SKILL.md. Missing files are treated as empty.
"""
import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:  # matplotlib is only needed for the no-Chromium fallback drawing code
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: E402
    from matplotlib.patches import FancyBboxPatch, Wedge  # noqa: E402
except ImportError:
    plt = None

DEFAULT_DATA = Path("/workspace/macro-coach")

# One color per metric, used everywhere.
BG, INK, MUTED, TRACK, PANEL = "#FFFFFF", "#111827", "#6B7280", "#E5E7EB", "#F9FAFB"
GOOD, BAD = "#16A34A", "#DC2626"
C = dict(cal="#F97316", protein="#2563EB", carbs="#EAB308", fat="#A855F7",
         fiber="#16A34A", water="#06B6D4", weight="#0F766E", sleep="#6366F1",
         steps="#84CC16", workout="#EF4444", measure="#64748B")
DPI, WIDTH_IN = 180, 6.0

DEFAULT_TARGETS = dict(units="imperial", calories=2000, protein_g=150, carbs_g=200,
                       fat_g=65, fiber_g=30, water_ml=2500, goal_weight_kg=None,
                       goal_type="maintain", step_goal=8000, sleep_goal_h=7.5,
                       sessions_per_week=3)

# ----------------------------------------------------------------- data ----

def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v, default=None):
    try:
        s = str(v).strip()
        return float(s) if s else default
    except (TypeError, ValueError):
        return default


def pdate(s):
    try:
        return dt.date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return None


class Data:
    def __init__(self, root):
        self.root = Path(root)
        r = lambda n: read_csv(self.root / n)  # noqa: E731
        self.food = {}
        for row in r("food_log.csv"):
            d = pdate(row.get("date"))
            if not d:
                continue
            a = self.food.setdefault(d, dict(cal=0, p=0, c=0, f=0, fib=0, n=0, meals={}))
            cal = num(row.get("calories"), 0)
            a["cal"] += cal
            a["p"] += num(row.get("protein_g"), 0)
            a["c"] += num(row.get("carbs_g"), 0)
            a["f"] += num(row.get("fat_g"), 0)
            a["fib"] += num(row.get("fiber_g"), 0)
            a["n"] += 1
            m = (row.get("meal") or "snack").strip().lower() or "snack"
            a["meals"][m] = a["meals"].get(m, 0) + cal
        self.water = {}
        for row in r("water.csv"):
            d = pdate(row.get("date"))
            if d:
                self.water[d] = self.water.get(d, 0) + num(row.get("ml"), 0)
        self.weight = {}
        for row in r("weight.csv"):  # last entry of a day wins
            d, w = pdate(row.get("date")), num(row.get("weight_kg"))
            if d and w:
                self.weight[d] = w
        self.workouts = {}
        for row in r("workouts.csv"):
            d = pdate(row.get("date"))
            if d:
                self.workouts.setdefault(d, []).append(row)
        self.sleep = {}
        for row in r("sleep.csv"):
            d, h = pdate(row.get("date")), num(row.get("hours"))
            if d and h is not None:
                self.sleep[d] = h
        self.steps = {}
        for row in r("steps.csv"):
            d, s = pdate(row.get("date")), num(row.get("steps"))
            if d and s is not None:
                self.steps[d] = s
        self.measure = sorted(
            [(pdate(x.get("date")), x) for x in r("measurements.csv") if pdate(x.get("date"))],
            key=lambda t: t[0])
        self.targets = sorted(
            [(pdate(x.get("effective_date")), x) for x in r("targets.csv") if pdate(x.get("effective_date"))],
            key=lambda t: t[0])

    def target(self, day):
        t = dict(DEFAULT_TARGETS)
        row = None
        for d, x in self.targets:
            if d <= day or row is None:
                row = x
            if d > day:
                break
        if row:
            for k in t:
                v = row.get(k)
                if v is None or str(v).strip() == "":
                    continue
                t[k] = str(v).strip() if k in ("units", "goal_type") else num(v, t[k])
        else:
            print("warning: no targets.csv, using placeholder targets", file=sys.stderr)
        return t

    def workout_sessions(self, d):
        # walks are covered by steps, so they don't count as sessions
        return [w for w in self.workouts.get(d, []) if (w.get("type") or "").strip().lower() != "walk"]


class Units:
    def __init__(self, imperial):
        self.imp = imperial
        self.w = "lb" if imperial else "kg"
        self.l = "in" if imperial else "cm"

    def wt(self, kg):
        return kg * 2.20462 if self.imp else kg

    def wt_s(self, kg, signed=False):
        v = self.wt(kg)
        return (f"{v:+.1f}" if signed else f"{v:.1f}") + f" {self.w}"

    def ln(self, cm):
        return cm / 2.54 if self.imp else cm

    def water_s(self, ml):
        return f"{ml / 29.5735:,.0f} oz" if self.imp else f"{ml / 1000:.1f} L"


def pick_units(data, arg, day):
    if arg in ("imperial", "metric"):
        return Units(arg == "imperial")
    return Units(data.target(day)["units"].lower() != "metric")


def rolling_weight(weights, days, window=7):
    out = {}
    for d in days:
        vals = [weights[x] for x in (d - dt.timedelta(k) for k in range(window)) if x in weights]
        if vals:
            out[d] = sum(vals) / len(vals)
    return out

# --------------------------------------------------------------- drawing ----

class Page:
    """A tall figure laid out in inches, y measured from the top."""

    def __init__(self, height):
        self.H = height
        self.fig = plt.figure(figsize=(WIDTH_IN, height), dpi=DPI, facecolor=BG)
        self.ov = self.fig.add_axes([0, 0, 1, 1])
        self.ov.set_xlim(0, WIDTH_IN)
        self.ov.set_ylim(0, height)
        self.ov.axis("off")
        self.fig.canvas.draw()
        self.renderer = self.fig.canvas.get_renderer()

    def text(self, x, y, s, size=12, color=INK, weight="normal", ha="left", va="top", **kw):
        return self.ov.text(x, self.H - y, s, fontsize=size, color=color, fontweight=weight,
                            ha=ha, va=va, **kw)

    def width(self, t):
        return t.get_window_extent(self.renderer).width / DPI

    def rrect(self, x, y, w, h, color, edge=None, r=0.08):
        self.ov.add_patch(FancyBboxPatch((x, self.H - y - h), w, h,
                                         boxstyle=f"round,pad=0,rounding_size={min(r, h / 2)}",
                                         fc=color, ec=edge or color, lw=1))

    def axes(self, x, y, w, h):
        ax = self.fig.add_axes([x / WIDTH_IN, (self.H - y - h) / self.H, w / WIDTH_IN, h / self.H],
                               facecolor=BG)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(TRACK)
        ax.tick_params(axis="both", labelsize=11, colors=MUTED, length=0)
        ax.grid(axis="y", color=TRACK, lw=0.8)
        ax.set_axisbelow(True)
        return ax

    def header(self, title, sub):
        self.text(0.4, 0.3, title, 26, INK, "bold")
        self.text(0.4, 0.78, sub, 13, MUTED)
        return 1.3

    def tile(self, x, y, w, h, value, label, color):
        self.rrect(x, y, w, h, PANEL, TRACK, 0.12)
        self.text(x + w / 2, y + h * 0.12, value, 22, color, "bold", ha="center")
        self.text(x + w / 2, y + h * 0.66, label, 11.5, MUTED, ha="center")

    def panel_title(self, x, y, title, right=None, color=INK):
        self.text(x, y, title, 15, color, "bold")
        if right:
            self.text(WIDTH_IN - 0.4, y + 0.02, right, 12.5, MUTED, ha="right")

    def no_data(self, x, y, w, h, msg="No data yet"):
        self.rrect(x, y, w, h, PANEL, TRACK, 0.12)
        self.text(x + w / 2, y + h / 2, msg, 13, MUTED, ha="center", va="center")

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(path, dpi=DPI, facecolor=BG)
        plt.close(self.fig)
        return path


def progress_row(pg, y, label, val, tgt, color, fmt, kind):
    x, w = 0.4, WIDTH_IN - 0.8
    pg.text(x, y, label.upper(), 12, MUTED, "bold")
    rem = tgt - val
    if rem >= 0:
        status, scol = f"{fmt(rem)} left", MUTED
    elif kind == "goal":
        status, scol = "goal hit \u2713", GOOD
    else:
        status, scol = f"{fmt(-rem)} over", BAD if val > tgt * 1.1 else MUTED
    if kind == "goal" and rem <= 0:
        status = "goal hit \u2713"
    pg.text(x + w, y, status, 13, scol, "bold", ha="right")
    big = pg.text(x, y + 0.2, fmt(val), 30, color, "bold")
    pg.text(x + pg.width(big) + 0.08, y + 0.4, f"/ {fmt(tgt)}", 14, MUTED)
    pg.rrect(x, y + 0.78, w, 0.15, TRACK, r=0.075)
    frac = 0 if tgt <= 0 else min(val / tgt, 1)
    if frac > 0.01:
        pg.rrect(x, y + 0.78, max(w * frac, 0.15), 0.15, color, r=0.075)


def weight_axes(ax, data, days, units, goal_kg, title_in_ax=False):
    """Daily dots (faint), 7-day average (bold), goal line (dashed)."""
    avg = rolling_weight(data.weight, days)
    xs = {d: i for i, d in enumerate(days)}
    pts = [(xs[d], units.wt(data.weight[d])) for d in days if d in data.weight]
    if not pts:
        return None
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=34, color=C["weight"], alpha=0.28,
               zorder=2, label="Daily weigh-in")
    ad = [d for d in days if d in avg]
    ax.plot([xs[d] for d in ad], [units.wt(avg[d]) for d in ad], color=C["weight"], lw=3.6,
            solid_capstyle="round", zorder=3, label="7-day average")
    ax.scatter([xs[ad[-1]]], [units.wt(avg[ad[-1]])], s=90, color=C["weight"], zorder=4)
    vals = [p[1] for p in pts] + [units.wt(avg[d]) for d in ad]
    lo, hi = min(vals), max(vals)
    goal_in = False
    if goal_kg:
        g = units.wt(goal_kg)
        span = max(hi - lo, 1.0)
        if lo - 6 * span <= g <= hi + 6 * span and abs(g - sum(vals) / len(vals)) < 0.15 * g:
            goal_in = True
            lo, hi = min(lo, g), max(hi, g)
            ax.axhline(g, color=INK, lw=1.8, ls=(0, (5, 4)), zorder=1)
            ax.text(len(days) - 0.5, g, f"goal {g:.1f}", fontsize=11, color=INK, va="bottom", ha="right",
                    fontweight="bold", bbox=dict(fc=BG, ec="none", pad=1.5), zorder=5)
    pad = max((hi - lo) * 0.25, 0.6 if units.imp else 0.3)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlim(-0.6, len(days) - 0.4)
    n = len(days)
    step = 1 if n <= 8 else (2 if n <= 16 else (5 if n <= 35 else 14))
    ticks = list(range(n - 1, -1, -step))[::-1]
    ax.set_xticks(ticks)
    ax.set_xticklabels([days[i].strftime("%b %-d") for i in ticks], fontsize=11)
    ax.tick_params(axis="y", labelsize=11.5)
    return dict(last=units.wt(avg[ad[-1]]), first=units.wt(avg[ad[0]]), goal_in=goal_in)


def weight_section(pg, data, days, units, y, h, goal_kg, title="Weight"):
    avg = rolling_weight(data.weight, days)
    if not avg:
        pg.panel_title(0.4, y, title)
        pg.no_data(0.4, y + 0.45, WIDTH_IN - 0.8, h - 0.45, "Weigh in tomorrow morning to start your trend")
        return
    last_d = max(avg)
    first_d = min(avg)
    delta = units.wt(avg[last_d]) - units.wt(avg[first_d])
    pg.panel_title(0.4, y, title, f"{len(days)}-day view")
    pg.text(0.4, y + 0.38, f"{units.wt(avg[last_d]):.1f}", 34, C["weight"], "bold")
    wtxt = pg.ov.texts[-1]
    pg.text(0.4 + pg.width(wtxt) + 0.08, y + 0.68, f"{units.w} (7-day avg)", 13, MUTED)
    if first_d != last_d:
        pg.text(WIDTH_IN - 0.4, y + 0.55, f"{delta:+.1f} {units.w}", 20,
                GOOD if (goal_kg and ((goal_kg < data.weight[last_d] and delta < 0) or (goal_kg > data.weight[last_d] and delta > 0))) else INK,
                "bold", ha="right")
    ax = pg.axes(0.4, y + 1.1, WIDTH_IN - 0.8, h - 1.75)
    weight_axes(ax, data, days, units, goal_kg)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=11,
              labelcolor=MUTED, handlelength=1.4)


def bar_panel(pg, y, h, days, vals, target, color, title, right, fmt=lambda v: f"{v:,.0f}",
              unit_note=None, goal_hit=None):
    note = f"dashed = target {fmt(target)}" if target else None
    pg.panel_title(0.4, y, title, f"{right}  \u2022  {note}" if right and note else (right or note))
    ax = pg.axes(0.4, y + 0.5, WIDTH_IN - 0.8, h - 1.05)
    xs = range(len(days))
    ys = [vals.get(d) for d in days]
    top = max([v for v in ys if v] + [target or 0, 1]) * 1.2
    for i, v in zip(xs, ys):
        if v:
            hit = goal_hit(v) if goal_hit else True
            ax.bar(i, v, width=0.62, color=color, alpha=1 if hit else 0.55, zorder=3)
            ax.text(i, v + top * 0.02, fmt(v), ha="center", va="bottom", fontsize=10.5,
                    fontweight="bold", color=INK, zorder=4,
                    bbox=dict(fc=BG, ec="none", pad=1, alpha=0.85))
        else:
            ax.text(i, top * 0.03, "\u2013", ha="center", va="bottom", fontsize=12, color=MUTED)
    if target:
        ax.axhline(target, color=INK, lw=1.6, ls=(0, (5, 4)), zorder=2)
    ax.set_ylim(0, top)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([d.strftime("%a\n%-d") for d in days], fontsize=11)
    ax.set_yticks([])
    ax.grid(False)
    return ax

# ---------------------------------------------------------------- scores ----

WEIGHTS = dict(logging=25, protein=25, training=20, sleep=15, steps=15)
FOCUS = dict(
    logging="Log every meal, even the rough ones. Aim for 7 of 7 logged days.",
    protein="Hit your protein target. Front-load it: 30-40 g at breakfast and again at lunch.",
    training="Book your sessions in advance. Hit every planned session, even short ones.",
    sleep="Protect sleep: fixed bedtime, screens off 30 minutes before, aim for 7+ hours.",
    steps="Add a 15-20 minute walk after your biggest meal each day.")


def week_score(data, end):
    days = [end - dt.timedelta(i) for i in range(6, -1, -1)]
    t = data.target(end)
    logged = [d for d in days if data.food.get(d, {}).get("cal", 0) >= 0.6 * t["calories"]]
    prot_hit = [d for d in logged if data.food[d]["p"] >= 0.9 * t["protein_g"]]
    sessions = sum(len(data.workout_sessions(d)) for d in days)
    planned = max(t["sessions_per_week"], 1)
    sl = [data.sleep[d] for d in days if d in data.sleep]
    st = [data.steps[d] for d in days if d in data.steps]
    ratio = dict(logging=len(logged) / 7,
                 protein=len(prot_hit) / 7,
                 training=min(sessions / planned, 1))
    sleep_avg = sum(sl) / len(sl) if sl else None
    steps_avg = sum(st) / len(st) if st else None
    if sl:
        ratio["sleep"] = min(max((sleep_avg - 5.0) / 2.0, 0), 1)  # 7h+ = full, 5h = zero
    if st:
        ratio["steps"] = min(steps_avg / max(t["step_goal"], 1), 1)
    total_w = sum(WEIGHTS[k] for k in ratio)
    score = round(100 * sum(WEIGHTS[k] * ratio[k] for k in ratio) / total_w)
    focus_key = min(ratio, key=lambda k: (ratio[k], -WEIGHTS[k]))
    points = {k: round(WEIGHTS[k] * ratio[k] * 100 / total_w) for k in ratio}
    return dict(score=score, ratios={k: round(v, 3) for k, v in ratio.items()},
                points=points, max_points={k: round(WEIGHTS[k] * 100 / total_w) for k in ratio},
                logged_days=len(logged), protein_hit_days=len(prot_hit),
                sessions=sessions, planned_sessions=int(planned),
                sleep_avg_h=None if sleep_avg is None else round(sleep_avg, 2),
                steps_avg=None if steps_avg is None else round(steps_avg),
                tracked=sorted(ratio), focus_key=focus_key, focus=FOCUS[focus_key],
                avg_cal_logged=round(sum(data.food[d]["cal"] for d in logged) / len(logged)) if logged else None)

# ----------------------------------------------------------------- charts ---

def chart_daily(data, day, units, out, final=False):
    t = data.target(day)
    f = data.food.get(day, dict(cal=0, p=0, c=0, f=0, fib=0, n=0, meals={}))
    water = data.water.get(day, 0)
    H = 12.3 if final else 9.7
    pg = Page(H)
    today = dt.date.today()
    sub = day.strftime("%A, %b %-d")
    if day == today and not final:
        sub += "  \u2022  as of " + dt.datetime.now().strftime("%-I:%M %p")
    y = pg.header("Day recap" if final else "Today so far", sub)
    rows = [("Calories", f["cal"], t["calories"], C["cal"], lambda v: f"{v:,.0f}", "limit"),
            ("Protein", f["p"], t["protein_g"], C["protein"], lambda v: f"{v:,.0f} g", "goal"),
            ("Carbs", f["c"], t["carbs_g"], C["carbs"], lambda v: f"{v:,.0f} g", "limit"),
            ("Fat", f["f"], t["fat_g"], C["fat"], lambda v: f"{v:,.0f} g", "limit"),
            ("Fiber", f["fib"], t["fiber_g"], C["fiber"], lambda v: f"{v:,.0f} g", "goal"),
            ("Water", water, t["water_ml"], C["water"], units.water_s, "goal")]
    for r in rows:
        progress_row(pg, y, *r)
        y += 1.08
    y += 0.1
    if final:
        w3 = (WIDTH_IN - 0.8 - 0.3) / 2
        wt = data.weight.get(day)
        sleep = data.sleep.get(day)
        steps = data.steps.get(day)
        ses = data.workout_sessions(day)
        kcal_burn = sum(num(s.get("est_kcal"), 0) for s in ses)
        tiles = [(units.wt_s(wt) if wt else "\u2013", "Weigh-in", C["weight"]),
                 (f"{sleep:.1f} h" if sleep is not None else "\u2013", "Sleep (last night)", C["sleep"]),
                 (f"{steps:,.0f}" if steps is not None else "\u2013", "Steps", C["steps"]),
                 (f"{len(ses)}", "Workouts" + (f" \u2022 ~{kcal_burn:,.0f} kcal" if kcal_burn else ""), C["workout"])]
        for i, (v, l, c) in enumerate(tiles):
            pg.tile(0.4 + (i % 2) * (w3 + 0.3), y + (i // 2) * 1.2, w3, 1.0, v, l, c)
        y += 2.5
        pg.panel_title(0.4, y, "Where the calories came from")
        y += 0.5
        kc = [("Protein", f["p"] * 4, C["protein"], f["p"]), ("Carbs", f["c"] * 4, C["carbs"], f["c"]),
              ("Fat", f["f"] * 9, C["fat"], f["f"])]
        tot = sum(k[1] for k in kc)
        cx, cy, r = 1.55, pg.H - (y + 1.0), 0.95
        if tot > 0:
            a0 = 90
            for name, kcal, col, g in kc:
                a1 = a0 - 360 * kcal / tot
                pg.ov.add_patch(Wedge((cx, cy), r, a1, a0, width=0.38, fc=col, ec=BG, lw=2))
                a0 = a1
            pg.text(cx, y + 1.0, f"{f['cal']:,.0f}", 19, INK, "bold", ha="center", va="center")
            pg.text(cx, y + 1.27, "kcal", 11, MUTED, ha="center", va="center")
            for i, (name, kcal, col, g) in enumerate(kc):
                yy = y + 0.2 + i * 0.62
                pg.rrect(3.1, yy + 0.06, 0.2, 0.2, col, r=0.05)
                pg.text(3.42, yy, f"{name}  {100 * kcal / tot:.0f}%", 15, INK, "bold")
                pg.text(3.42, yy + 0.27, f"{g:,.0f} g", 12, MUTED)
        else:
            pg.no_data(0.4, y, WIDTH_IN - 0.8, 2.0, "Nothing logged today")
        y += 2.3
    else:
        pg.panel_title(0.4, y, "Calories by meal")
        y += 0.5
        order = ["breakfast", "lunch", "dinner", "snack"]
        meals = {m: f["meals"].get(m, 0) for m in order}
        for m, v in f["meals"].items():
            if m not in meals:
                meals["snack"] += v
        mx = max(list(meals.values()) + [1])
        for m in order:
            pg.text(0.4, y + 0.04, m.capitalize(), 14, MUTED, "bold")
            pg.rrect(1.6, y + 0.04, 3.4, 0.26, TRACK, r=0.13)
            if meals[m] > 0:
                pg.rrect(1.6, y + 0.04, max(3.4 * meals[m] / mx, 0.26), 0.26, C["cal"], r=0.13)
            pg.text(WIDTH_IN - 0.4, y, f"{meals[m]:,.0f}", 15, INK, "bold", ha="right")
            y += 0.5
    return pg.save(out)


def chart_weight(data, day, units, out, ndays=30):
    days = [day - dt.timedelta(i) for i in range(ndays - 1, -1, -1)]
    pg = Page(6.6)
    y = pg.header("Weight trend", f"{days[0].strftime('%b %-d')} \u2013 {day.strftime('%b %-d')}")
    weight_section(pg, data, days, units, y + 0.1, 4.9, data.target(day)["goal_weight_kg"], "Weight")
    return pg.save(out)


def chart_weekly(data, end, units, out):
    days = [end - dt.timedelta(i) for i in range(6, -1, -1)]
    t = data.target(end)
    s = week_score(data, end)
    pg = Page(23.5)
    y = pg.header("Week in review", f"{days[0].strftime('%b %-d')} \u2013 {end.strftime('%b %-d')}")
    # score card
    pg.rrect(0.4, y, WIDTH_IN - 0.8, 1.5, PANEL, TRACK, 0.14)
    sc = GOOD if s["score"] >= 80 else (C["carbs"] if s["score"] >= 60 else BAD)
    big = pg.text(0.7, y + 0.12, f"{s['score']}", 56, sc, "bold")
    pg.text(0.7 + pg.width(big) + 0.1, y + 0.78, "/ 100 weekly score", 14, MUTED, "bold")
    pg.text(0.7, y + 1.12, "logging 25 \u2022 protein 25 \u2022 training 20 \u2022 sleep 15 \u2022 steps 15", 10.5, MUTED)
    y += 1.75
    tw = (WIDTH_IN - 0.8 - 0.3) / 2
    sess = f"{s['sessions']} / {s['planned_sessions']}"
    tiles = [(f"{s['logged_days']} / 7", "Days logged", C["cal"]),
             (f"{s['protein_hit_days']} / 7", "Protein hit days", C["protein"]),
             (sess, "Training sessions", C["workout"]),
             (f"{s['sleep_avg_h']:.1f} h" if s["sleep_avg_h"] is not None else "\u2013", "Avg sleep", C["sleep"])]
    for i, (v, l, c) in enumerate(tiles):
        pg.tile(0.4 + (i % 2) * (tw + 0.3), y + (i // 2) * 1.2, tw, 1.0, v, l, c)
    y += 2.5
    pg.rrect(0.4, y, WIDTH_IN - 0.8, 1.15, C["protein"], r=0.14)
    pg.text(0.65, y + 0.14, "FOCUS FOR NEXT WEEK", 11.5, "#DBEAFE", "bold")
    pg.text(0.65, y + 0.42, s["focus"], 12.5, "#FFFFFF", "bold", wrap=True)
    pg.ov.texts[-1]._get_wrap_line_width = lambda: 5.0 * DPI
    y += 1.5
    cal = {d: data.food[d]["cal"] for d in days if d in data.food}
    pro = {d: data.food[d]["p"] for d in days if d in data.food}
    avg_cal = (sum(cal.values()) / len(cal)) if cal else 0
    bar_panel(pg, y, 3.5, days, cal, t["calories"], C["cal"], "Calories",
              f"avg {avg_cal:,.0f}" if cal else None)
    y += 3.75
    bar_panel(pg, y, 3.5, days, pro, t["protein_g"], C["protein"], "Protein (g)",
              f"hit {s['protein_hit_days']} of 7", goal_hit=lambda v: v >= 0.9 * t["protein_g"])
    y += 3.75
    wdays = [end - dt.timedelta(i) for i in range(27, -1, -1)]
    weight_section(pg, data, wdays, units, y, 4.9, t["goal_weight_kg"], "Weight")
    y += 5.2
    sleep = {d: data.sleep[d] for d in days if d in data.sleep}
    bar_panel(pg, y, 3.5, days, sleep, t["sleep_goal_h"], C["sleep"], "Sleep (hours)",
              f"avg {s['sleep_avg_h']:.1f} h" if s["sleep_avg_h"] is not None else None,
              fmt=lambda v: f"{v:.1f}")
    return pg.save(out), s


def chart_monthly(data, end, units, out):
    days = [end - dt.timedelta(i) for i in range(29, -1, -1)]
    prev = [days[0] - dt.timedelta(i) for i in range(30, 0, -1)]
    t = data.target(end)
    pg = Page(22.0)
    y = pg.header("Month in review", f"{days[0].strftime('%b %-d')} \u2013 {end.strftime('%b %-d')}")

    def stats(ds):
        lg = [d for d in ds if data.food.get(d, {}).get("cal", 0) >= 0.6 * t["calories"]]
        ph = [d for d in lg if data.food[d]["p"] >= 0.9 * t["protein_g"]]
        sl = [data.sleep[d] for d in ds if d in data.sleep]
        st = [data.steps[d] for d in ds if d in data.steps]
        av = rolling_weight(data.weight, ds)
        return dict(logged=len(lg), prot=len(ph),
                    cal=sum(data.food[d]["cal"] for d in lg) / len(lg) if lg else None,
                    p=sum(data.food[d]["p"] for d in lg) / len(lg) if lg else None,
                    work=sum(len(data.workout_sessions(d)) for d in ds),
                    sleep=sum(sl) / len(sl) if sl else None,
                    steps=sum(st) / len(st) if st else None,
                    wt=av[max(av)] if av else None)
    cur, old = stats(days), stats(prev)
    wchg = None
    wd = [d for d in days if d in data.weight]
    avg = rolling_weight(data.weight, days)
    if len(avg) >= 2:
        wchg = units.wt(avg[max(avg)]) - units.wt(avg[min(avg)])
    tw = (WIDTH_IN - 0.8 - 0.3) / 2
    tiles = [(f"{wchg:+.1f} {units.w}" if wchg is not None else "\u2013", "Weight change (avg)", C["weight"]),
             (f"{cur['cal']:,.0f}" if cur["cal"] else "\u2013", "Avg kcal (logged days)", C["cal"]),
             (f"{cur['p']:,.0f} g" if cur["p"] else "\u2013", "Avg protein", C["protein"]),
             (f"{cur['work']}", "Workouts", C["workout"])]
    for i, (v, l, c) in enumerate(tiles):
        pg.tile(0.4 + (i % 2) * (tw + 0.3), y + (i // 2) * 1.2, tw, 1.0, v, l, c)
    y += 2.6
    weight_section(pg, data, days, units, y, 4.9, t["goal_weight_kg"], "Weight")
    y += 5.6
    # weekly average calories, 4 full weeks
    pg.panel_title(0.4, y, "Average calories by week", f"target {t['calories']:,.0f}")
    ax = pg.axes(0.4, y + 0.5, WIDTH_IN - 0.8, 3.0)
    wk = []
    for i in range(3, -1, -1):
        wend = end - dt.timedelta(7 * i)
        ds = [wend - dt.timedelta(k) for k in range(7)]
        vals = [data.food[d]["cal"] for d in ds if data.food.get(d, {}).get("cal", 0) >= 0.6 * t["calories"]]
        wk.append((wend, sum(vals) / len(vals) if vals else 0))
    top = max([v for _, v in wk] + [t["calories"], 1]) * 1.2
    for i, (we, v) in enumerate(wk):
        if v:
            ax.bar(i, v, width=0.55, color=C["cal"], zorder=3)
            ax.text(i, v + top * 0.02, f"{v:,.0f}", ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax.axhline(t["calories"], color=INK, lw=1.6, ls=(0, (5, 4)), zorder=2)
    ax.set_ylim(0, top)
    ax.set_yticks([])
    ax.grid(False)
    ax.set_xticks(range(4))
    ax.set_xticklabels([f"wk ending\n{we.strftime('%b %-d')}" for we, _ in wk], fontsize=11)
    y += 4.2
    # this month vs last month
    pg.panel_title(0.4, y, "This month vs last month")
    y += 0.5
    hdr = [(3.1, "Last", MUTED), (4.3, "This", INK), (5.6, "Change", MUTED)]
    for x, h, c in hdr:
        pg.text(x, y, h, 11.5, c, "bold", ha="right")
    y += 0.35

    def row(label, a, b, fmt, higher_good=None, dec=0):
        nonlocal y
        pg.text(0.4, y, label, 13, INK, "bold")
        pg.text(3.1, y, fmt(a) if a is not None else "\u2013", 13, MUTED, ha="right")
        pg.text(4.3, y, fmt(b) if b is not None else "\u2013", 13, INK, "bold", ha="right")
        if a is not None and b is not None:
            d = b - a
            col = INK
            if higher_good is not None and abs(d) > 1e-9:
                col = GOOD if (d > 0) == higher_good else BAD
            pg.text(5.6, y, f"{d:+,.{dec}f}", 13, col, "bold", ha="right")
        y += 0.42
    row("Days logged", old["logged"], cur["logged"], lambda v: f"{v:.0f}", True)
    row("Avg calories", old["cal"], cur["cal"], lambda v: f"{v:,.0f}")
    row("Avg protein (g)", old["p"], cur["p"], lambda v: f"{v:,.0f}", True)
    row("Protein hit days", old["prot"], cur["prot"], lambda v: f"{v:.0f}", True)
    row("Workouts", old["work"], cur["work"], lambda v: f"{v:.0f}", True)
    row("Avg sleep (h)", old["sleep"], cur["sleep"], lambda v: f"{v:.1f}", True, 1)
    row("Avg steps", old["steps"], cur["steps"], lambda v: f"{v:,.0f}", True)
    row(f"Weight ({units.w})", None if old["wt"] is None else units.wt(old["wt"]),
        None if cur["wt"] is None else units.wt(cur["wt"]), lambda v: f"{v:.1f}", None, 1)
    y += 0.3
    # measurements
    pg.panel_title(0.4, y, "Body measurements", f"{'inches' if units.imp else 'cm'}, first vs latest")
    y += 0.55
    sites = [("waist_cm", "Waist"), ("hips_cm", "Hips"), ("chest_cm", "Chest"),
             ("arm_cm", "Arm"), ("thigh_cm", "Thigh")]
    ch = []
    for col, name in sites:
        series = [(d, num(x.get(col))) for d, x in data.measure if num(x.get(col)) is not None]
        if len(series) >= 2:
            ch.append((name, units.ln(series[-1][1] - series[0][1]), units.ln(series[-1][1]),
                       (series[-1][0] - series[0][0]).days))
    if ch:
        mid, scale = 3.3, 1.2 / max(max(abs(c[1]) for c in ch), 0.5)
        for name, d, last, span in ch:
            pg.text(0.4, y + 0.02, name, 13, INK, "bold")
            w = max(abs(d) * scale, 0.04)
            pg.rrect(mid if d >= 0 else mid - w, y, w, 0.26, C["measure"], r=0.06)
            pg.text(WIDTH_IN - 0.4, y, f"{d:+.1f} {units.l}", 13, INK, "bold", ha="right")
            y += 0.45
    else:
        pg.no_data(0.4, y, WIDTH_IN - 0.8, 1.2, "Measure monthly (waist, hips, chest, arms, thighs)")
    return pg.save(out), dict(this=cur, last=old, weight_change=wchg)

# ------------------------------------------------------------------ main ----

def main():
    # Premium HTML/Chromium renderer first; this matplotlib code is the fallback when Chromium is not installed.
    try:
        import render_core
        if render_core.chromium_available():
            import render
            return render.main(sys.argv[1:])
        print("note: Chromium not available, using the basic matplotlib fallback "
              "(pip install playwright && playwright install chromium for the full design)", file=sys.stderr)
    except ImportError:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["overview", "detail", "daily", "eod", "weekly", "monthly", "weight", "treatment", "all"])
    ap.add_argument("module", nargs="?", help="ignored by the fallback charts")
    ap.add_argument("--theme", default=None, help="ignored by the fallback charts")
    ap.add_argument("--palette", default=None, help="ignored by the fallback charts")
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--out", default=None)
    ap.add_argument("--date", default=None)
    ap.add_argument("--units", default="auto", choices=["auto", "imperial", "metric"])
    ap.add_argument("--days", type=int, default=30, help="window for the weight chart")
    ap.add_argument("--window", type=int, default=30, help="ignored by the fallback charts")
    ap.add_argument("--compound", default=None, help="ignored by the fallback charts")
    ap.add_argument("--coach", default=None, help="ignored by the fallback charts")
    a = ap.parse_args()
    day = pdate(a.date) if a.date else dt.date.today()
    if not day:
        sys.exit("bad --date, use YYYY-MM-DD")
    data = Data(a.data)
    out = Path(a.out) if a.out else Path(a.data) / "charts"
    units = pick_units(data, a.units, day)
    ds = day.isoformat()
    paths, summary = [], {}
    if a.kind in ("overview", "detail", "treatment"):
        sys.exit(f"the {a.kind} image needs headless Chromium (pip install playwright, then python -m playwright install chromium)")
    kinds = ["daily", "eod", "weekly", "monthly"] if a.kind == "all" else [a.kind]
    for k in kinds:
        if k == "daily":
            paths.append(chart_daily(data, day, units, out / f"daily_{ds}.png"))
            paths.append(chart_weight(data, day, units, out / f"weight_{ds}.png", 30))
        elif k == "eod":
            paths.append(chart_daily(data, day, units, out / f"eod_{ds}.png", final=True))
        elif k == "weekly":
            p, s = chart_weekly(data, day, units, out / f"weekly_{ds}.png")
            paths.append(p)
            paths.append(chart_weight(data, day, units, out / f"weight_week_{ds}.png", 28))
            summary["week"] = s
        elif k == "monthly":
            p, s = chart_monthly(data, day, units, out / f"monthly_{ds}.png")
            paths.append(p)
            summary["month"] = s
        elif k == "weight":
            paths.append(chart_weight(data, day, units, out / f"weight_{ds}.png", a.days))
        elif k == "treatment":
            sys.exit("the treatment image needs headless Chromium (pip install playwright, then python -m playwright install chromium)")
    for p in dict.fromkeys(paths):
        print(p)
    print("SUMMARY:" + json.dumps(summary, default=str))


if __name__ == "__main__":
    main()
