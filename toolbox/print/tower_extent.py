"""Footprint of a sliced plate's prime tower (incl. its brim) and the nearest part outline, from the G-code: extruding
moves (Bambu: relative E) inside "; FEATURE: Prime tower" / "Brim" blocks at the tower, against every other extruding
move of layer 1. Used to place the tower next to the cap plates (tools/plate_kappen.py, 2026-10-14).
Usage: uv run --no-project python -I tools/tower_extent.py <plate_1.gcode>
"""
import re
import sys

feature, x, y, layer = None, 0.0, 0.0, 0
tower, brim, parts = [], [], []
for line in open(sys.argv[1]):
    if line.startswith("; FEATURE:"):
        feature = line.split(":", 1)[1].strip()
    elif line.startswith("; CHANGE_LAYER"):
        layer += 1
    elif line.startswith(("G1 ", "G2 ", "G3 ")):
        d = dict((k, float(v)) for k, v in re.findall(r"([XYE])(-?[\d.]+)", line))
        nx, ny = d.get("X", x), d.get("Y", y)
        if d.get("E", 0) > 0 and ("X" in d or "Y" in d) and 0 <= nx <= 256 and 0 <= ny <= 256:   # no unretracts
            (tower if feature == "Prime tower" else brim if feature == "Brim" and layer <= 1
             else parts if layer <= 1 else []).append((nx, ny))
        x, y = nx, ny


def box(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


tx0, tx1, ty0, ty1 = box(tower)
# brim within 6 mm of the tower body is the tower's (its brim is 3.2 wide, parts stand 5 mm off that); the rest is parts'
near_tower = [(px, py) for px, py in brim if tx0 - 6 <= px <= tx1 + 6 and ty0 - 6 <= py <= ty1 + 6]
parts += [p for p in brim if p not in near_tower]
tx0, tx1, ty0, ty1 = box(tower + near_tower)
print(f"tower x {tx0:.2f} .. {tx1:.2f}, y {ty0:.2f} .. {ty1:.2f} ({tx1 - tx0:.1f} x {ty1 - ty0:.1f})")
near = min(max(tx0 - px, px - tx1, ty0 - py, py - ty1) for px, py in parts)
print(f"nearest layer-1 part extrusion to the tower box: {near:.2f} mm")
