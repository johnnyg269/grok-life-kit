#!/usr/bin/env python3
"""Medication and peptide tracking for Grok Life: dose log, schedule, estimated level, injection sites, side effects.

Grok Life tracks what the user and their prescriber decided. It never recommends a dose, a titration change or a compound.
The level curve is an ESTIMATE from published half-lives (one-compartment model with first-order absorption, Bateman),
not a blood test and not medical advice.

CLI (all take --data DIR, default /workspace/macro-coach):
  python meds.py log --compound tirzepatide --brand Zepbound --mg 5 --site abdomen_ur [--datetime "2026-11-16 19:30"] [--notes "..."]
  python meds.py schedule --compound tirzepatide --interval-days 7 --next-due "2026-11-23 19:30" [--titration "2.5x4>5x4>7.5x4"] [--half-life-h 120 --tmax-h 24]
  python meds.py effects [--date YYYY-MM-DD] [--nausea 4 --heartburn 1 --food-noise 3 --appetite 6 --fatigue 2 --constipation 0]
  python meds.py status [--compound NAME] [--now "YYYY-MM-DD HH:MM"]     # JSON: level, next dose, steady state, sites, side effects
  python meds.py selftest                                                  # checks the model against the published half-lives and Tmax
"""
import argparse
import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

DEFAULT_DATA = Path("/workspace/macro-coach")

# ---- compounds -----------------------------------------------------------------------------------------------------
# half_life_h: terminal elimination half-life. tmax_h: time to peak after a subcutaneous dose (used to derive the absorption rate).
# Sources are cited in SKILL.md section 5.8. interval_days is the usual schedule, only used to suggest a default schedule row.
COMPOUNDS = {
    "tirzepatide": dict(label="Tirzepatide", brands=["Zepbound", "Mounjaro"], half_life_h=120.0, tmax_h=24.0, interval_days=7, approved=True,
                        hl_range="about 5 days", tmax_range="8 to 72 h (24 h median in the Zepbound label)"),
    "semaglutide": dict(label="Semaglutide", brands=["Ozempic", "Wegovy", "Rybelsus"], half_life_h=168.0, tmax_h=48.0, interval_days=7, approved=True,
                        hl_range="about 1 week", tmax_range="1 to 3 days"),
    "retatrutide": dict(label="Retatrutide", brands=[], half_life_h=144.0, tmax_h=24.0, interval_days=7, approved=False,
                        hl_range="about 6 days", tmax_range="12 to 48 h"),
    "liraglutide": dict(label="Liraglutide", brands=["Victoza", "Saxenda"], half_life_h=13.0, tmax_h=10.0, interval_days=1, approved=True,
                        hl_range="13 h", tmax_range="8 to 12 h"),
    "cagrilintide": dict(label="Cagrilintide", brands=[], half_life_h=177.0, tmax_h=48.0, interval_days=7, approved=False,
                         hl_range="159 to 195 h (combination data)", tmax_range="24 to 72 h"),
}
ALIASES = {}
for _k, _v in COMPOUNDS.items():
    ALIASES[_k] = _k
    for _b in _v["brands"]:
        ALIASES[_b.lower()] = _k
ALIASES.update({"mounjaro": "tirzepatide", "zepbound": "tirzepatide", "ozempic": "semaglutide", "wegovy": "semaglutide",
                "victoza": "liraglutide", "saxenda": "liraglutide", "reta": "retatrutide", "cagri": "cagrilintide"})

# ---- injection sites -----------------------------------------------------------------------------------------------
# Left and right are the user's own left and right. Tie-break order alternates regions so a fresh rotation spreads out.
SITES = ["abdomen_ul", "thigh_r", "arm_l", "abdomen_lr", "thigh_l", "arm_r", "abdomen_ur", "abdomen_ll"]
SITE_LABEL = {
    "abdomen_ul": "Abdomen, upper left", "abdomen_ur": "Abdomen, upper right", "abdomen_ll": "Abdomen, lower left", "abdomen_lr": "Abdomen, lower right",
    "thigh_l": "Left thigh", "thigh_r": "Right thigh", "arm_l": "Left upper arm", "arm_r": "Right upper arm"}
SITE_ALIAS = {"stomach_upper_left": "abdomen_ul", "stomach_upper_right": "abdomen_ur", "stomach_lower_left": "abdomen_ll",
              "stomach_lower_right": "abdomen_lr", "left_thigh": "thigh_l", "right_thigh": "thigh_r",
              "left_arm": "arm_l", "right_arm": "arm_r", "left_upper_arm": "arm_l", "right_upper_arm": "arm_r"}

EFFECTS = [("nausea", "Nausea"), ("heartburn", "Heartburn"), ("food_noise", "Food noise"),
           ("suppressed_appetite", "Suppressed appetite"), ("fatigue", "Fatigue"), ("constipation", "Constipation")]

DOSE_FIELDS = ["datetime", "compound", "brand", "dose_mg", "site", "notes"]
SCHED_FIELDS = ["compound", "brand", "interval_days", "next_due", "dose_mg", "titration", "half_life_h", "tmax_h"]
EFFECT_FIELDS = ["date"] + [k for k, _ in EFFECTS]


# ---- parsing -------------------------------------------------------------------------------------------------------
def pdt(s):
    """Parse 'YYYY-MM-DD HH:MM' (or 'YYYY-MM-DDTHH:MM', or a bare date at 09:00). None if empty or bad."""
    s = (s or "").strip()
    if not s:
        return None
    for f in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            pass
    try:
        return dt.datetime.combine(dt.date.fromisoformat(s), dt.time(9, 0))
    except ValueError:
        return None


def num(x, default=None):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return default


def norm_compound(name):
    n = (name or "").strip().lower().replace(" ", "_")
    return ALIASES.get(n, ALIASES.get(n.replace("_", ""), n))


def norm_site(s):
    s = (s or "").strip().lower().replace(" ", "_").replace(",", "")
    return SITE_ALIAS.get(s, s)


def read_rows(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_doses(root):
    out = []
    for r in read_rows(Path(root) / "meds.csv"):
        t, mg = pdt(r.get("datetime")), num(r.get("dose_mg"))
        if t is None or mg is None or mg <= 0:
            continue
        out.append(dict(t=t, compound=norm_compound(r.get("compound")), brand=(r.get("brand") or "").strip(),
                        mg=mg, site=norm_site(r.get("site")), notes=(r.get("notes") or "").strip()))
    return sorted(out, key=lambda d: d["t"])


def load_schedule(root):
    """One row per compound (the last row wins). Returns {compound: dict}."""
    out = {}
    for r in read_rows(Path(root) / "med_schedule.csv"):
        c = norm_compound(r.get("compound"))
        if not c:
            continue
        out[c] = dict(compound=c, brand=(r.get("brand") or "").strip(), interval_days=num(r.get("interval_days")),
                      next_due=pdt(r.get("next_due")), dose_mg=num(r.get("dose_mg")), titration=(r.get("titration") or "").strip(),
                      half_life_h=num(r.get("half_life_h")), tmax_h=num(r.get("tmax_h")))
    return out


def load_effects(root):
    out = {}
    for r in read_rows(Path(root) / "side_effects.csv"):
        try:
            d = dt.date.fromisoformat((r.get("date") or "").strip())
        except ValueError:
            continue
        row = out.setdefault(d, {})
        for k, _ in EFFECTS:
            v = num(r.get(k))
            if v is not None:
                row[k] = max(0.0, min(10.0, v))
    return out


# ---- pharmacokinetics ----------------------------------------------------------------------------------------------
def params(compound, sched=None):
    """(half_life_h, tmax_h or None, label, approved). Custom compounds take half_life_h and tmax_h from the schedule row."""
    sched = (sched or {}).get(compound, {})
    c = COMPOUNDS.get(compound)
    hl = sched.get("half_life_h") or (c["half_life_h"] if c else None)
    tmax = sched.get("tmax_h") or (c["tmax_h"] if c else None)
    label = c["label"] if c else (compound.replace("_", " ").title() if compound else "Custom")
    return hl, tmax, label, (c["approved"] if c else None)


def rates(hl, tmax):
    """ke from the half-life; ka from Tmax by solving tmax = ln(ka/ke) / (ka - ke). No Tmax gives ka=None (first-order decay only)."""
    ke = math.log(2) / hl
    if not tmax or tmax <= 0 or tmax >= 1 / ke:
        return None, ke
    lo, hi = ke * 1.0001, ke * 5000
    for _ in range(200):  # f(ka) falls as ka rises, so bisect
        mid = (lo + hi) / 2
        f = math.log(mid / ke) / (mid - ke)
        lo, hi = (mid, hi) if f > tmax else (lo, mid)
    return (lo + hi) / 2, ke


def one_dose(t_h, mg, ka, ke):
    """Amount (mg of the administered dose) still in the body t_h hours after one subcutaneous dose. Bioavailability is not applied."""
    if t_h < 0:
        return 0.0
    if ka is None:
        return mg * math.exp(-ke * t_h)
    return mg * ka / (ka - ke) * (math.exp(-ke * t_h) - math.exp(-ka * t_h))


def level_at(doses, when, ka, ke):
    """Superposition of every dose (mg) at datetime `when`."""
    tot = 0.0
    for d in doses:
        h = (when - d["t"]).total_seconds() / 3600
        if h >= 0:
            tot += one_dose(h, d["mg"], ka, ke)
    return tot


def steady_state(mg, interval_h, ka, ke):
    """(trough, peak) in mg at steady state for a repeated dose, by summing 12 half-lives of earlier doses."""
    n = int(math.ceil(12 * math.log(2) / ke / interval_h)) + 1
    trough = sum(one_dose(k * interval_h, mg, ka, ke) for k in range(1, n + 1))
    peak = 0.0
    for i in range(0, int(interval_h) + 1):
        peak = max(peak, sum(one_dose(i + k * interval_h, mg, ka, ke) for k in range(0, n + 1)))
    return trough, peak


def series(doses, start, end, ka, ke, step_h=2.0, extra=()):
    """[(datetime, level)] from start to end. `extra` adds scheduled future doses (projection)."""
    allv = list(doses) + list(extra)
    out, t = [], start
    while t <= end:
        out.append((t, level_at(allv, t, ka, ke)))
        t += dt.timedelta(hours=step_h)
    return out


# ---- sites ---------------------------------------------------------------------------------------------------------
def next_site(doses, compound=None):
    """Least recently used site, never the last one used. Ties fall back to SITES order. Returns (key, label)."""
    use = [d for d in doses if d["site"] in SITES and (compound is None or d["compound"] == compound)]
    last_used = {s: None for s in SITES}
    for d in use:
        last_used[d["site"]] = d["t"]
    last = use[-1]["site"] if use else None
    cands = [s for s in SITES if s != last]
    cands.sort(key=lambda s: (last_used[s] is not None, last_used[s] or dt.datetime.min, SITES.index(s)))
    return cands[0], SITE_LABEL[cands[0]]


# ---- status --------------------------------------------------------------------------------------------------------
def fmt_countdown(delta):
    s = int(delta.total_seconds())
    if s <= 0:
        return "Due now"
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d}d {h}h"
    return f"{h}h {m:02d}m" if h else f"{m}m"


def primary(doses, now):
    """Compound of the most recent dose on or before now."""
    past = [d for d in doses if d["t"] <= now]
    return past[-1]["compound"] if past else None


def active_compounds(doses, now, sched=None, limit=2):
    """Compounds with a dose within 3 intervals (or 21 days), most recent first."""
    out = []
    for d in reversed([x for x in doses if x["t"] <= now]):
        c = d["compound"]
        if c in out:
            continue
        iv = ((sched or {}).get(c, {}).get("interval_days") or (COMPOUNDS.get(c, {}).get("interval_days")) or 7)
        if (now - d["t"]).days <= max(21, 3 * iv):
            out.append(c)
    return out[:limit]


def status(root, now=None, compound=None):
    """Everything the images and the dashboard need. None if no dose has been logged."""
    root = Path(root)
    now = now or dt.datetime.now()
    doses_all = load_doses(root)
    sched = load_schedule(root)
    compound = norm_compound(compound) if compound else primary(doses_all, now)
    if not compound:
        return None
    doses = [d for d in doses_all if d["compound"] == compound]
    past = [d for d in doses if d["t"] <= now]
    if not past:
        return None
    hl, tmax, label, approved = params(compound, sched)
    if not hl:
        return None
    ka, ke = rates(hl, tmax)
    last = past[-1]
    sc = sched.get(compound, {})
    interval = sc.get("interval_days") or (COMPOUNDS.get(compound, {}).get("interval_days")) or 7
    nxt = sc.get("next_due")
    if nxt is None or nxt <= last["t"]:
        nxt = last["t"] + dt.timedelta(days=interval)
    cur = level_at(past, now, ka, ke)
    at_next = level_at(past, nxt, ka, ke)
    trough, peak = steady_state(last["mg"], interval * 24, ka, ke)
    nsite, nlabel = next_site(doses_all, None)
    elapsed = max(0.0, min(1.0, (now - last["t"]) / (nxt - last["t"]))) if nxt > last["t"] else 1.0
    steps = [d for d in past if d["mg"] == last["mg"]]
    return dict(compound=compound, label=label, brand=last["brand"] or sc.get("brand") or "", approved=approved,
                half_life_h=hl, tmax_h=tmax, ka=ka, ke=ke, interval_days=interval, now=now,
                last=dict(t=last["t"], mg=last["mg"], site=last["site"], site_label=SITE_LABEL.get(last["site"], ""), notes=last["notes"],
                          ago=fmt_countdown(now - last["t"]) if now > last["t"] else ""),
                next=dict(t=nxt, countdown=fmt_countdown(nxt - now), overdue=nxt <= now, elapsed=elapsed),
                level_now=cur, level_next=at_next, ss_trough=trough, ss_peak=peak,
                doses_at_current=len(steps), n_doses=len(past), doses=doses, all_doses=doses_all,
                next_site=nsite, next_site_label=nlabel, titration=sc.get("titration", ""))


def effects_summary(root, now, days=14):
    """Latest value, previous-week average and a daily list per side effect."""
    eff = load_effects(root)
    today = now.date()
    out = []
    for key, label in EFFECTS:
        vals = [(today - dt.timedelta(i), eff.get(today - dt.timedelta(i), {}).get(key)) for i in range(days - 1, -1, -1)]
        logged = [(d, v) for d, v in vals if v is not None]
        latest = None
        if logged and (today - logged[-1][0]).days <= 3:
            latest = logged[-1][1]
        cur_week = [v for d, v in logged if (today - d).days < 7]
        prev_week = [v for d, v in logged if 7 <= (today - d).days < 14]
        out.append(dict(key=key, label=label, latest=latest, series=[v for _, v in vals],
                        avg=(sum(cur_week) / len(cur_week) if cur_week else None),
                        prev=(sum(prev_week) / len(prev_week) if prev_week else None)))
    return out


# ---- coach line ----------------------------------------------------------------------------------------------------
def treatment_line(st, eff, data=None, now=None):
    """One neutral sentence. Never advises a dose, a schedule change or a compound."""
    now = now or st["now"]
    hi = [e for e in eff if e["latest"] is not None and e["latest"] >= 8 and e["key"] in ("nausea", "heartburn", "constipation")]
    if hi:
        return f'{hi[0]["label"]} is at {hi[0]["latest"]:.0f}/10. If it keeps up, contact your prescriber.'
    if data is not None:
        days = [now.date() - dt.timedelta(i) for i in range(3)]
        low = [d for d in days if d in data.food and data.food[d]["cal"] < 1200]
        if len(low) >= 2:
            return "Intake has been under 1,200 kcal. Eat to your floor and tell your prescriber if you can't."
        prot = [(data.food[d]["p"], data.target(d)["protein_g"]) for d in days if d in data.food]
        if prot and sum(p for p, _ in prot) < 0.85 * sum(t for _, t in prot):
            return "Appetite is low and protein is behind. Protein first at each meal."
        if not any(data.workout_sessions(now.date() - dt.timedelta(i)) for i in range(6)):
            return "No lifting in 5 days. Resistance training helps protect muscle on a GLP-1."
    sa = next((e for e in eff if e["key"] == "suppressed_appetite"), None)
    if sa and sa["latest"] is not None and sa["latest"] >= 6:
        return "Appetite is suppressed. Small, protein-rich meals keep intake up."
    if st["next"]["overdue"]:
        return "Your next dose was due. Check your label or prescriber about timing."
    return f'Next dose in {st["next"]["countdown"]}. The curve is an estimate, not a blood level.'


# ---- logging CLI ---------------------------------------------------------------------------------------------------
def append_row(path, fields, row):
    p = Path(path)
    new = not p.exists() or p.stat().st_size == 0
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def cmd_log(a):
    c = norm_compound(a.compound)
    site = norm_site(a.site)
    if site and site not in SITES:
        sys.exit(f"unknown site {a.site!r}; use one of: {', '.join(SITES)}")
    when = pdt(a.datetime) if a.datetime else dt.datetime.now().replace(second=0, microsecond=0)
    if when is None:
        sys.exit("bad --datetime, use 'YYYY-MM-DD HH:MM'")
    if a.mg <= 0:
        sys.exit("--mg must be above 0")
    row = dict(datetime=when.strftime("%Y-%m-%d %H:%M"), compound=c, brand=a.brand or "", dose_mg=f"{a.mg:g}", site=site, notes=a.notes or "")
    append_row(Path(a.data) / "meds.csv", DOSE_FIELDS, row)
    out = dict(logged=row)
    cc = COMPOUNDS.get(c)
    if cc and not cc["approved"]:
        out["note"] = f"{cc['label']} is not FDA-approved. Say that once, neutrally, and keep tracking."
    elif not cc:
        out["note"] = "Custom compound: set its half-life with `schedule --half-life-h` so the level curve works."
    print(json.dumps(out))


def cmd_schedule(a):
    c = norm_compound(a.compound)
    nd = pdt(a.next_due) if a.next_due else None
    if a.next_due and nd is None:
        sys.exit("bad --next-due, use 'YYYY-MM-DD HH:MM'")
    row = dict(compound=c, brand=a.brand or "", interval_days=a.interval_days if a.interval_days is not None else "",
               next_due=nd.strftime("%Y-%m-%d %H:%M") if nd else "", dose_mg=a.mg if a.mg is not None else "", titration=a.titration or "",
               half_life_h=a.half_life_h if a.half_life_h is not None else "", tmax_h=a.tmax_h if a.tmax_h is not None else "")
    old = load_schedule(a.data)
    p = Path(a.data) / "med_schedule.csv"
    rows = [r for r in read_rows(p) if norm_compound(r.get("compound")) != c]
    prev = old.get(c, {})
    for k, v in row.items():  # keep earlier values for fields not passed again
        if v == "" and prev.get(k) not in (None, ""):
            row[k] = prev[k].strftime("%Y-%m-%d %H:%M") if isinstance(prev[k], dt.datetime) else prev[k]
    rows.append(row)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHED_FIELDS)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in SCHED_FIELDS} for r in rows)
    print(json.dumps(dict(schedule=row)))


def cmd_effects(a):
    day = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    vals = dict(nausea=a.nausea, heartburn=a.heartburn, food_noise=a.food_noise, suppressed_appetite=a.appetite,
                fatigue=a.fatigue, constipation=a.constipation)
    p = Path(a.data) / "side_effects.csv"
    rows = read_rows(p)
    cur = next((r for r in rows if r.get("date") == day.isoformat()), None)
    if cur is None:
        cur = dict(date=day.isoformat())
        rows.append(cur)
    for k, v in vals.items():
        if v is not None:
            if not 0 <= v <= 10:
                sys.exit(f"{k} must be 0 to 10")
            cur[k] = f"{v:g}"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EFFECT_FIELDS)
        w.writeheader()
        w.writerows({k: r.get(k, "") for k in EFFECT_FIELDS} for r in rows)
    print(json.dumps(dict(date=day.isoformat(), **{k: cur.get(k, "") for k, _ in EFFECTS})))


def cmd_status(a):
    now = pdt(a.now) if a.now else dt.datetime.now()
    st = status(a.data, now, a.compound)
    if not st:
        print(json.dumps(dict(on_treatment=False)))
        return
    eff = effects_summary(a.data, now)
    out = dict(on_treatment=True, compound=st["compound"], brand=st["brand"], approved=st["approved"],
               level_now_mg=round(st["level_now"], 3), level_at_next_dose_mg=round(st["level_next"], 3),
               steady_state_trough_mg=round(st["ss_trough"], 3), steady_state_peak_mg=round(st["ss_peak"], 3),
               last_dose=dict(time=st["last"]["t"].isoformat(" ", "minutes"), mg=st["last"]["mg"], site=st["last"]["site_label"]),
               next_dose=dict(time=st["next"]["t"].isoformat(" ", "minutes"), countdown=st["next"]["countdown"], overdue=st["next"]["overdue"]),
               next_site=st["next_site_label"], doses_logged=st["n_doses"],
               side_effects={e["key"]: e["latest"] for e in eff}, estimate=True)
    print(json.dumps(out))


def selftest():
    """Check the model against the published half-lives and Tmax. Prints a table; exits 1 on a miss."""
    bad = 0
    print("compound      half-life  fitted  tmax  fitted-peak  ka(/h)   ss peak/trough (1 mg weekly or daily)")
    for key, c in COMPOUNDS.items():
        ka, ke = rates(c["half_life_h"], c["tmax_h"])
        peak_t = max(range(0, 24 * 14 * 4), key=lambda i: one_dose(i / 4, 1, ka, ke)) / 4
        t1, t2 = 24 * 40, 24 * 40 + c["half_life_h"]
        fit_hl = c["half_life_h"] * math.log(2) / math.log(one_dose(t1, 1, ka, ke) / one_dose(t2, 1, ka, ke))
        tr, pk = steady_state(1.0, c["interval_days"] * 24, ka, ke)
        ok = abs(peak_t - c["tmax_h"]) <= 0.5 and abs(fit_hl - c["half_life_h"]) / c["half_life_h"] < 0.01
        bad += not ok
        print(f"{key:<13} {c['half_life_h']:>7.0f} h {fit_hl:>6.1f} {c['tmax_h']:>4.0f} h {peak_t:>8.1f} h  {ka:>7.4f}  {pk:.2f} / {tr:.2f}  {'ok' if ok else 'MISS'}")
    # first-order fallback
    _, ke = rates(100, None)
    ok = abs(one_dose(100, 1, None, ke) - 0.5) < 1e-9
    bad += not ok
    print("first-order fallback halves in one half-life:", "ok" if ok else "MISS")
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["log", "schedule", "effects", "status", "selftest"])
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--compound")
    ap.add_argument("--brand")
    ap.add_argument("--mg", type=float)
    ap.add_argument("--site")
    ap.add_argument("--datetime")
    ap.add_argument("--notes")
    ap.add_argument("--interval-days", type=float, dest="interval_days")
    ap.add_argument("--next-due", dest="next_due")
    ap.add_argument("--titration")
    ap.add_argument("--half-life-h", type=float, dest="half_life_h")
    ap.add_argument("--tmax-h", type=float, dest="tmax_h")
    ap.add_argument("--date")
    ap.add_argument("--now")
    for k, _ in EFFECTS:
        ap.add_argument("--" + k.replace("_", "-").replace("suppressed-appetite", "appetite"), type=float, dest=("appetite" if k == "suppressed_appetite" else k))
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    if a.cmd == "log":
        if not a.compound or a.mg is None:
            sys.exit("log needs --compound and --mg")
        cmd_log(a)
    elif a.cmd == "schedule":
        if not a.compound:
            sys.exit("schedule needs --compound")
        cmd_schedule(a)
    elif a.cmd == "effects":
        cmd_effects(a)
    else:
        cmd_status(a)


if __name__ == "__main__":
    main()
