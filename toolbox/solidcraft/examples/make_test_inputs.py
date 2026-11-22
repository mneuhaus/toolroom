"""Writes the inputs of the scan examples into the current folder: scan.png, outline.dxf and cloud.xyz.

scan.png is a synthetic flatbed scan at 20 px/mm: a dark L profile, 40 x 30 mm with 8 mm legs and one 6 mm hole, on a
light background, with a 50 mm reference bar under it. outline.dxf is the same outline in mm as closed polylines, the
form scan/scan_kontur.py writes. cloud.xyz is a grid of points 0.05 mm outside every face of a 40 x 20 x 10 mm box.
Known values: section area 467.73 mm2 (467.75 with the hole as the DXF's 96-gon), deviation +0.05 mm.

Usage: uv run --no-project --with pillow --with ezdxf python -I make_test_inputs.py
"""
import math

import ezdxf
from PIL import Image, ImageDraw

SCALE = 20                                   # px per mm
image = Image.new("L", (70 * SCALE, 60 * SCALE), 245)
draw = ImageDraw.Draw(image)


def px(x, y):
    return (10 * SCALE + x * SCALE, 50 * SCALE - y * SCALE)


draw.polygon([px(0, 0), px(40, 0), px(40, 8), px(8, 8), px(8, 30), px(0, 30)], fill=20)
cx, cy = px(30, 4)
draw.ellipse([cx - 3 * SCALE, cy - 3 * SCALE, cx + 3 * SCALE, cy + 3 * SCALE], fill=245)
draw.rectangle([*px(0, -5), *px(50, -6)], fill=20)
image.save("scan.png")

doc = ezdxf.new("R2010", setup=False)
doc.units = ezdxf.units.MM
msp = doc.modelspace()
msp.add_lwpolyline([(0, 0), (40, 0), (40, 8), (8, 8), (8, 30), (0, 30)], close=True)
msp.add_lwpolyline([(30 + 3 * math.cos(2 * math.pi * i / 96), 4 + 3 * math.sin(2 * math.pi * i / 96))
                    for i in range(96)], close=True)
doc.saveas("outline.dxf")

SIZE, OFFSET, points = (40.0, 20.0, 10.0), 0.05, []
for axis in range(3):
    u, v = [a for a in range(3) if a != axis]
    for side in (0, 1):
        for i in range(1, 20):
            for j in range(1, 20):
                p = [0.0, 0.0, 0.0]
                p[axis] = SIZE[axis] + OFFSET if side else -OFFSET
                p[u], p[v] = SIZE[u] * i / 20, SIZE[v] * j / 20
                points.append(p)
with open("cloud.xyz", "w") as out:
    out.writelines(f"{p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n" for p in points)
