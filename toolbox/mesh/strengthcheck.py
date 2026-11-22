# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "trimesh", "shapely", "matplotlib", "scipy", "networkx", "rtree"]
# ///
"""strengthcheck — Layer-Anisotropie-Bewertung fuer FDM-Teile.

FDM-Teile brechen bevorzugt AN einer Schichtebene (Layer-Haftung nur
~40-60 % der XY-Festigkeit). Das Tool schneidet das Teil in DRUCKLAGE in
Z-Ebenen und bewertet je Ebene den tragenden Querschnitt:

- A(z): Querschnittsflaeche — Minima = Sollbruchstellen/Einschnuerungen
- W_x/W_y(z): Biege-Widerstandsmomente um die Bett-Achsen — wo bricht es
  bei Seitenlast zuerst
- Inseln je Ebene: zerfaellt der Querschnitt, traegt nur die kleinste
  Verbindung
- Schlankheit: Hoehe vs. typische Querschnittsgroesse (der "stehende Stab")

  uv run tools/strengthcheck.py teil.stl            # Report
  uv run tools/strengthcheck.py --compare teil.stl  # as-is vs flip-x180
  uv run tools/strengthcheck.py --plot out/maps *.stl   # A(z)/W(z)-Kurven

Kein FEM — eine ehrliche Geometrie-Heuristik fuer die Frage "wo und wie
leicht bricht das entlang der Druckschichten".
"""
import argparse
import math
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon


def ring_moments(coords):
    """Flaeche, statische + quadratische Momente eines Rings (Shoelace/Green).
    Liefert (A, Sx, Sy, Ixx, Iyy) bzgl. Ursprung; Vorzeichen = Umlaufsinn."""
    x = np.asarray([c[0] for c in coords])
    y = np.asarray([c[1] for c in coords])
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cross = x * y1 - x1 * y
    a = cross.sum() / 2.0
    sx = ((y + y1) * cross).sum() / 6.0          # int y dA
    sy = ((x + x1) * cross).sum() / 6.0          # int x dA
    ixx = ((y * y + y * y1 + y1 * y1) * cross).sum() / 12.0   # int y^2 dA
    iyy = ((x * x + x * x1 + x1 * x1) * cross).sum() / 12.0   # int x^2 dA
    return a, sx, sy, ixx, iyy


def _oriented(coords):
    """Ring-Momente unabhaengig vom Umlaufsinn: alle Integrale wechseln
    mit dem Umlaufsinn das Vorzeichen -> mit sign(A) normalisieren."""
    a, sx, sy, ixx, iyy = ring_moments(coords)
    s = 1.0 if a >= 0 else -1.0
    return np.array([a * s, sx * s, sy * s, ixx * s, iyy * s])


def section_props(polys):
    """Gesamt-Querschnitt (mehrere shapely-Polygone mit Loechern):
    A, W_x, W_y (Widerstandsmomente um den Gesamt-Schwerpunkt)."""
    tot = np.zeros(5)
    pts = []
    for p in polys:
        tot += _oriented(p.exterior.coords)
        for hole in p.interiors:
            tot -= _oriented(hole.coords)
        pts.extend(p.exterior.coords)
    A, Sx, Sy, Ixx, Iyy = tot
    if A <= 1e-9:
        return 0.0, 0.0, 0.0
    cy, cx = Sx / A, Sy / A
    ixx_c = Ixx - A * cy * cy
    iyy_c = Iyy - A * cx * cx
    arr = np.asarray(pts)
    ymax = max(abs(arr[:, 1].max() - cy), abs(arr[:, 1].min() - cy), 1e-9)
    xmax = max(abs(arr[:, 0].max() - cx), abs(arr[:, 0].min() - cx), 1e-9)
    return A, ixx_c / ymax, iyy_c / xmax


def sweep(stl, flip=False, step=1.0):
    m = trimesh.load(stl, force="mesh")
    if m.bounds[1].max() < 1.0:
        m.apply_scale(1000.0)
    if flip:
        m.apply_transform(trimesh.transformations.rotation_matrix(
            math.pi, [1, 0, 0]))
    m.apply_translation([0, 0, -m.bounds[0][2]])
    zmax = m.bounds[1][2]
    rows = []
    z = step / 2.0
    while z < zmax:
        sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            rows.append((z, 0.0, 0.0, 0.0, 0, 0.0))
        else:
            planar, _ = sec.to_2D()
            polys = list(planar.polygons_full)
            A, wx, wy = section_props(polys)
            islands = len(polys)
            a_min_island = min((p.area for p in polys), default=0.0)
            rows.append((z, A, wx, wy, islands, a_min_island))
        z += step
    return m, np.array(rows, dtype=float)


def analyze(stl, flip=False, step=1.0, layer_factor=0.5):
    m, rows = sweep(stl, flip, step)
    solid = rows[rows[:, 1] > 1e-6]
    if not len(solid):
        raise SystemExit(f"{stl}: keine Querschnitte gefunden")
    z, A, wx, wy = solid[:, 0], solid[:, 1], solid[:, 2], solid[:, 3]
    med = float(np.median(A))
    i_min = int(np.argmin(A))
    # Taille oder endender Aufsatz? Eine echte Einschnuerung hat OBERHALB
    # wieder substanziell Material (Pads/Noppen am Deckel dagegen nicht).
    a_above = float(A[i_min:].max()) if i_min < len(A) else 0.0
    is_neck = a_above > max(2.0 * A[i_min], 0.2 * med)
    i_wx = int(np.argmin(wx))
    i_wy = int(np.argmin(wy))
    h = float(m.bounds[1][2])
    slender = h / math.sqrt(med) if med > 0 else 0.0
    return {
        "stl": Path(stl).name, "flip": flip, "hoehe": h, "step": step,
        "A_med": med,
        "A_min": float(A[i_min]), "A_min_z": float(z[i_min]),
        "neck": float(A[i_min] / med) if med else 0.0,
        "is_neck": bool(is_neck),
        "Wx_min": float(wx[i_wx]), "Wx_min_z": float(z[i_wx]),
        "Wy_min": float(wy[i_wy]), "Wy_min_z": float(z[i_wy]),
        "islands_max": int(solid[:, 4].max()),
        "min_island": float(solid[:, 5].min()),
        "min_island_z": float(solid[np.argmin(solid[:, 5]), 0]),
        "slender": slender, "layer_factor": layer_factor,
        "rows": solid,
    }


def verdict(r):
    v = []
    if r["neck"] < 0.3 and r["is_neck"]:
        v.append(f"EINSCHNUERUNG bei z={r['A_min_z']:.1f} "
                 f"({r['A_min']:.0f} mm2 = {100 * r['neck']:.0f}% vom Median)"
                 " — Sollbruchstelle an der Schichtnaht!")
    elif r["neck"] < 0.3:
        v.append(f"Aufsatz ab z={r['A_min_z']:.1f}: nur {r['A_min']:.0f} mm2 "
                 "Layer-Anbindung — z-Zug daran (z.B. Schraube) ist reiner "
                 "Schichtnaht-Zug (~50%)")
    elif r["neck"] < 0.6:
        v.append(f"verjuengt bei z={r['A_min_z']:.1f} "
                 f"({100 * r['neck']:.0f}% vom Median)")
    if r["islands_max"] > 1 and r["min_island"] < 0.25 * r["A_med"]:
        v.append(f"Querschnitt zerfaellt (bis {r['islands_max']} Inseln, "
                 f"kleinste {r['min_island']:.0f} mm2 bei "
                 f"z={r['min_island_z']:.1f}) — duenne Einzelverbindung")
    if r["slender"] > 4:
        v.append(f"SCHLANK-HOCH (Hoehe {r['hoehe']:.0f} = "
                 f"{r['slender']:.1f}x Querschnittsmass) — stehender-Stab-"
                 f"Risiko: Seitenlast bricht die Schichtnaht "
                 f"(~{100 * r['layer_factor']:.0f}% Festigkeit)")
    if not v:
        v.append("keine Layer-Schwachstelle erkennbar (satter, "
                 "gleichmaessiger Querschnitt)")
    return "; ".join(v)


def line(r):
    return (f"h={r['hoehe']:.1f}  A med {r['A_med']:.0f} / min "
            f"{r['A_min']:.0f} mm2 @z{r['A_min_z']:.1f}  "
            f"Wx min {r['Wx_min']:.0f} @z{r['Wx_min_z']:.1f}  "
            f"Wy min {r['Wy_min']:.0f} @z{r['Wy_min_z']:.1f}\n"
            f"    -> {verdict(r)}")


def plot(r, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = r["rows"]
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(rows[:, 0], rows[:, 1], label="A(z) mm2", color="#2a6fbb")
    ax1.axhline(r["A_med"], ls=":", color="#2a6fbb", alpha=0.5)
    ax1.scatter([r["A_min_z"]], [r["A_min"]], color="red", zorder=5,
                label=f"min A @z{r['A_min_z']:.1f}")
    ax1.set_xlabel("z (Drucklage) mm")
    ax1.set_ylabel("Querschnitt mm2")
    ax2 = ax1.twinx()
    ax2.plot(rows[:, 0], rows[:, 2], label="Wx(z)", color="#4a9a4a", alpha=0.7)
    ax2.plot(rows[:, 0], rows[:, 3], label="Wy(z)", color="#b8862a", alpha=0.7)
    ax2.set_ylabel("Widerstandsmoment mm3")
    fig.legend(loc="upper right")
    ax1.set_title(f"{r['stl']}{' (geflippt)' if r['flip'] else ''} — "
                  "Layer-Querschnitts-Sweep")
    fig.savefig(out_png, dpi=110, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stls", nargs="+")
    ap.add_argument("--step", type=float, default=1.0)
    ap.add_argument("--layer-factor", type=float, default=0.5,
                    help="Layer-Haftung relativ zur XY-Festigkeit (ASA ~0.5)")
    ap.add_argument("--compare", action="store_true",
                    help="as-is vs flip-x180 vergleichen")
    ap.add_argument("--plot", metavar="DIR", help="A/W(z)-Kurve als PNG")
    args = ap.parse_args()
    for stl in args.stls:
        variants = [False, True] if args.compare else [False]
        print(f"{Path(stl).name}:")
        for flip in variants:
            r = analyze(stl, flip, args.step, args.layer_factor)
            tag = "flip-x180" if flip else "as-is    "
            print(f"  {tag}  {line(r)}")
            if args.plot:
                Path(args.plot).mkdir(parents=True, exist_ok=True)
                suffix = "-flip" if flip else ""
                plot(r, f"{args.plot}/{Path(stl).stem}-strength{suffix}.png")


if __name__ == "__main__":
    main()
