"""Self-test for a brand-new user's first day: python test_firstday.py  (HTML only, no Chromium needed)
One entry logged, no targets, no schedule, one weigh-in, sleep logged on an earlier day: nothing crashes, nothing is invented."""
import json, subprocess, sys, tempfile, datetime as dt
from pathlib import Path
here = Path(__file__).parent
sys.path.insert(0, str(here))
import config as CFG, charts as C, scoring as S, render_core as rc, render_modules as RM

DAY, NOW = dt.date(2026, 11, 18), dt.datetime(2026, 11, 18, 18, 40)
py = sys.executable
FOOD = "date,time,meal,food,source,qty,calories,protein_g,carbs_g,fat_g,fiber_g,barcode\n2026-11-18,08:00,breakfast,2 eggs and toast,estimate,,260,16,18,13,1,\n"

def run(script, *a):
    r = subprocess.run([py, str(here / script), *a], capture_output=True, text=True)
    assert r.returncode == 0, (script, a, r.stderr[-500:])
    return r.stdout

def data_dir(**files):
    d = Path(tempfile.mkdtemp())
    for name, text in files.items():
        (d / f"{name}.csv").write_text(text)
    return d

def pages(d, day=DAY):
    cfg = CFG.load(d)
    rc.set_theme("light", None)
    data = C.Data(str(d))
    data.off = {k for k in CFG.ORDER if not cfg["modules"].get(k)}
    shown = CFG.visible(str(d))
    units = C.pick_units(data, "auto", day)
    return data, shown, units, RM.overview_html(data, day, units, None, shown)

# 1. The skipper: one meal, no config, no targets. Only Diet and macros appears, and the footer says the targets are placeholders.
d = data_dir(food_log=FOOD)
data, shown, units, html = pages(d)
assert shown == ["nutrition"] and "Diet and macros" in html and "starting targets" in html
assert all(w not in html for w in ("Recovery", "Workouts", "Health", "Steps and activity"))
d = data_dir(food_log=FOOD, targets="effective_date,units,calories,protein_g,carbs_g,fat_g,fiber_g,water_ml,goal_weight_kg,goal_type,step_goal,sleep_goal_h,sessions_per_week\n2026-11-18,imperial,1600,128,160,50,22,2540,72.6,lose,8000,7.5,3\n")
assert "starting targets" not in pages(d)[3]                  # real targets: no note

# 2. One weigh-in is a starting point: no 0.0 change, no fake trend, no weight image.
d = data_dir(food_log=FOOD, weight="date,weight_kg\n2026-11-18,78.0\n", sleep="date,hours,quality\n2026-11-17,7.1,3\n")
data, shown, units, html = pages(d)
assert "first weigh-in" in html and "steady" not in html
page = RM.DETAIL["health"](data, DAY, units, None)
assert "First weigh-in logged" in page and "0.0 lb" not in page and "7-day average" not in page
assert "h most recent night" in page                          # sleep was logged yesterday, not today: no crash, honest label
r = subprocess.run([py, str(here / "charts.py"), "weight", "--data", str(d), "--out", str(d / "o"), "--date", "2026-11-18"], capture_output=True, text=True)
assert "only one weigh-in" in r.stderr

# 3. Readiness on day one says what it rests on.
d = data_dir(food_log=FOOD, sleep="date,hours,quality\n2026-11-18,7.1,3\n")
data, shown, units, html = pages(d)
assert S.pillars(data, DAY)["recovery"] is not None
assert "sleep alone" in S.coach_line(data, DAY, "daily", units, now=NOW)

# 4. A dose with no schedule: logged and shown, but no next-dose date, countdown or projected doses are invented.
d = Path(tempfile.mkdtemp())
CFG.save(str(d), dict(CFG.load(str(d)), modules=dict(workouts=False, nutrition=True, activity=False, health=False, peptides=True)))
run("meds.py", "log", "--data", str(d), "--compound", "semaglutide", "--mg", "0.25", "--datetime", "2026-11-18 09:00")
(d / "food_log.csv").write_text(FOOD)
st = json.loads(run("meds.py", "status", "--data", str(d), "--date", "2026-11-18"))
assert st["scheduled"] is False and st["next_dose"] is None
data, shown, units, html = pages(d)
assert "Peptides and meds" in html and "no schedule set yet" in html and "Next dose Wed" not in html
page = RM.DETAIL["peptides"](data, DAY, units, None)
assert "Not set yet" in page and "At next dose" not in page and "if the schedule is kept" not in page and "weekly" not in page
import meds as M
st2 = M.status(d, NOW)
assert "No schedule saved" in M.treatment_line(st2, [], None, NOW)
# giving a schedule brings the dates back
run("meds.py", "schedule", "--data", str(d), "--compound", "semaglutide", "--interval-days", "7", "--next-due", "2026-11-25 09:00")
data, shown, units, html = pages(d)
page = RM.DETAIL["peptides"](data, DAY, units, None)
assert "At next dose" in page and "weekly" in page and "Next dose Wed" in html

# 5. A half-logged morning is not "behind on protein"; the evening is allowed to say so.
d = data_dir(food_log=FOOD)
CFG.save(str(d), dict(CFG.load(str(d)), modules=dict(workouts=False, nutrition=True, activity=False, health=False, peptides=True)))
run("meds.py", "log", "--data", str(d), "--compound", "tirzepatide", "--mg", "2.5", "--datetime", "2026-11-18 07:30")
run("meds.py", "schedule", "--data", str(d), "--compound", "tirzepatide", "--interval-days", "7", "--next-due", "2026-11-25 07:30")
data = C.Data(str(d))
morning, evening = dt.datetime(2026, 11, 18, 10, 0), dt.datetime(2026, 11, 18, 18, 40)
assert "Protein has run behind" not in M.treatment_line(M.status(d, morning), [], data, morning)
assert "Protein has run behind" in M.treatment_line(M.status(d, evening), [], data, evening)
print("test_firstday ok")
