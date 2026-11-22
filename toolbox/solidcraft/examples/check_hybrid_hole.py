"""Compares the SolidCraft demo block of m3_hybrid_hole.py with the same block cut by the build123d adapter
(skills/onshape-cad/scripts/m3_hybrid_hole.py): the material only one of them has must be next to nothing.

Usage: uv run --no-project --with build123d python -I check_hybrid_hole.py <work-dir>
"""
import importlib.util
import sys
from pathlib import Path

from build123d import Box, Pos, import_step

BOX = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load("adapter", BOX.parent / "skills/onshape-cad/scripts/m3_hybrid_hole.py")
helper = load("helper", BOX / "solidcraft/m3_hybrid_hole.py")

reference = Pos(20, 15, 12) * Box(40, 30, 24)
for _, origin, axis in helper.DEMO_HOLES:
    reference = reference - adapter.hybrid_tool(origin, axis, helper.DEPTH)
built = import_step(Path(sys.argv[1]) / "m3-hybrid-hole-demo.step")


def volume(shape):
    """A cut that leaves nothing, or several pieces, comes back as a list."""
    return sum(piece.volume for piece in shape) if isinstance(shape, list) else shape.volume


only_reference, only_built = volume(reference - built), volume(built - reference)
ok = only_reference < 0.01 and only_built < 0.01
print(("ok    " if ok else "FAIL  ") + f"M3 hybrid hole equals the build123d adapter: volumes {volume(built):.3f} and "
      f"{volume(reference):.3f} mm3, only in one of them {only_built:.4f} and {only_reference:.4f} mm3")
sys.exit(0 if ok else 1)
