"""Voxelgitter, Füllung und Ankerfindung für `relevance()`.

Die Füllung geht **nicht** über `trimesh.voxelized().fill()` (gemessen 7,7 s bei 1 mm
auf dem Hopperboden, und die Oberflächenvoxel blähen das Volumen um ein Drittel auf),
sondern über Strahlenspalten: je Gitterspalte ein Strahl durch das Mesh, danach
Paritätsfüllung über die sortierten Durchstoßpunkte. Das ist bei 1 mm 0,27 s je Achse
und trifft das Volumen auf 0,3 % genau. Gefüllt wird über alle drei Achsen und per
Mehrheit entschieden, damit ein Strahl, der eine koplanare Fläche streift, nicht
stillschweigend eine ganze Spalte umklappt.
"""
from __future__ import annotations

from itertools import product

import numpy as np

from ..machine import Machine, Scene, State
from . import _nearest

#: Bohrungen größer als das sind Durchbrüche/Taschen, keine Verschraubung.
MAX_BOHRUNG_MM = 12.0
#: Ein Zylinder gilt erst ab dieser Umfassung als Bohrung (Verrundungen umfassen weniger).
MIN_BOHRUNG_GRAD = 170.0
#: Mehr Posen als das werden auf Endlagen + Standardwert eingedampft.
MAX_POSEN = 12


class Grid:
    """Achsparalleles Voxelgitter in Weltkoordinaten."""

    __slots__ = ('lo', 'pitch', 'occ')

    def __init__(self, lo, pitch, occ):
        self.lo = np.asarray(lo, dtype=float).reshape(3)
        self.pitch = float(pitch)
        self.occ = occ

    @property
    def shape(self):
        return self.occ.shape

    @property
    def voxel_mm3(self) -> float:
        return self.pitch ** 3

    def centers(self, idx) -> np.ndarray:
        """Weltkoordinaten der Zellmittelpunkte zu (N,3)-Indizes."""
        idx = np.atleast_2d(np.asarray(idx))
        return self.lo + (idx + 0.5) * self.pitch

    def all_centers(self) -> np.ndarray:
        ax = [self.lo[i] + (np.arange(self.shape[i]) + 0.5) * self.pitch for i in range(3)]
        return np.stack(np.meshgrid(*ax, indexing='ij'), axis=-1)

    def contains_mask(self, region) -> np.ndarray:
        """Bool-Array: welche Zellmittelpunkte liegen in der Region?"""
        pts = self.all_centers().reshape(-1, 3)
        return np.asarray(region.contains(pts)).reshape(self.shape)


def _fill_axis(mesh, lo, n, pitch, axis) -> np.ndarray:
    """Paritätsfüllung entlang einer Achse."""
    ax = [lo[i] + (np.arange(n[i]) + 0.5) * pitch for i in range(3)]
    others = [i for i in range(3) if i != axis]
    A, B = np.meshgrid(ax[others[0]], ax[others[1]], indexing='ij')
    org = np.zeros((A.size, 3))
    org[:, others[0]] = A.ravel()
    org[:, others[1]] = B.ravel()
    start = lo[axis] - pitch
    org[:, axis] = start
    d = np.zeros(3)
    d[axis] = 1.0
    loc, ray_idx, _ = mesh.ray.intersects_location(org, np.tile(d, (len(org), 1)), multiple_hits=True)
    occ = np.zeros((len(org), n[axis]), dtype=bool)
    if len(ray_idx):
        t = loc[:, axis] - start
        order = np.lexsort((t, ray_idx))
        ray_idx = ray_idx[order]
        t = t[order]
        coord = ax[axis] - start
        starts = np.searchsorted(ray_idx, np.arange(len(org)), 'left')
        ends = np.searchsorted(ray_idx, np.arange(len(org)), 'right')
        for r in np.nonzero(ends - starts >= 2)[0]:
            occ[r] = (np.searchsorted(t[starts[r]:ends[r]], coord, 'right') % 2) == 1
    occ = occ.reshape(n[others[0]], n[others[1]], n[axis])
    return np.moveaxis(occ, [0, 1, 2], [others[0], others[1], axis])


def voxelize(mesh, pitch) -> Grid:
    """Massivvoxel des Meshes. Mehrheit aus drei Strahlrichtungen."""
    m = mesh.copy()
    m.merge_vertices()
    lo = np.asarray(m.bounds[0], dtype=float) - pitch
    hi = np.asarray(m.bounds[1], dtype=float) + pitch
    n = np.maximum(np.ceil((hi - lo) / pitch).astype(int), 1)
    votes = sum(_fill_axis(m, lo, n, pitch, a).astype(np.uint8) for a in range(3))
    return Grid(lo, pitch, votes >= 2)


# -- Anker ---------------------------------------------------------------

def poses(context, at=None) -> list:
    """Zu prüfende Posen. Machine -> Endlagen, Mitte und Standardwert je Motion."""
    if at is not None:
        return [at.state if isinstance(at, Scene) else at]
    if not isinstance(context, Machine):
        return [None]
    if not context.motions:
        return [context.state()]
    per = []
    for name, m in context.motions.items():
        rng = m.get('range')
        std = float(m.get('default', 0))
        vals = {std}
        if rng:
            lo, hi = float(rng[0]), float(rng[1])
            vals |= {lo, hi, (lo + hi) / 2.0}
        per.append([(name, v) for v in sorted(vals)])
    combos = list(product(*per))
    if len(combos) > MAX_POSEN:
        per = [[p for p in vals if p[1] in (vals[0][1], vals[-1][1],
                                            float(context.motions[p[0]].get('default', 0)))]
               for vals in per]
        combos = list(product(*per))[:MAX_POSEN]
    return [context.state(**dict(c)) for c in combos]


def scene_bodies(context, state, ausser) -> list:
    """Alle Fremdkörper einer Pose, ohne den Prüfling."""
    if isinstance(context, Machine):
        bodies = list(context.scene_at(state).bodies)
    elif isinstance(context, Scene):
        bodies = [(state.apply(b) if state is not None else b) for b in context.bodies]
    elif context is None:
        bodies = []
    else:
        items = context if isinstance(context, (list, tuple, set)) else [context]
        bodies = [(state.apply(b) if state is not None else b) for b in items]
    return [b for b in bodies if b.key not in ausser]


def _kd(mesh):
    """KD-Baum über die Mesh-Ecken plus längste Kante (konservative Vorfilterung)."""
    cached = getattr(mesh, '_pruefstand_relevanz_kd', None)
    if cached is not None:
        return cached
    from scipy.spatial import cKDTree
    v = np.asarray(mesh.vertices, dtype=float)
    tri = np.asarray(mesh.triangles, dtype=float)
    kante = 0.0
    if len(tri):
        e = np.concatenate([tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 1], tri[:, 0] - tri[:, 2]])
        kante = float(np.linalg.norm(e, axis=1).max())
    entry = (cKDTree(v), kante)
    try:
        object.__setattr__(mesh, '_pruefstand_relevanz_kd', entry)
    except Exception:  # pragma: no cover
        pass
    return entry


def contact_anchors(grid: Grid, rand_idx, rand_pts, bodies, kontakt_mm) -> tuple[np.ndarray, dict]:
    """Randvoxel, die einem Fremdkörper näher als `kontakt_mm` kommen."""
    seeds = np.zeros(grid.shape, dtype=bool)
    treffer: dict[str, int] = {}
    if not len(rand_idx):
        return seeds, treffer
    lo = rand_pts.min(axis=0) - kontakt_mm
    hi = rand_pts.max(axis=0) + kontakt_mm
    for b in bodies:
        m = b.mesh
        if m is None or len(m.faces) == 0:
            continue
        b0, b1 = m.bounds
        if np.any(b0 - kontakt_mm > hi) or np.any(b1 + kontakt_mm < lo):
            continue
        nah = np.all((rand_pts >= b0 - kontakt_mm - grid.pitch) & (rand_pts <= b1 + kontakt_mm + grid.pitch), axis=1)
        if not nah.any():
            continue
        cand = np.nonzero(nah)[0]
        tree, kante = _kd(m)
        # Untere Schranke: Abstand zur Oberfläche >= Abstand zur nächsten Ecke - längste Kante.
        grob = tree.query(rand_pts[cand], k=1)[0]
        cand = cand[grob <= kontakt_mm + kante]
        if not len(cand):
            continue
        d = _nearest.distances(rand_pts[cand], m)
        hit = cand[d <= kontakt_mm]
        if not len(hit):
            continue
        treffer[b.key] = treffer.get(b.key, 0) + int(len(hit))
        seeds[tuple(rand_idx[hit].T)] = True
    return seeds, treffer


def bores(solid) -> list[dict]:
    """Zylindrische Innenflächen eines build123d-Solids: Achse, Radius, axiale Spanne."""
    if solid is None:
        return []
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_Orientation
    out = []
    for f in solid.faces():
        if str(f.geom_type) != 'GeomType.CYLINDER':
            continue
        if f.wrapped.Orientation() != TopAbs_Orientation.TopAbs_REVERSED:
            continue                       # konvex: Zapfen oder Verrundung, keine Bohrung
        u0, u1, _, _ = BRepTools.UVBounds_s(f.wrapped)
        if np.degrees(u1 - u0) < MIN_BOHRUNG_GRAD:
            continue                       # Verrundung, keine umfassende Bohrung
        cyl = BRepAdaptor_Surface(f.wrapped).Cylinder()
        r = float(cyl.Radius())
        if r > MAX_BOHRUNG_MM:
            continue
        ax = cyl.Axis()
        o = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()], dtype=float)
        d = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()], dtype=float)
        d = d / np.linalg.norm(d)
        bb = f.bounding_box()
        ecken = np.array(list(product(*zip((bb.min.X, bb.min.Y, bb.min.Z),
                                           (bb.max.X, bb.max.Y, bb.max.Z)))), dtype=float)
        t = (ecken - o) @ d
        out.append({'origin': o, 'axis': d, 'radius': r, 'span': (float(t.min()), float(t.max()))})
    return out


def bore_anchors(grid: Grid, material, bohrungen) -> tuple[np.ndarray, int]:
    """Material im Ring um jede Bohrung."""
    seeds = np.zeros(grid.shape, dtype=bool)
    if not bohrungen:
        return seeds, 0
    idx = np.argwhere(material)
    if not len(idx):
        return seeds, 0
    pts = grid.centers(idx)
    n = 0
    for b in bohrungen:
        rel = pts - b['origin']
        t = rel @ b['axis']
        radial = np.linalg.norm(rel - t[:, None] * b['axis'], axis=1)
        hit = ((radial <= b['radius'] + 1.5 * grid.pitch)
               & (t >= b['span'][0] - grid.pitch) & (t <= b['span'][1] + grid.pitch))
        if not hit.any():
            continue
        seeds[tuple(idx[hit].T)] = True
        n += 1
    return seeds, n


# -- Funktionsmengen -----------------------------------------------------

#: Mehr Ankerquellen als das werden zusammengefasst (Laufzeit der Geodäten).
MAX_QUELLEN = 24
#: 26er-Nachbarschaft für Zusammenhang.
_NACHBARN = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)
             if (a, b, c) > (0, 0, 0)]


def hull_mask(grid: Grid, material, anker_pts, margin) -> np.ndarray | None:
    """Material innerhalb der um `margin` aufgeweiteten konvexen Hülle der Anker.

    Das ist die großzügige Lesart von „Materialkontinuum zwischen den Ankern“: was
    zwischen den Ankern eingeschlossen liegt, verbindet sie. Bewusst großzügig — die
    Hülle enthält auch Luft, aber Luft trägt kein Material bei.
    """
    from scipy.spatial import ConvexHull, QhullError
    if len(anker_pts) < 4:
        return None
    try:
        h = ConvexHull(np.asarray(anker_pts, dtype=float), qhull_options='QJ')
    except (QhullError, ValueError):       # pragma: no cover - entartete Ankerlage
        return None
    idx = np.argwhere(material)
    if not len(idx):
        return None
    pts = grid.centers(idx)
    A = h.equations[:, :3]
    b = h.equations[:, 3]
    drin = np.ones(len(pts), dtype=bool)
    for k in range(0, len(A), 64):
        drin &= np.all(pts @ A[k:k + 64].T + b[k:k + 64] <= margin, axis=1)
    out = np.zeros(grid.shape, dtype=bool)
    out[tuple(idx[drin].T)] = True
    return out


def _graph(material, pitch):
    """26er-Nachbarschaftsgraph der Materialvoxel, Kantengewicht = euklidischer Abstand."""
    from scipy import sparse
    n = int(material.sum())
    ids = np.full(material.shape, -1, dtype=np.int64)
    ids[material] = np.arange(n)
    rows, cols, w = [], [], []
    for d in _NACHBARN:
        a = [slice(None)] * 3
        b = [slice(None)] * 3
        for k in range(3):
            if d[k] == 1:
                a[k], b[k] = slice(0, -1), slice(1, None)
            elif d[k] == -1:
                a[k], b[k] = slice(1, None), slice(0, -1)
        A, B = ids[tuple(a)], ids[tuple(b)]
        m = (A >= 0) & (B >= 0)
        if not m.any():
            continue
        rows.append(A[m])
        cols.append(B[m])
        w.append(np.full(int(m.sum()), pitch * float(np.linalg.norm(d))))
    if not rows:
        return ids, sparse.csr_matrix((n, n))
    g = sparse.csr_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))),
                          shape=(n, n))
    return ids, (g + g.T).tocsr()


def detour_mask(material, pitch, quellen, tol) -> np.ndarray:
    """Material auf einem Lastpfad: geodätischer Umweg gegenüber der kürzesten
    Anker-zu-Anker-Verbindung höchstens `tol`.

    Für jedes Quellenpaar (i, j) ist D_ij der kürzeste Weg im Material zwischen beiden.
    Ein Voxel v mit d_i(v) + d_j(v) <= D_ij + tol liegt auf einer (fast) direkten
    Verbindung, trägt also. `tol` ist die geduldete Ausbuchtung; ein Überstand der
    Länge L über den direkten Pfad hinaus kostet 2·L, `tol = 2·r_anker` heißt also
    „bis r_anker neben dem Lastpfad zählt noch als Lastpfad“.
    """
    from scipy.sparse.csgraph import dijkstra
    out = np.zeros(material.shape, dtype=bool)
    if len(quellen) < 2 or not material.any():
        return out
    ids, g = _graph(material, pitch)
    n = int(material.sum())
    d = np.empty((len(quellen), n))
    for k, q in enumerate(quellen):
        src = ids[q & material]
        src = src[src >= 0]
        if not len(src):
            d[k] = np.inf
            continue
        d[k] = dijkstra(g, indices=src, min_only=True)
    umweg = np.full(n, np.inf)
    for i in range(len(quellen)):
        for j in range(i + 1, len(quellen)):
            s = d[i] + d[j]
            D = s.min()
            if np.isfinite(D):
                umweg = np.minimum(umweg, s - D)
    out[material] = umweg <= tol
    return out


def opening(mask) -> np.ndarray:
    """Morphologische Öffnung: einzelne Voxelhäute fallen weg, kompakte Klumpen bleiben.

    Ohne das melden dünne Wände ihre abgewandte Deckschicht als riesigen
    zusammenhängenden Befund — der teuerste Fehlalarm, den es hier gibt.
    """
    from scipy import ndimage
    kern = ndimage.generate_binary_structure(3, 1)
    kern_erodiert = ndimage.binary_erosion(mask, kern, border_value=0)
    return ndimage.binary_dilation(kern_erodiert, kern) & mask
