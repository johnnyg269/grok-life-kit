"""Self-test for compare_photos.py using generated images: python test_compare_photos.py [TMPDIR]"""
import csv, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw
here = Path(__file__).parent
tmp = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
data, src = tmp / "data", tmp / "src"
data.mkdir(parents=True, exist_ok=True); src.mkdir(exist_ok=True)

def fake(path, size, shade, body_w):
    im = Image.new("RGB", size, (shade, shade + 20, 235 - shade // 2)); d = ImageDraw.Draw(im)
    w, h = size; cx = w // 2
    d.ellipse((cx - 60, h * .08, cx + 60, h * .08 + 120), fill=(40, 40, 40))
    d.rounded_rectangle((cx - body_w, h * .08 + 130, cx + body_w, h * .62), 40, fill=(40, 40, 40))
    d.rectangle((cx - body_w // 2, h * .62, cx + body_w // 2, h * .95), fill=(40, 40, 40))
    im.save(path, "JPEG")

def run(*args, expect=0):
    r = subprocess.run([sys.executable, str(here / "compare_photos.py"), "--data", str(data), "--units", "imperial", *args],
                       capture_output=True, text=True)
    assert r.returncode == expect, (args, r.returncode, r.stdout, r.stderr)
    return r.stdout.split(), r.stderr

with open(data / "weight.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "weight_kg"])
    w.writerows([["2026-10-18", 86.0], ["2026-11-01", 84.9], ["2026-11-18", 83.5]])
fake(src / "a.jpg", (1500, 2000), 120, 150)   # 3:4
fake(src / "b.jpg", (3000, 3000), 140, 140)   # square, different size
fake(src / "c.jpg", (900, 1600), 160, 130)    # tall 9:16

# pose missing / bad -> exit 2
_, err = run("add", "--src", str(src / "a.jpg"), "--date", "2026-10-18", expect=2); assert "POSE_NEEDED" in err
_, err = run("add", "--src", str(src / "a.jpg"), "--pose", "profile", "--date", "2026-10-18", expect=2)
# first photo: no comparison
o, _ = run("add", "--src", str(src / "a.jpg"), "--pose", "front", "--date", "2026-10-18"); assert len(o) == 1
o, _ = run("add", "--src", str(src / "b.jpg"), "--pose", "front", "--date", "2026-11-01"); assert len(o) == 2
assert "prev_2026-10-18_to_2026-11-01" in o[1]
o, _ = run("add", "--src", str(src / "c.jpg"), "--pose", "front", "--date", "2026-11-18"); prev = o[1]
assert "prev_2026-11-01_to_2026-11-18" in prev
run("add", "--src", str(src / "a.jpg"), "--pose", "side", "--date", "2026-10-18")
run("add", "--src", str(src / "c.jpg"), "--pose", "side", "--date", "2026-11-18")
# re-adding same day replaces the row
run("add", "--src", str(src / "b.jpg"), "--pose", "front", "--date", "2026-11-18")
rows = list(csv.DictReader(open(data / "photos.csv")))
assert len([r for r in rows if r["pose"] == "front"]) == 3, rows
assert rows[0].keys() >= {"date", "pose", "path", "weight_kg"}
assert [r["weight_kg"] for r in rows if r["pose"] == "front"] == ["86.0", "84.9", "83.5"]
o, _ = run("alltime"); assert len(o) == 2, o       # front + side, no back
assert any("first_2026-10-18_to_2026-11-18" in p for p in o)
import os
for p in o + [prev]:
    im = Image.open(p)
    if os.environ.get("GROKLIFE_NO_CHROMIUM") or os.environ.get("SWOLE_NO_CHROMIUM"):
        assert im.width <= 1600 and im.height > 1000, (p, im.size)   # Pillow fallback layout
    else:
        assert im.size == (1080, 1080), (p, im.size)                 # Chromium layout
assert (data / "photos/front/2026-11-18.jpg").exists()
o, _ = run("compare", "--pose", "back"); assert o == []
print("OK")
for p in sorted((data / "photos" / "comparisons").rglob("*.jpg")): print(p)
