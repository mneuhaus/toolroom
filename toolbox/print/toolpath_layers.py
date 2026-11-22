"""Draws layers 1 and 2 of a sliced plate in a bed window, one row per (layer, filament): filament 2 (and Bambu's first
load T1000) red, filament 1 grey; each row is clipped to the window. Handles G1, arcs (G2/G3) and G90/G91.
Used to check that the bed-side logo (the visible face) prints in layer 1: with the classic wall generator the 0.4 mm
registered-sign ring vanished there; Arachne keeps it.
Usage: uv run --no-project --with pillow python -I tools/toolpath_layers.py <plate_1.gcode> <out.png> x0 x1 y0 y1
"""
import math, sys, re
from PIL import Image, ImageDraw
gcode, out, X0, X1, Y0, Y1 = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7])
S = 30
segs = []
tool = None; z = 0; x = y = 0; absolute = True
for line in open(gcode):
    if line.startswith("; Z_HEIGHT:"): z = float(line.split(":")[1])
    if line.startswith("G90"): absolute = True
    if line.startswith("G91"): absolute = False
    m = re.match(r"^T(\d+)\s*$", line)
    if m: tool = int(m.group(1))
    if line[:3] in ("G1 ", "G2 ", "G3 "):
        d = dict((k, float(v)) for k, v in re.findall(r"([XYEIJ])(-?[\d.]+)", line))
        nx = d.get("X", x if absolute else 0) + (0 if absolute else x)
        ny = d.get("Y", y if absolute else 0) + (0 if absolute else y)
        pts = [(x, y), (nx, ny)]
        if line[1] in "23":                      # arc: centre relative to the start, G2 clockwise
            cx, cy = x + d.get("I", 0), y + d.get("J", 0)
            a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
            if line[1] == "2" and a1 >= a0: a1 -= 2 * math.pi
            if line[1] == "3" and a1 <= a0: a1 += 2 * math.pi
            r = math.hypot(x - cx, y - cy); n = max(2, int(abs(a1 - a0) / 0.1))
            pts = [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
        if d.get("E", 0) > 0 and z in (0.2, 0.4):
            segs += [(z, 1 if tool in (1, 1000) else 0, *pts[i], *pts[i + 1]) for i in range(len(pts) - 1)]
        x, y = nx, ny
W, H = int((X1 - X0) * S), int((Y1 - Y0) * S)
rows = [(0.2, 1), (0.2, 0), (0.4, 1), (0.4, 0)]
img = Image.new("RGB", (W, len(rows) * (H + 10)), "black")
for r, (lz, lt) in enumerate(rows):     # each row on its own canvas, so paths outside the window are clipped
    row = Image.new("RGB", (W, H), "black")
    dr = ImageDraw.Draw(row)
    col = (200, 40, 50) if lt else (225, 225, 225)
    for z, t, ax, ay, bx, by in segs:
        if (z, t) == (lz, lt):
            p = lambda px, py: ((px - X0) * S, (Y1 - py) * S)
            dr.line([p(ax, ay), p(bx, by)], fill=col, width=int(0.42 * S))
    img.paste(row, (0, r * (H + 10)))
img.save(out)
