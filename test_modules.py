"""Self-test for modules, themes and the dashboard: python test_modules.py  (HTML checks need no Chromium; PNG checks run when it is installed)"""
import json, re, subprocess, sys, tempfile, datetime as dt
from pathlib import Path
here = Path(__file__).parent
sys.path.insert(0, str(here))
import config as CFG
import themes as T

py = sys.executable
def run(script, *a, ok=True):
    r = subprocess.run([py, str(here / script), *a], capture_output=True, text=True)
    assert (r.returncode == 0) == ok, (script, a, r.stdout[-400:], r.stderr[-600:])
    return r.stdout

def sample():
    d = tempfile.mkdtemp()
    run("make_sample_data.py", d)
    return d

DAY = dt.date(2026, 11, 18)

# 1. Config: defaults, round trip, enable and disable. Re-enabling brings the module back with its data untouched.
empty = tempfile.mkdtemp()
c = CFG.load(empty)
assert c["modules"] == dict(workouts=True, nutrition=True, activity=True, health=True, peptides=False) and c["theme"] == "light"
assert CFG.visible(empty) == []                                 # on, but no data yet: nothing is drawn
d = sample()
assert CFG.visible(d) == CFG.ORDER                              # everything on, everything has data
run("config.py", "disable", "peptides", "--data", d)
assert CFG.visible(d) == ["workouts", "nutrition", "activity", "health"]
assert (Path(d) / "meds.csv").exists()                          # disabling never deletes data
run("config.py", "enable", "peptides", "--data", d)
assert CFG.visible(d) == CFG.ORDER
run("config.py", "init", "--data", d, "--modules", "workouts,health", "--theme", "dark")
assert CFG.visible(d) == ["workouts", "health"] and CFG.load(d)["theme"] == "dark"
run("config.py", "init", "--data", d, "--modules", "bogus", ok=False)
run("config.py", "theme", "light", "--data", d)
assert CFG.resolve_theme(d) == "light" and CFG.resolve_theme(d, "dark") == "dark"
# enabled but unfed: reported as waiting, not drawn
d2 = sample()
(Path(d2) / "steps.csv").write_text("date,steps\n")
st = CFG.status(d2)
assert "activity" not in st["shown"] and [w["module"] for w in st["waiting"]] == ["activity"]
sch = json.loads((Path(d) / "config.json").read_text())
assert set(sch) == {"version", "theme", "palette", "modules", "sources"} and set(sch["modules"]) == set(CFG.ORDER)

# 2. Palettes: contrast floors, a real light and dark, nothing pink, purple or near-black.
for name in T.PALETTES:
    for mode in T.MODES:
        rep = T.report(name)[mode]
        assert rep["text"] >= 12 and rep["text3"] >= 4.5 and rep["hue_min"] >= 3.0, (name, mode, rep)
        tk = T.tokens(name, mode)
        assert T.to_oklab(tk["bg"])[0] > 0.9 if mode == "light" else 0.18 < T.to_oklab(tk["bg"])[0] < 0.4, (name, mode)
        for key, hexv in tk["hues"].items():
            h = T.hue_of(hexv)
            assert not (285 <= h <= 360), (name, mode, key, hexv, h)   # no purple, magenta or pink
    assert T.tokens(name, "dark")["bg"].lower() not in ("#000000", "#0a0a0a", "#0b0b0f", "#111111")
assert T.tokens("lagoon", "light")["bg"] != T.tokens("lagoon", "dark")["bg"]

# 3. Overview HTML draws only the modules that are shown. No placeholder for the others.
import render_core as rc
import render_modules as RM
import charts as C
import scoring as S

def overview(dd, **kw):
    cfg = CFG.load(dd)
    rc.set_theme(kw.get("theme", "light"), None)
    data = C.Data(dd)
    data.off = {k for k in CFG.ORDER if not cfg["modules"].get(k)}
    shown = CFG.visible(dd)
    return RM.overview_html(data, DAY, C.pick_units(data, "auto", DAY), None, shown), data, shown

TITLES = {k: CFG.MODULES[k]["label"] for k in CFG.ORDER}
d3 = sample()
html, data, shown = overview(d3)
for k in CFG.ORDER:
    assert TITLES[k] in html, k
run("config.py", "disable", "peptides", "--data", d3)
html, data, shown = overview(d3)
assert "Peptides and meds" not in html and "Tirzepatide" not in html and "peptides" not in shown
for k in ("workouts", "nutrition", "activity", "health"):
    assert TITLES[k] in html
for bad in ("No data", "no data", "Connect", "connect", "Coming soon", "Not set up", "\u2013 \u2013"):
    assert bad not in html, bad
run("config.py", "init", "--data", d3, "--modules", "nutrition")
html, data, shown = overview(d3)
assert shown == ["nutrition"] and "Recovery" not in html and "Workouts" not in html and "Diet and macros" in html
# scoring ignores a module that is off: no sleep, no recovery without Health
assert S.pillars(data, DAY)["recovery"] is None
run("config.py", "init", "--data", d3, "--modules", "workouts,nutrition,activity,health,peptides")
html, data, shown = overview(d3)
assert S.pillars(data, DAY)["recovery"] is not None and "Peptides and meds" in html   # re-enabled: back, nothing lost
# every detail page has a way back to the overview; only shown modules have one
cfg = CFG.load(d3)
for k in CFG.ORDER:
    page = RM.DETAIL[k](data, DAY, C.pick_units(data, "auto", DAY), None)
    assert page and "Overview" in page, k
# light and dark differ and both are complete pages
rc.set_theme("dark", None)
dark = RM.overview_html(data, DAY, C.pick_units(data, "auto", DAY), None, shown)
assert dark != html and T.tokens(T.DEFAULT_PALETTE, "dark")["bg"].lower() in dark.lower()
rc.set_theme("light", None)

# 4. Dashboard data and template.
import dashboard_data as DD
d4 = sample()
dash, photo = DD.build(Path(d4), DAY, "Alex", "auto")
assert dash["shown"] == CFG.ORDER and all(dash[k] for k in CFG.ORDER) and dash["name"] == "Alex"
assert len(dash["pal"]["light"]) == 6 and len(dash["pal"]["dark"]) == 6
run("config.py", "disable", "peptides", "--data", d4)
run("config.py", "disable", "workouts", "--data", d4)
dash, _ = DD.build(Path(d4), DAY, "Alex", "auto")
assert dash["peptides"] is None and dash["workouts"] is None and dash["shown"] == ["nutrition", "activity", "health"]
run("config.py", "enable", "peptides", "--data", d4)
dash, _ = DD.build(Path(d4), DAY, "Alex", "auto")
assert dash["peptides"] and dash["shown"][-1] == "peptides"
src = run("dashboard_data.py", "full", "--data", d4, "--name", "Alex", "--date", DAY.isoformat())
assert "__DATA__" not in src and "__PHOTO__" not in src and '"workouts": null' in src and "Alex" in src
tpl = (here / "dashboard.canvas.tsx.template").read_text()
# the host re-themes a whole page when it sees a neutral-filled rect, so none may exist
assert not re.search(r'<rect[^>]*fill=\{(p\.)?(ink|muted|check)\}', tpl) and not re.search(r'<rect[^>]*fill="#(fff|000)', tpl, re.I)
assert "useState" in tpl and "Segmented" in tpl and 'setView("overview")' in tpl

# 5. PNGs (Chromium only): overview and detail respect modules and theme.
if rc.chromium_available():
    out = tempfile.mkdtemp()
    run("config.py", "enable", "workouts", "--data", d4)
    run("config.py", "disable", "peptides", "--data", d4)
    o = run("charts.py", "overview", "--data", d4, "--out", out, "--date", DAY.isoformat(), "--theme", "dark")
    assert (Path(out) / f"overview_{DAY}.png").exists() and "SUMMARY" in o
    run("charts.py", "detail", "peptides", "--data", d4, "--out", out, "--date", DAY.isoformat())   # off: no image, not an error
    assert not list(Path(out).glob("detail_peptides_*"))
    run("charts.py", "detail", "--data", d4, "--out", out, "--date", DAY.isoformat(), "--theme", "light")
    assert sorted(p.name.split("_")[1] for p in Path(out).glob("detail_*")) == ["activity", "health", "nutrition", "workouts"]
    from PIL import Image
    a, b = Image.open(Path(out) / f"overview_{DAY}.png"), Image.open(Path(out) / f"detail_health_{DAY}.png")
    assert a.width == b.width == 1080
else:
    print("note: Chromium not installed, PNG checks skipped")
print("test_modules ok")
