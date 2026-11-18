"""Daily pillar scores, the daily readiness (recovery) score, the day score and the coach line.

Pure functions over charts.Data. Definitions are documented in SKILL.md section 5.7; use the numbers these
functions print, never recompute by hand. Every pillar is 0-100 or None (no data). Missing pillars are dropped
and the remaining weights are rescaled, as in the weekly score.
"""
import datetime as dt

PILLARS = ("recovery", "sleep", "nutrition", "hydration", "activity")
READY_W = dict(sleep=45, nutrition=20, hydration=10, activity=10, load=15)
DAY_W = dict(sleep=25, nutrition=30, hydration=15, activity=30)


def _off(data):
    """Modules the user turned off (set on the Data object by the renderers). Their data never feeds a score."""
    return getattr(data, "off", ())


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _pct(x):
    return None if x is None else round(100 * x)


def logged(data, d):
    f = data.food.get(d)
    return f is not None and f["cal"] >= 0.3 * data.target(d)["calories"]


def sleep_score(data, d):
    h = None if "health" in _off(data) else data.sleep.get(d)
    if h is None:
        return None
    goal = max(data.target(d)["sleep_goal_h"], 5.0)
    return clamp((h - 4.0) / (goal - 4.0))  # goal hours = full, 4 h = zero


def nutrition_score(data, d):
    """Half protein (capped at 100% of target), half calorie fit (within 5% of target is full; over or far under loses)."""
    if "nutrition" in _off(data) or not logged(data, d):
        return None
    t, f = data.target(d), data.food[d]
    prot = clamp(f["p"] / t["protein_g"]) if t["protein_g"] else 1.0
    r = f["cal"] / t["calories"]
    fit = 1.0 if 0.8 <= r <= 1.05 else (clamp(1 - (r - 1.05) * 3) if r > 1.05 else clamp(1 - (0.8 - r) * 2.5))
    return 0.5 * prot + 0.5 * fit


def hydration_score(data, d):
    if "health" in _off(data) or d not in data.water:
        return None
    t = data.target(d)
    return clamp(data.water[d] / t["water_ml"]) if t["water_ml"] else None


def steps_ratio(data, d):
    if "activity" in _off(data) or d not in data.steps:
        return None
    return clamp(data.steps[d] / max(data.target(d)["step_goal"], 1))


def activity_score(data, d):
    """Steps up to 70 points, a logged session adds 30. Without a session, full steps scores 85 (rest days are fine)."""
    sr, ses = steps_ratio(data, d), _sessions(data, d)
    if sr is None and not ses:
        return None
    if sr is None:  # steps module off or no steps: a logged session is a good movement day
        return 0.85
    return (min(1.0, sr * 0.70 + 0.30) if ses else sr * 0.85)


def _sessions(data, d):
    return [] if "workouts" in _off(data) else data.workout_sessions(d)


def load_score(data, d):
    """Training load: sessions in the 3 days before d. 0-1 is fresh, 2 is moderate, 3+ is heavy."""
    n = sum(len(_sessions(data, d - dt.timedelta(k))) for k in (1, 2, 3))
    return 1.0 if n <= 1 else 0.7 if n == 2 else 0.4


def _blend(parts, weights):
    parts = {k: v for k, v in parts.items() if v is not None}
    if not parts:
        return None
    tw = sum(weights[k] for k in parts)
    return sum(weights[k] * v for k, v in parts.items()) / tw


def pillars(data, d):
    """Pillar scores for day d as 0-100 (None = no data). `recovery` is the readiness for d, `day` the day score."""
    p = dict(sleep=sleep_score(data, d), nutrition=nutrition_score(data, d),
             hydration=hydration_score(data, d), activity=activity_score(data, d))
    y = d - dt.timedelta(1)
    ready = _blend(dict(sleep=p["sleep"], nutrition=nutrition_score(data, y), hydration=hydration_score(data, y),
                        activity=activity_score(data, y), load=load_score(data, d) if p["sleep"] is not None else None), READY_W)
    if ready is not None and p["sleep"] is not None and p["sleep"] < 0.6:
        ready = min(ready, 0.66)  # a short night caps readiness at Steady, whatever yesterday looked like
    out = {k: _pct(v) for k, v in p.items()}
    out["recovery"] = _pct(ready) if p["sleep"] is not None else None  # no sleep logged, no readiness
    out["day"] = _pct(_blend(p, DAY_W))
    return out


def state_word(score, kind="recovery"):
    if score is None:
        return "No score yet"
    if kind == "day":
        return "Strong day" if score >= 80 else "Solid day" if score >= 60 else "Light day"
    return "Primed" if score >= 67 else "Steady" if score >= 34 else "Recover"


def avg(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None


def period(data, days):
    """Pillar averages over a list of days: {pillar: avg or None}, plus per-day series for sparklines."""
    series = {k: [] for k in (*PILLARS, "day")}
    for d in days:
        p = pillars(data, d)
        for k in series:
            series[k].append(p.get(k))
    return {k: avg(v) for k, v in series.items()}, series


def weakest(p):
    cand = {k: v for k, v in p.items() if k in ("sleep", "nutrition", "hydration", "activity") and v is not None}
    return min(cand, key=cand.get) if cand else None


GAP_LINES = dict(
    sleep="Sleep was the gap. Aim for lights-out 30 minutes earlier tonight.",
    nutrition="Nutrition drifted. Plan tomorrow's first meal around 30-40 g of protein.",
    hydration="Hydration lagged. Put a full bottle where you work tomorrow.",
    activity="Movement was light. A 20-minute walk counts.")


def coach_line(data, day, kind, units=None, now=None, extra=None):
    """One plain sentence. kind: daily, eod, weekly, monthly, weight."""
    t = data.target(day)
    p = pillars(data, day)
    now = now or dt.datetime.now()
    midday = day == now.date()
    hour = now.hour if midday else 23
    f = data.food.get(day, dict(cal=0, p=0))
    if kind == "daily":
        h = None if "health" in _off(data) else data.sleep.get(day)
        if h is not None and h < t["sleep_goal_h"] - 1.0:
            return "Sleep was short. Keep today light and hit your protein."
        if p["recovery"] is not None and p["recovery"] >= 67 and not _sessions(data, day):
            return "Well recovered. Good day for a hard session."
        if p["recovery"] is None and f["cal"] == 0:
            return "Log last night's sleep and your first meal to unlock today's readiness score."
        if hour >= 14 and f["p"] < 0.5 * t["protein_g"]:
            return "Protein is behind. Make your next meal 30-40 g."
        if hour >= 14 and "health" not in _off(data) and t["water_ml"] and data.water.get(day, 0) < 0.4 * t["water_ml"]:
            return "Water is low. Drink a glass now and one with each meal."
        if p["recovery"] is None:
            return "Log last night's sleep to unlock your daily readiness score."
        return "Steady start. Log each meal as you eat it and you stay on track."
    if kind == "eod":
        if p["day"] is not None and p["day"] >= 80:
            return "Strong day. Repeat it tomorrow: same bedtime, protein early."
        w = weakest(p)
        return GAP_LINES[w] if w else "Log sleep, water and steps tomorrow for a full day score."
    return extra or ""


def weight_line(delta, n, goal_gap, unit, goal_type):
    """Insight sentence for the weight image (the chip already shows the change). delta = 7-day average change over n days."""
    if abs(delta) < 0.2:
        return "Flat trend. Daily weight is noisy, so hold steady for two weeks before changing anything."
    per_wk = abs(delta) / max(n, 1) * 7
    good = (goal_type == "lose" and delta < 0) or (goal_type == "gain" and delta > 0)
    tail = "On track. Keep calories steady." if good else "Check this against your goal before changing targets."
    return f"About {per_wk:.1f} {unit} a week. {tail}"
