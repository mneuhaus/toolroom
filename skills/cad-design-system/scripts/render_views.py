#!/usr/bin/env python3
"""render_views.py — front / top / side / isometric views of one or more meshes as a PNG,
so the model (and the human) can look at the geometry after every export.

Orthographic, flat-shaded, no OpenGL needed (matplotlib, headless). Several bodies are
drawn in one scene with different greys so multi-part exports (body + label + cap) can be
judged together.

Usage:
  render_views.py part.stl --out part_views.png
  render_views.py tile_body_base.stl tile_label_accent.stl --out tile.png --up +Z --size 1600

Dependencies: trimesh, numpy, matplotlib, scipy, pyyaml (shared orientation helper).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
except ImportError as e:  # pragma: no cover
    print(f"missing dependency: {e}. pip install trimesh numpy matplotlib", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_mesh import UP, rotate_to_z_up  # noqa: E402

VIEWS = [  # name, elevation, azimuth (matplotlib convention)
    ("front (−Y)", 0, -90),
    ("top (+Z)", 90, -90),
    ("side (+X)", 0, 0),
    ("iso", 30, -50),
]
SHADES = [0.78, 0.35, 0.60, 0.20, 0.90]      # per-body base grey


def load_meshes(paths, up):
    meshes = []
    for p in paths:
        m = trimesh.load(p, force="mesh")
        if isinstance(m, trimesh.Scene):  # pragma: no cover
            m = trimesh.util.concatenate(list(m.geometry.values()))
        m = rotate_to_z_up(m, up)
        # painter's-algorithm sorting in matplotlib fails on long thin triangles (fans on big
        # flat faces); subdividing them to a modest edge length fixes most of the artefacts
        try:
            max_edge = float(max(m.extents)) / 12.0
            if len(m.faces) < 150_000:
                m = m.subdivide_to_size(max_edge=max_edge, max_iter=6)
        except Exception:
            pass
        if len(m.faces) > 200_000:
            print(f"note: {p} has {len(m.faces)} faces; rendering may be slow", file=sys.stderr)
        meshes.append((Path(p).stem, m))
    return meshes


def draw(ax, meshes, elev, azim, light=np.array([0.3, -0.6, 0.75])):
    light = light / np.linalg.norm(light)
    allv = np.vstack([m.vertices for _, m in meshes])
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    # camera direction for back-face culling: closed meshes then need far less depth sorting
    e, a = np.radians(elev), np.radians(azim)
    cam = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    for i, (_, m) in enumerate(meshes):
        base = SHADES[i % len(SHADES)]
        front = (m.face_normals @ cam) > 1e-6
        if not front.any():
            continue
        lam = np.clip(m.face_normals[front] @ light, 0, 1)
        col = base * (0.45 + 0.55 * lam)
        tris = m.vertices[m.faces[front]]
        pc = Poly3DCollection(tris, linewidths=0.15, zsort="average")
        rgba = [(c, c, c, 1.0) for c in col]
        pc.set_facecolor(rgba)
        pc.set_edgecolor(rgba)          # hides anti-aliasing seams between triangles
        ax.add_collection3d(pc)
    c = (lo + hi) / 2
    r = float(max(hi - lo)) / 2 * 1.05
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    try:
        ax.set_box_aspect((1, 1, 1), zoom=1.6)
    except TypeError:  # older matplotlib
        ax.set_box_aspect((1, 1, 1))
    ax.set_proj_type("ortho")
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh", nargs="+")
    ap.add_argument("--out", default="views.png")
    ap.add_argument("--up", default="+Z", choices=list(UP))
    ap.add_argument("--size", type=int, default=1400, help="image width in px")
    args = ap.parse_args(argv)
    meshes = load_meshes(args.mesh, args.up)
    if not meshes:
        return 2
    ext = np.vstack([m.vertices for _, m in meshes])
    dims = ext.max(axis=0) - ext.min(axis=0)
    fig = plt.figure(figsize=(args.size / 100, args.size / 100 * 0.62), dpi=100)
    for k, (name, elev, azim) in enumerate(VIEWS):
        ax = fig.add_subplot(2, 2, k + 1, projection="3d")
        draw(ax, meshes, elev, azim)
        ax.set_title(name, fontsize=11, pad=2)
    fig.suptitle(", ".join(n for n, _ in meshes) + f"   ·   {dims[0]:.1f} × {dims[1]:.1f} × {dims[2]:.1f} mm (up {args.up})", fontsize=11)
    fig.tight_layout()
    fig.savefig(args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
