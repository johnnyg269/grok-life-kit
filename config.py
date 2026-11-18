#!/usr/bin/env python3
"""Grok Life config: which modules the user opted into, and their light or dark preference. Lives in DATA/config.json.

  python config.py init [--modules workouts,nutrition,activity,health,peptides] [--theme light|dark] [--palette NAME]
  python config.py show
  python config.py enable peptides        # re-enabling restores the module with its old data, nothing is deleted
  python config.py disable peptides
  python config.py theme dark             # the saved preference every image uses unless --theme is passed
  python config.py status [--date YYYY-MM-DD]   # per module: enabled, has data, shown; and what is waiting for a source

Schema (config.json):
  {"version": 1, "theme": "light" | "dark", "palette": "lagoon",
   "modules": {"workouts": true, "nutrition": true, "activity": true, "health": true, "peptides": false},
   "sources": {"apple_health": false}}

Rule used everywhere (images and dashboard): a module is SHOWN when it is enabled AND its source files hold at least one row.
An enabled module whose data has not arrived yet is simply not drawn: no placeholder, no empty card. `status` lists it under
`waiting`, and the bot says so once in chat (for example "Activity is on and starts showing when steps arrive from Apple Health").
"""
import argparse
import csv
import json
import sys
from pathlib import Path

DEFAULT_DATA = Path("/workspace/macro-coach")
VERSION = 1

# key, label, the CSV files that feed it, what to tell the user while it waits
MODULES = {
    "workouts": dict(label="Workouts", sources=["workouts.csv"], hint="Log a workout and it appears."),
    "nutrition": dict(label="Diet and macros", sources=["food_log.csv"], hint="Log a meal and it appears."),
    "activity": dict(label="Steps and activity", sources=["steps.csv"], hint="Steps arrive from Apple Health (section 10), or log them by hand."),
    "health": dict(label="Health", sources=["weight.csv", "sleep.csv", "water.csv"], hint="Weight, sleep or water, from Apple Health or by hand."),
    "peptides": dict(label="Peptides and meds", sources=["meds.csv"], hint="Log a first dose with meds.py and it appears."),
}
ORDER = ["workouts", "nutrition", "activity", "health", "peptides"]
DEFAULT_ENABLED = dict(workouts=True, nutrition=True, activity=True, health=True, peptides=False)
THEMES = ("light", "dark")


def path(root):
    return Path(root) / "config.json"


def default():
    return dict(version=VERSION, theme="light", palette=None, modules=dict(DEFAULT_ENABLED), sources=dict(apple_health=False))


def has_rows(root, name):
    p = Path(root) / name
    if not p.exists():
        return False
    with open(p, newline="", encoding="utf-8") as f:
        return sum(1 for r in csv.reader(f) if r and any(c.strip() for c in r)) > 1  # header plus one row


def load(root):
    """Config with defaults filled in. With no file, behaviour matches the old one: everything on, peptides on once meds.csv has a dose."""
    cfg = default()
    p = path(root)
    if p.exists():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}
        for k in ("theme", "palette"):
            if raw.get(k):
                cfg[k] = raw[k]
        cfg["modules"].update({k: bool(v) for k, v in (raw.get("modules") or {}).items() if k in MODULES})
        cfg["sources"].update(raw.get("sources") or {})
    elif has_rows(root, "meds.csv"):
        cfg["modules"]["peptides"] = True
    if cfg["theme"] not in THEMES:
        cfg["theme"] = "light"
    return cfg


def save(root, cfg):
    p = path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    out = dict(version=VERSION, theme=cfg["theme"], palette=cfg.get("palette"),
               modules={k: bool(cfg["modules"].get(k, DEFAULT_ENABLED[k])) for k in ORDER}, sources=cfg.get("sources", {}))
    p.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def enabled(root, key):
    return bool(load(root)["modules"].get(key))


def visible(root):
    """Modules to draw, in display order: enabled and fed by at least one row of data."""
    cfg = load(root)
    return [k for k in ORDER if cfg["modules"].get(k) and any(has_rows(root, s) for s in MODULES[k]["sources"])]


def status(root):
    cfg = load(root)
    rows, waiting = [], []
    for k in ORDER:
        on = bool(cfg["modules"].get(k))
        data = any(has_rows(root, s) for s in MODULES[k]["sources"])
        rows.append(dict(module=k, label=MODULES[k]["label"], enabled=on, has_data=data, shown=on and data))
        if on and not data:
            waiting.append(dict(module=k, label=MODULES[k]["label"], waiting_for=" or ".join(MODULES[k]["sources"]), hint=MODULES[k]["hint"]))
    return dict(theme=cfg["theme"], palette=cfg["palette"], modules=rows, shown=[r["module"] for r in rows if r["shown"]], waiting=waiting)


def resolve_theme(root, override=None):
    """The theme an image uses: --theme if given, else the saved preference, else light."""
    return override if override in THEMES else load(root)["theme"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["init", "show", "enable", "disable", "theme", "status"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--modules", help="init: comma list of modules to turn on; all others are off")
    ap.add_argument("--theme", dest="theme_opt", choices=THEMES)
    ap.add_argument("--palette")
    a = ap.parse_args(argv)
    root = Path(a.data)
    cfg = load(root)
    if a.cmd == "init":
        want = [m.strip() for m in (a.modules or ",".join(k for k in ORDER if DEFAULT_ENABLED[k])).split(",") if m.strip()]
        bad = [m for m in want if m not in MODULES]
        if bad:
            sys.exit(f"unknown module {bad[0]!r}; use: {', '.join(ORDER)}")
        cfg["modules"] = {k: k in want for k in ORDER}
        if a.theme_opt:
            cfg["theme"] = a.theme_opt
        if a.palette:
            cfg["palette"] = a.palette
        print(json.dumps(save(root, cfg)))
    elif a.cmd in ("enable", "disable"):
        if a.arg not in MODULES:
            sys.exit(f"module required: {', '.join(ORDER)}")
        cfg["modules"][a.arg] = a.cmd == "enable"
        print(json.dumps(save(root, cfg)))
    elif a.cmd == "theme":
        if a.arg not in THEMES:
            sys.exit("theme must be light or dark")
        cfg["theme"] = a.arg
        print(json.dumps(save(root, cfg)))
    elif a.cmd == "show":
        print(json.dumps(cfg, indent=2))
    else:
        print(json.dumps(status(root), indent=2))


if __name__ == "__main__":
    main()
