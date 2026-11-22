"""Layers 1-3 of a three-colour plate in a bed window, one panel per layer, every filament's extrusion in its colour
(filament 1 white, 2 red, 3 dark brown), x flipped so the bed-side face reads as on the part. The filament is taken from
the AMS loads (M620 S<n>A): the first one prints as T1000.
usage: uv run --no-project --with pillow python -I tools/toolpath_layers.py <plate_1.gcode> <out.png> x0 x1 y0 y1
(plate_1.gcode: in the .gcode.3mf that slice-a1.sh writes with GCODE=1)"""
import math, re, sys
from PIL import Image, ImageDraw
gcode, out, X0, X1, Y0, Y1 = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7])
S, LAYERS = 40, (0.2, 0.4, 0.6)
COL = {0: (235, 235, 230), 1: (200, 20, 30), 2: (90, 55, 30)}
segs, tool, z, x, y = [], None, 0, 0, 0
for line in open(gcode):
    if line.startswith("; Z_HEIGHT:"): z = round(float(line.split(":")[1]), 2)
    m = re.match(r"^M620 S(\d+)A", line)
    if m: tool = int(m.group(1))
    if line[:3] in ("G1 ", "G2 ", "G3 "):
        d = dict((k, float(v)) for k, v in re.findall(r"([XYEIJ])(-?[\d.]+)", line))
        nx, ny = d.get("X", x), d.get("Y", y)
        pts = [(x, y), (nx, ny)]
        if line[1] in "23":
            cx, cy = x + d.get("I", 0), y + d.get("J", 0)
            a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
            if line[1] == "2" and a1 >= a0: a1 -= 2 * math.pi
            if line[1] == "3" and a1 <= a0: a1 += 2 * math.pi
            r = math.hypot(x - cx, y - cy); n = max(2, int(abs(a1 - a0) / 0.1))
            pts = [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
        if d.get("E", 0) > 0 and z in LAYERS and tool in COL:
            segs += [(z, tool, *pts[i], *pts[i + 1]) for i in range(len(pts) - 1)]
        x, y = nx, ny
W, H = int((X1 - X0) * S), int((Y1 - Y0) * S)
img = Image.new("RGB", (len(LAYERS) * (W + 10), H), "black")
for k, lz in enumerate(LAYERS):
    row = Image.new("RGB", (W, H), "black"); dr = ImageDraw.Draw(row)
    for zz, t, ax, ay, bx, by in segs:
        if zz == lz:
            p = lambda px, py: ((X1 - px) * S, (Y1 - py) * S)
            dr.line([p(ax, ay), p(bx, by)], fill=COL[t], width=int(0.42 * S))
    img.paste(row, (k * (W + 10), 0))
img.save(out)
print({lz: {t: sum(1 for s in segs if s[0] == lz and s[1] == t) for t in COL} for lz in LAYERS})
