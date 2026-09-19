"""same_as(): Region geometrisch unverändert gegenüber dem Vorgänger."""
from __future__ import annotations

import numpy as np

from .. import kernel
from ..body import Body
from ..results import KernelFehler, SameAsResult
from . import _nearest
from ._common import empty, fenster_flag, one_body

MAX_SAMPLES = 200_000
PER_MM2 = 5.0


def _sample(src, region):
    """Abtastpunkte auf der Oberfläche des bereits beschnittenen Meshes."""
    import trimesh
    if empty(src):
        return np.zeros((0, 3))
    area = float(src.area)
    n = int(min(MAX_SAMPLES, max(1000, round(PER_MM2 * area))))
    pts, _ = trimesh.sample.sample_surface(src, n, seed=0)
    pts = np.asarray(pts, dtype=float)
    keep = region.contains(pts)
    return pts[keep]


def _ausnehmen(pts, erwartet):
    """Abtastpunkte in einer erwarteten Region verwerfen.

    Nicht jede Änderung ist eine Abweichung: wer eine Pilotbohrung ergänzt, hat die
    Schnittstelle nicht verlassen. Solche Stellen werden benannt und herausgenommen --
    benannt, nicht weggerechnet: die Zahl der verworfenen Punkte steht im Ergebnis.
    """
    if len(pts) == 0 or not erwartet:
        return pts, 0
    drin = np.zeros(len(pts), dtype=bool)
    for r in erwartet:
        drin |= np.asarray(r.contains(pts), dtype=bool)
    return pts[~drin], int(drin.sum())


def _max_dist(pts, mesh):
    if len(pts) == 0 or empty(mesh):
        return 0.0, 0
    return float(np.max(_nearest.distances(pts, mesh))), len(pts)


def _vol(shape):
    if shape is None:
        return 0.0
    if hasattr(shape, 'volume'):
        return float(shape.volume)
    return float(sum(s.volume for s in shape))


def _cut(a, b):
    if a is None:
        return None
    if b is None:
        return a
    try:
        return a.cut(b)
    except Exception as e:
        # Nicht None zurückgeben: _vol(None) ist 0.0, und ein gescheiterter Schnitt
        # würde sonst als „kein Unterschied, exakt gerechnet" gemeldet.
        raise KernelFehler(f'Differenz gescheitert: {e}') from e


def _differenz_volumen(a, b) -> float:
    """Volumen von a ohne b -- bewacht, wenn der Kernwächter läuft."""
    if a is None:
        return 0.0
    if b is None:
        return _vol(a)
    if kernel.aktiv():
        return kernel.rechne('differenz', kernel.schreibe(a), kernel.schreibe(b))
    return _vol(_cut(a, b))


def same_as(part, predecessor, region, at=None, max_deviation_mm=None, erwartet=()) -> SameAsResult:
    a = one_body(part, at)
    if predecessor is None or (not isinstance(predecessor, Body) and not list(predecessor)):
        # Kein Vorgänger zugeordnet. Das ist nicht „unverändert" -- ohne Gegenstück
        # gibt es nichts zu vergleichen, und ein fehlender Anker beweist gar nichts.
        r = SameAsResult(passed=False)
        r.unentschieden = True
        r.offen_grund = f'kein Vorgänger zu {a.key!r} zugeordnet'
        r._publish()
        return r
    b = one_body(predecessor, at)
    # Beide Seiten auf denselben Ausschnitt beschneiden und auch gegen diesen messen.
    # Vorher wurde aus dem beschnittenen Netz abgetastet, aber gegen das volle
    # Gegenstück gemessen -- die beiden Richtungen sahen unterschiedliche Geometrie.
    ma = region.crop(a.mesh)
    mb = region.crop(b.mesh)
    pa = _sample(ma, region)
    pb = _sample(mb, region)
    erwartet = list(erwartet or ())
    pa, aus_a = _ausnehmen(pa, erwartet)
    pb, aus_b = _ausnehmen(pb, erwartet)
    d1, n1 = _max_dist(pa, mb)
    d2, n2 = _max_dist(pb, ma)
    dev = max(d1, d2)
    diff = None
    exact = False
    kernel_grund = ''
    if a.solid is not None and b.solid is not None:
        rs = region.solid()
        try:
            sa = a.solid.intersect(rs)
            sb = b.solid.intersect(rs)
            diff = round(_differenz_volumen(sa, sb) + _differenz_volumen(sb, sa), 6)
            exact = True
        except Exception as e:
            diff = None
            kernel_grund = f'BRep-Differenz gescheitert: {e}'
    samples = n1 + n2
    ok = (True if max_deviation_mm is None else dev <= max_deviation_mm) and samples > 0
    r = SameAsResult(max_deviation_mm=dev, diff_mm3=diff, samples=samples, exact=exact,
                     erwartet_ausgenommen=aus_a + aus_b, passed=ok)
    # `exact` sagt nur, dass das Differenzvolumen aus dem BRep stammt. Das Urteil in
    # `passed` kommt aus der abgetasteten Mesh-Abweichung -- das ist nicht dasselbe.
    r.urteil_auf = 'mesh'
    r.fenster_schneidet_material = fenster_flag(region)
    if kernel_grund:
        r.technischer_fehler = True
        r.fehler_grund = kernel_grund
        r._publish()
        return r
    if samples == 0:
        r.nichts_gemessen = True
        r.leer_grund = 'samples=0, keine Fläche im Ausschnitt'
    r._publish()
    return r
