"""Quick matplotlib-based preview renders (no pyrender/pyglet available in the toolroom
env): one iso view of the whole plate, plus one iso view per posed stab."""
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

P = Path(__file__).resolve().parent.parent
POSED = P / "var" / "print" / "parts_posed"
OUT = P / "var" / "print"


def render(meshes_colors, dest, title):
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection="3d")
    all_pts = []
    for mesh, color in meshes_colors:
        tris = mesh.vertices[mesh.faces]
        coll = Poly3DCollection(tris, facecolor=color, edgecolor="k", linewidths=0.1, alpha=1.0)
        ax.add_collection3d(coll)
        all_pts.append(mesh.vertices)
    pts = np.vstack(all_pts)
    mins, maxs = pts.min(axis=0), pts.max(axis=0)
    center = (mins + maxs) / 2
    span = (maxs - mins).max() / 2 * 1.1
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(max(0, center[2] - span), center[2] + span)
    ax.set_box_aspect([1, 1, 1])
    ax.view_init(elev=25, azim=-60)
    ax.set_title(title)
    ax.set_xlabel("X mm"); ax.set_ylabel("Y mm"); ax.set_zlabel("Z mm")
    fig.tight_layout()
    fig.savefig(dest, dpi=150)
    plt.close(fig)
    print("wrote", dest)


def main():
    colors = ["#7fb3ff", "#ffb37f", "#9fdf9f", "#df9fdf"]
    parts = sorted(POSED.glob("*-posed.stl"))
    all_mc = []
    for i, stl in enumerate(parts):
        m = trimesh.load_mesh(stl, process=True)
        color = colors[i % len(colors)]
        all_mc.append((m, color))
        render([(m, color)], OUT / f"{stl.stem.replace('-posed','')}-iso.png", stl.stem)
    render(all_mc, OUT / "plate-iso.png", "Probestaebe A1-01 Plate")


if __name__ == "__main__":
    main()
