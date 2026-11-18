"""Self-test for meds.py: python test_meds.py  (no Chromium needed; renders are checked in test_render when Chromium is present)"""
import datetime as dt, json, math, subprocess, sys, tempfile
from pathlib import Path
here = Path(__file__).parent
sys.path.insert(0, str(here))
import meds as M

# 1. Model vs the sourced parameters: half-life, Tmax, and weekly accumulation (tirzepatide label: ratio ~1.6 after 4 weeks).
for key, c in M.COMPOUNDS.items():
    ka, ke = M.rates(c["half_life_h"], c["tmax_h"])
    peak = max(range(0, 24 * 14 * 4), key=lambda i: M.one_dose(i / 4, 1, ka, ke)) / 4
    assert abs(peak - c["tmax_h"]) <= 0.5, (key, peak)
    ratio = M.one_dose(24 * 40, 1, ka, ke) / M.one_dose(24 * 40 + c["half_life_h"], 1, ka, ke)
    assert abs(ratio - 2) < 0.03, (key, ratio)   # terminal slope halves per half-life
ka, ke = M.rates(120, 24)
tr, pk = M.steady_state(1.0, 168, ka, ke)
assert 1.4 < sum(M.one_dose(168 * k + 168 * 3, 1, ka, ke) for k in range(0, 4)) / M.one_dose(168 * 3, 1, ka, ke) < 2.1
assert pk > tr > 0
# superposition: two doses add
t0 = dt.datetime(2026, 1, 1, 8)
d = [dict(t=t0, mg=2.5, compound="tirzepatide"), dict(t=t0 + dt.timedelta(days=7), mg=2.5, compound="tirzepatide")]
at = t0 + dt.timedelta(days=9)
assert math.isclose(M.level_at(d, at, ka, ke), M.one_dose(216, 2.5, ka, ke) + M.one_dose(48, 2.5, ka, ke))
assert M.level_at(d, t0 - dt.timedelta(hours=1), ka, ke) == 0
# 2. Site rotation: never the last site, uses all eight before repeating.
seq, doses = [], []
for i in range(16):
    k, _ = M.next_site(doses, "tirzepatide")
    assert not doses or k != doses[-1]["site"]
    seq.append(k)
    doses.append(dict(t=t0 + dt.timedelta(days=7 * i), mg=2.5, compound="tirzepatide", site=k))
assert len(set(seq[:8])) == 8 and seq[:8] == seq[8:16], seq
# 3. CLI round trip in a temp dir.
tmp = tempfile.mkdtemp()
def run(*a, ok=True, data=None):
    r = subprocess.run([sys.executable, str(here / "meds.py"), "--data", data or tmp, *a], capture_output=True, text=True)
    assert (r.returncode == 0) == ok, (a, r.stdout, r.stderr)
    return r.stdout
run("log", "--compound", "Zepbound", "--mg", "2.5", "--site", "stomach_upper_left", "--datetime", "2026-11-02 19:30")
run("log", "--compound", "tirzepatide", "--mg", "2.5", "--site", "thigh_r", "--datetime", "2026-11-09 19:30")
out = run("log", "--compound", "retatrutide", "--mg", "2", "--datetime", "2026-11-09 08:00")
assert "FDA" in out
run("schedule", "--compound", "tirzepatide", "--interval-days", "7", "--next-due", "2026-11-16 19:30", "--titration", "2.5x4>5x4")
run("effects", "--date", "2026-11-10", "--nausea", "4", "--appetite", "7")
run("effects", "--date", "2026-11-11", "--nausea", "11", ok=False)           # out of range
run("log", "--compound", "tirzepatide", "--mg", "-1", ok=False)             # bad dose
st = json.loads(run("status", "--compound", "tirzepatide", "--now", "2026-11-12 12:00"))
assert st["on_treatment"] and st["compound"] == "tirzepatide" and st["doses_logged"] == 2 and st["last_dose"]["mg"] == 2.5
assert st["last_dose"]["site"] == "Right thigh" and st["next_site"] != "Right thigh"
assert 0 < st["level_now_mg"] < 2 * 2.5 and st["steady_state_peak_mg"] > st["steady_state_trough_mg"] > 0
assert st["next_dose"]["countdown"] == "4d 7h", st["next_dose"]
assert st["side_effects"]["nausea"] == 4 and st["side_effects"]["suppressed_appetite"] == 7 and st["estimate"] is True
assert json.loads(run("status", data=tempfile.mkdtemp()))["on_treatment"] is False   # empty data dir
# the log is plain CSV with the documented header
head = (Path(tmp) / "meds.csv").read_text().splitlines()[0]
assert head == ",".join(M.DOSE_FIELDS), head
# custom compound: logs with a note; the curve needs a half-life from `schedule`
assert "half-life" in run("log", "--compound", "mystery", "--mg", "1", "--datetime", "2026-11-10 08:00")
run("schedule", "--compound", "mystery", "--interval-days", "3", "--next-due", "2026-11-13 08:00", "--half-life-h", "30")
st = json.loads(run("status", "--compound", "mystery", "--now", "2026-11-11 08:00"))
assert 0.5 < st["level_now_mg"] < 1.0, st
print("test_meds ok")
