"""The M3 hybrid hole (Toolroom interface profile 03_m3_hybrid_hole) as SolidCraft commands.

The contour and the entry relief are read from profiles/interfaces/m3-hybrid-hole.json, never retyped: twelve exact
arcs sketched on the entry face and cut to the profile depth, plus the 45 degree entry relief as a true cone.
`hybrid_hole` returns a list of {"command", "params"} steps to append to a command script. Origin, axis and the
default rib phase follow the build123d adapter skills/onshape-cad/scripts/m3_hybrid_hole.py, so both give the same
hole for the same arguments.

Usage in a generator:
    from m3_hybrid_hole import hybrid_hole
    commands += hybrid_hole("Screw 1", "Base", origin=[12, 8, 20], axis=[0, 0, -1])

Self-check (a block with one hole from the top, one from below and one from the side; prints the script):
    uv run --no-project python -I m3_hybrid_hole.py demo > m3-hybrid-hole-demo.json
    solidcraft-cli run m3-hybrid-hole-demo.json --results
examples/run-examples.sh runs it and compares the result with the build123d adapter's cutters.

Run on SolidCraft 0.46.2-nightly.20261122.155.1 (2026-11-22). Helpers written for 0.27 started the tool outside the
face, stepped the relief and drew it 0.01 wider than the profile; this one cuts the exact geometry, which built and
exported closed in the demo and in one real enclosure. That is no proof for every part: check each export for open
edges.
"""

import json
import sys
from pathlib import Path

PROFILE = json.loads((Path(__file__).resolve().parents[2] / "profiles/interfaces/m3-hybrid-hole.json").read_text())
ARCS = [[tuple(arc["points"][i]) for i in range(3)] for arc in PROFILE["contour"]["arcs"]]
DEPTH = PROFILE["interface"]["depth"]
RELIEF = PROFILE["interface"]["entry_relief"]


def _step(command, **params):
    return {"command": command, "params": params}


def _mm(value):
    return f"{round(value, 6)} mm"


def _basis(axis, x_dir):
    """Unit axis, and the sketch x and y axes: x as given or the adapter's default, y = axis x x."""
    norm = sum(c * c for c in axis) ** 0.5
    a = [c / norm for c in axis]
    if x_dir is None:
        reference = [1.0, 0.0, 0.0] if abs(a[0]) < 0.9 else [0.0, 1.0, 0.0]
        dot = sum(reference[i] * a[i] for i in range(3))
        x = [reference[i] - dot * a[i] for i in range(3)]
    else:
        x = [float(c) for c in x_dir]
        if abs(sum(x[i] * a[i] for i in range(3))) > 1e-9:
            raise ValueError("x_dir must be orthogonal to axis")
    norm = sum(c * c for c in x) ** 0.5
    x = [c / norm for c in x]
    y = [a[1] * x[2] - a[2] * x[1], a[2] * x[0] - a[0] * x[2], a[0] * x[1] - a[1] * x[0]]
    return a, x, y


def hybrid_hole(name, target, origin, axis, depth=DEPTH, x_dir=None, relief=True):
    """Cut the hole into the body `target`. origin: [x, y, z] on the entry face, in mm. axis: points into the
    material. x_dir (optional, orthogonal to axis) fixes the rotational phase of the three ribs."""
    a, x, y = _basis(axis, x_dir)
    plane = {"origin": [round(c, 6) for c in origin], "x_dir": [round(c, 9) for c in x], "y_dir": [round(c, 9) for c in y]}
    steps = [_step("sketch.create", plane=plane, name=f"{name} profile")]
    first = previous = [round(ARCS[0][0][0], 9), round(ARCS[0][0][1], 9)]
    for index, (_, through, end) in enumerate(ARCS):
        end = first if index == len(ARCS) - 1 else [round(end[0], 9), round(end[1], 9)]
        steps.append(_step("sketch.arc.three_point", start=previous, end=end,
                           through=[round(through[0], 9), round(through[1], 9)]))
        previous = end
    steps.append(_step("sketch.finish"))
    # the sketch normal is the axis, so "positive" runs into the material
    steps.append(_step("solid.extrude", distance=_mm(depth), direction="positive", operation="cut", targets=[target],
                       name=name))
    if relief:
        steps.append(_step("solid.cone", radius=_mm(RELIEF["entry_radius"]), height=_mm(RELIEF["apex_depth"]),
                           base=plane["origin"], axis=[round(c, 9) for c in a], operation="cut", targets=[target],
                           name=f"{name} relief"))
    return steps


DEMO_HOLES = [("Top hole", [10, 15, 24], [0, 0, -1]), ("Bottom hole", [30, 15, 0], [0, 0, 1]),
              ("Side hole", [20, 0, 12], [0, 1, 0])]


def demo():
    commands = [_step("solid.box", length="40 mm", width="30 mm", height="24 mm", corner=[0, 0, 0], name="Block",
                      body_name="Block"),
                _step("inspect.measure")]
    for name, origin, axis in DEMO_HOLES:
        commands += hybrid_hole(name, "Block", origin, axis) + [_step("inspect.measure")]
    commands.append(_step("file.export", path="m3-hybrid-hole-demo.stl", bodies=["Block"], quality="fine"))
    commands.append(_step("file.export", path="m3-hybrid-hole-demo.step", bodies=["Block"]))
    return {"commands": commands}


if __name__ == "__main__":
    if sys.argv[1:] != ["demo"]:
        sys.exit(__doc__)
    json.dump(demo(), sys.stdout, indent=1)
