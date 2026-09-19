"""Helfer: Schnittlinien echter Koerper im lokalen Maschinensystem von R6d.

Ein Schnitt durch eine Ebene senkrecht zur lokalen X-Achse liefert geschlossene
Polygonzuege in (Y, Z). Das liest sich deutlich klarer als eine 3D-Projektion und
ist massstabstreu -- genau das, was die Doku braucht.
"""
from pathlib import Path

import numpy as np
import trimesh

MACHINE = Path('/Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d/machine/machine.json')
BELT_CLAMP = Path('/Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d-belt-clamp-r1')
HOPPER = Path('/Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d-hopper-floor-r1')
BILDER = Path(__file__).resolve().parent.parent


def local_mesh(body, frame):
    """Kopie des Meshes in lokalen Koordinaten."""
    m = body.mesh
    return trimesh.Trimesh(vertices=frame.to_local(np.asarray(m.vertices, dtype=float)),
                           faces=np.asarray(m.faces), process=False)


def section(mesh_local, axis=0, value=0.0):
    """Liste von (N,2)-Polygonzuegen in den beiden uebrigen Achsen."""
    normal = np.zeros(3)
    normal[axis] = 1.0
    origin = np.zeros(3)
    origin[axis] = value
    try:
        path = mesh_local.section(plane_origin=origin, plane_normal=normal)
    except Exception:
        return []
    if path is None:
        return []
    keep = [i for i in range(3) if i != axis]
    out = []
    for ent in path.entities:
        pts = path.vertices[ent.points]
        out.append(np.asarray(pts, dtype=float)[:, keep])
    return out


def draw(ax, polys, facecolor, edgecolor='#222222', lw=0.9, alpha=1.0, label=None, zorder=2, hatch=None):
    from matplotlib.patches import Polygon
    first = True
    for p in polys:
        if len(p) < 3:
            continue
        ax.add_patch(Polygon(p, closed=True, facecolor=facecolor, edgecolor=edgecolor,
                             linewidth=lw, alpha=alpha, zorder=zorder, hatch=hatch,
                             label=label if first else None))
        first = False


def limits(ax, polys, pad=4.0):
    pts = np.vstack([p for p in polys if len(p)])
    lo, hi = pts.min(axis=0) - pad, pts.max(axis=0) + pad
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_aspect('equal')


def masspfeil(ax, p0, p1, text, color='#b02020', offset=(0, 0), fontsize=9):
    """Bemassung zwischen zwei Punkten, Text daneben."""
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    ax.annotate('', xy=tuple(p1), xytext=tuple(p0),
                arrowprops=dict(arrowstyle='<->', color=color, lw=1.4, shrinkA=0, shrinkB=0),
                zorder=10)
    mid = (p0 + p1) / 2 + np.asarray(offset, dtype=float)
    ax.text(mid[0], mid[1], text, color=color, fontsize=fontsize, fontweight='bold',
            ha='center', va='center', zorder=11,
            bbox=dict(boxstyle='round,pad=0.25', fc='white', ec=color, lw=0.8))


def sauber(ax, titel, xlabel='lokal Y  [mm]', ylabel='lokal Z  [mm]'):
    ax.set_title(titel, fontsize=11)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(True, color='#dddddd', lw=0.5, zorder=0)
    ax.set_axisbelow(True)
