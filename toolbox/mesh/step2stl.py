"""Mesh a STEP file with OpenCascade, as a fallback when a CAD backend's own mesh export has open edges.

Usage: uv run --no-project --with build123d python -I step2stl.py in.step out.stl [chord tolerance in mm, default 0.01]
"""
import sys

from build123d import export_stl, import_step

shape = import_step(sys.argv[1])
tolerance = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
export_stl(shape, sys.argv[2], tolerance=tolerance, angular_tolerance=0.1)
