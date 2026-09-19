"""Abtastung entlang einer Schraubenachse: freier Lochdurchmesser, Ein-/Austritt, Restwand.

Gemessen wird **auf dem Netz**, nicht an Feature-Namen. Je Tiefenschritt sitzt ein
Kreisring aus `directions` Strahlen senkrecht zur Achse; der erste Treffer je Richtung
gibt den freien Radius, das Minimum über alle Richtungen den freien Durchmesser.

Auflösung (gemessen, siehe tests/test_screw_chain.py):
- Die Strahlen starten exakt auf der Achse. Für ein rundes Loch liefert jede Richtung
  denselben Radius; der Winkelraster bestimmt also **nicht** die Genauigkeit, sondern nur,
  wie sicher eine unrunde Störstelle getroffen wird. 72 Richtungen = 5° Raster.
- Der systematische Fehler kommt aus der Tessellation: ein Zylinder wird als
  einbeschriebenes Vieleck abgebildet, der gemessene Durchmesser ist also minimal zu klein.
  Bei den STEP-Tessellationen des Prüfstands (Sehnentoleranz 0,01 mm) liegt der Fehler
  unter 0,01 mm. Gemessen an der echten Riemenklemme: Ø2,620 (Soll 2,62) und Ø3,400
  (Soll 3,4) -- der Abstand zwischen Pilot und Durchgang beträgt 0,78 mm und ist damit
  rund 80-mal größer als die Messunsicherheit.
- Ein- und Austritt werden nach dem groben Raster (`step_mm`) per Bisektion auf 0,001 mm
  nachgezogen.

Ob ein Körper überhaupt ein Glied der Kette ist, entscheidet die **Umschließung**: nur
wenn fast alle Richtungen treffen, liegt die Achse in einem Loch dieses Körpers.
Ob die Achse in Material statt in einem Loch liegt, entscheidet die Richtung der
Flächennormale des ersten Treffers: nach außen zeigend = Material auf der Achse
(typisch der Schraubenkörper selbst), zur Achse zeigend = Lochwand.
"""
from __future__ import annotations

import numpy as np

UMSCHLIESSUNG = 0.9
"""Anteil der Richtungen, der treffen muss, damit ein Körper als Glied zählt."""

MATERIAL_ANTEIL = 0.5
"""Ab diesem Anteil nach außen zeigender Normalen liegt die Achse in Material."""


def basis(direction) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(u, e1, e2): Einheitsachse und zwei Querachsen."""
    u = np.asarray(direction, dtype=float).reshape(3)
    n = float(np.linalg.norm(u))
    if n == 0.0:
        raise ValueError('Achsrichtung darf nicht null sein')
    u = u / n
    helper = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(u, helper)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    return u, e1, e2


def ring(e1, e2, n: int) -> np.ndarray:
    a = np.linspace(0.0, 2 * np.pi, int(n), endpoint=False)
    return np.cos(a)[:, None] * e1 + np.sin(a)[:, None] * e2


class Slice:
    """Radialprofil eines Körpers an einer Tiefe."""

    __slots__ = ('dist', 'outward', 'r_max')

    def __init__(self, dist, outward, r_max):
        self.dist = dist            # (N,) Abstand zum ersten Treffer, inf wenn keiner
        self.outward = outward      # (N,) bool: Normale zeigt von der Achse weg
        self.r_max = float(r_max)

    @property
    def hits(self) -> np.ndarray:
        return np.isfinite(self.dist)

    @property
    def enclosure(self) -> float:
        return float(self.hits.mean()) if len(self.dist) else 0.0

    @property
    def enclosed(self) -> bool:
        return self.enclosure >= UMSCHLIESSUNG

    @property
    def material(self) -> bool:
        h = self.hits
        if not h.any():
            return False
        return bool(self.outward[h].mean() >= MATERIAL_ANTEIL)

    @property
    def d_min(self) -> float:
        h = self.hits
        return float(2.0 * self.dist[h].min()) if h.any() else float('inf')

    @property
    def d_max(self) -> float:
        h = self.hits
        return float(2.0 * self.dist[h].max()) if h.any() else float('inf')

    def lobes(self) -> int:
        """Zahl der nach innen ragenden Rippen (zusammenhängende Winkelgruppen unter
        dem Mittelwert von kleinstem und größtem Radius)."""
        h = self.hits
        if not h.all():
            return 0
        r = self.dist
        schwelle = 0.5 * (r.min() + r.max())
        # Unter 0,1 mm Radienspreizung ist das Tessellationsrauschen eines runden Lochs,
        # keine Rippe (echte Crush-Rippen ragen rund 0,4 mm ein).
        if r.max() - r.min() < 0.05:
            return 0
        eng = r < schwelle - 1e-9
        if not eng.any():
            return 0
        # zirkuläre Gruppen zählen
        wechsel = np.sum(eng & ~np.roll(eng, 1))
        return int(wechsel)


def profile(mesh, origin, dirs, r_max) -> Slice:
    """Radialprofil an einem Achsenpunkt."""
    n = len(dirs)
    dist = np.full(n, np.inf)
    outward = np.zeros(n, dtype=bool)
    if mesh is None or len(mesh.faces) == 0:
        return Slice(dist, outward, r_max)
    origins = np.tile(np.asarray(origin, dtype=float), (n, 1))
    locs, idx_ray, idx_tri = mesh.ray.intersects_location(origins, dirs, multiple_hits=False)
    if len(idx_ray):
        d = np.linalg.norm(locs - origins[idx_ray], axis=1)
        keep = d <= r_max
        if keep.any():
            nrm = np.asarray(mesh.face_normals)[np.asarray(idx_tri)[keep]]
            dot = np.einsum('ij,ij->i', nrm, dirs[np.asarray(idx_ray)[keep]])
            for k, r in enumerate(np.asarray(idx_ray)[keep]):
                if d[keep][k] < dist[r]:
                    dist[r] = d[keep][k]
                    outward[r] = bool(dot[k] > 0.0)
    return Slice(dist, outward, r_max)


def scan(mesh, origin, u, dirs, depths, r_max) -> list[Slice]:
    return [profile(mesh, origin + u * t, dirs, r_max) for t in depths]


def refine(mesh, origin, u, dirs, r_max, innen, aussen, tol=1e-3) -> float:
    """Bisektion der Grenze zwischen `innen` (umschlossen) und `aussen`."""
    lo, hi = float(innen), float(aussen)
    for _ in range(40):
        if abs(hi - lo) <= tol:
            break
        mid = 0.5 * (lo + hi)
        s = profile(mesh, origin + u * mid, dirs, r_max)
        if s.enclosed or s.material:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def wall(mesh, origin, u, dirs, depths, r_max) -> float:
    """Dünnste Restwand: kleinster Abstand zwischen erstem und zweitem Treffer einer
    Radialrichtung, über alle Tiefen. `inf`, wenn nirgends ein zweiter Treffer liegt."""
    best = float('inf')
    n = len(dirs)
    for t in depths:
        o = origin + u * t
        origins = np.tile(o, (n, 1))
        locs, idx_ray, _ = mesh.ray.intersects_location(origins, dirs, multiple_hits=True)
        if not len(idx_ray):
            continue
        d = np.linalg.norm(locs - o, axis=1)
        je_richtung: dict[int, list[float]] = {}
        for k, r in enumerate(np.asarray(idx_ray)):
            je_richtung.setdefault(int(r), []).append(float(d[k]))
        for ds in je_richtung.values():
            ds = sorted(x for x in ds if x <= r_max)
            # erster Sprung: von der Lochwand bis zur nächsten Materialgrenze
            for a, b in zip(ds, ds[1:]):
                if b - a > 1e-6:
                    best = min(best, b - a)
                    break
    return best


def stepped_envelope(origin, direction, segments, sections=48):
    """Gestufter Zylinder als trimesh. `segments` = [(start_mm, end_mm, durchmesser_mm)]
    entlang `direction` ab `origin`."""
    import trimesh
    u = np.asarray(direction, dtype=float).reshape(3)
    u = u / np.linalg.norm(u)
    T0 = trimesh.geometry.align_vectors([0, 0, 1], u)
    teile = []
    for s0, s1, d in segments:
        h = float(s1) - float(s0)
        if h <= 0 or d <= 0:
            continue
        T = T0.copy()
        T[:3, 3] = np.asarray(origin, dtype=float) + u * (float(s0) + h / 2.0)
        teile.append(trimesh.creation.cylinder(radius=float(d) / 2.0, height=h,
                                               sections=sections, transform=T))
    if not teile:
        raise ValueError('leere Werkzeughülle')
    return trimesh.util.concatenate(teile) if len(teile) > 1 else teile[0]


def self_bodies(bodies, origin, u, dirs, nominal, laenge, step_mm=0.5, tol=0.3) -> set:
    """Keys der Körper, die **selbst die Schraube** sind: Material auf der Achse über die
    ganze Schaftlänge und mit dem Nenndurchmesser (±tol)."""
    keys = set()
    depths = np.arange(step_mm, max(laenge - step_mm, step_mm) + 1e-9, step_mm)
    for b in bodies:
        s = scan(b.mesh, origin, u, dirs, depths, r_max=nominal + 4.0)
        treffer = [x for x in s if x.hits.any()]
        if not treffer or len(treffer) < 0.9 * len(depths):
            continue
        if all(x.material for x in treffer) and abs(np.median([x.d_min for x in treffer]) - nominal) <= tol:
            keys.add(b.key)
    return keys
