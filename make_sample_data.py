"""Generate fake sample CSVs for testing charts.py: python make_sample_data.py DIR"""
import csv, random, sys, datetime as dt
from pathlib import Path
root = Path(sys.argv[1]); root.mkdir(parents=True, exist_ok=True)
random.seed(7)
end = dt.date(2026, 11, 18)
def w(name, header, rows):
    with open(root / name, "w", newline="") as f:
        c = csv.writer(f); c.writerow(header); c.writerows(rows)
w("targets.csv", "effective_date,units,calories,protein_g,carbs_g,fat_g,fiber_g,water_ml,goal_weight_kg,goal_type,step_goal,sleep_goal_h,sessions_per_week".split(","),
  [["2026-09-01","imperial",2200,170,230,65,30,3000,78.5,"lose",9000,7.5,4]])
food, water, weight, work, sleep, steps = [], [], [], [], [], []
wt = 88.4
for i in range(75, -1, -1):
    d = end - dt.timedelta(i)
    wt -= random.uniform(0.02, 0.2) if i % 2 else random.uniform(-0.04, 0.12)
    if random.random() > 0.1: weight.append([d, round(wt + random.uniform(-0.5, 0.5), 1)])
    if random.random() > 0.08:
        tot = 1660 if d == end else random.uniform(1900, 2500)
        for meal, share, hm in (("breakfast", .25, "08:10"), ("lunch", .30, "12:40"), ("dinner", .35, "19:05"), ("snack", .10, "15:30")):
            k = tot * share
            food.append([d, hm, meal, f"{meal} item", "off", 1, round(k), round(k*.30/4), round(k*.42/4), round(k*.28/9), round(k/100,1), ""])
        water.append([d, "12:00", 1600 if d == end else random.randint(1800, 3400)])
    if d.weekday() in (0, 2, 4, 5) and random.random() > .15:
        work.append([d, "lift", "Upper/lower", 55, 250, ""])
    if d.weekday() == 6: work.append([d, "walk", "Long walk", 60, 200, ""])
    if random.random() > .1: sleep.append([d, round(random.uniform(5.8, 8.4), 1), random.randint(2, 5)])
    steps.append([d, 6357 if d == end else random.randint(4500, 12500)])
w("food_log.csv","date,time,meal,food,source,qty,calories,protein_g,carbs_g,fat_g,fiber_g,barcode".split(","), food)
w("water.csv",["date","time","ml"], water)
w("weight.csv",["date","weight_kg"], weight)
w("workouts.csv","date,type,name,duration_min,est_kcal,notes".split(","), work)
w("sleep.csv",["date","hours","quality"], sleep)
w("steps.csv",["date","steps"], steps)
w("measurements.csv","date,waist_cm,hips_cm,chest_cm,arm_cm,thigh_cm".split(","),
  [["2026-10-18",94.0,104.0,106.0,35.5,60.0],["2026-11-18",91.5,103.0,106.5,36.0,59.5]])

# ---- medication sample: tirzepatide 2.5 mg x4 weekly, then 5 mg x3, about 6 weeks of history, Mondays 19:30 ----
sites = ["abdomen_ul", "thigh_r", "arm_l", "abdomen_lr", "thigh_l", "arm_r", "abdomen_ur"]
start = dt.date(2026, 10, 5)
doses = []
for i in range(7):
    d = start + dt.timedelta(7 * i)
    if d > end:
        break
    doses.append([f"{d} 19:30", "tirzepatide", "Zepbound", 2.5 if i < 4 else 5, sites[i], "first dose" if i == 0 else ("dose step up" if i == 4 else "")])
w("meds.csv", "datetime,compound,brand,dose_mg,site,notes".split(","), doses)
last = dt.date.fromisoformat(doses[-1][0][:10])
w("med_schedule.csv", "compound,brand,interval_days,next_due,dose_mg,titration,half_life_h,tmax_h".split(","),
  [["tirzepatide", "Zepbound", 7, f"{last + dt.timedelta(7)} 19:30", 5, "2.5x4>5x4>7.5x4", "", ""]])
rnd = random.Random(11)
eff = []
for i in range(41, -1, -1):
    d = end - dt.timedelta(i)
    since = [(d - dt.date.fromisoformat(x[0][:10])).days for x in doses if dt.date.fromisoformat(x[0][:10]) <= d]
    if not since:
        continue
    k, mg = min(since), [x[3] for x in doses if dt.date.fromisoformat(x[0][:10]) <= d][-1]
    bump = max(0.0, 1.0 - abs(k - 1.5) / 3.0)          # side effects peak 1 to 2 days after a dose
    step = 1.4 if mg > 2.5 else 1.0
    r = lambda base, amp: max(0, min(10, round(base + amp * bump * step + rnd.uniform(-0.6, 0.6))))  # noqa: E731
    if rnd.random() > 0.12:
        eff.append([d, r(0.5, 4.5), r(0.3, 1.8), r(2.0, 1.5), r(3.5, 2.5), r(1.5, 2.5), r(1.0, 2.0)])
w("side_effects.csv", "date,nausea,heartburn,food_noise,suppressed_appetite,fatigue,constipation".split(","), eff)

# ---- config: every module on, light theme (what onboarding writes when the user opts into everything) ----
import json
(root / "config.json").write_text(json.dumps(dict(version=1, theme="light", palette=None,
    modules=dict(workouts=True, nutrition=True, activity=True, health=True, peptides=True), sources=dict(apple_health=False)), indent=2) + "\n")
