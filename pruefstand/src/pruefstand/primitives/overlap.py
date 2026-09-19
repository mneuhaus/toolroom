"""overlap(): Überschneidung zweier Körpermengen, exakt oder über Meshes."""
from __future__ import annotations

from .. import kernel
from ..results import KernelFehler, OverlapResult
from . import _fcl
from ._common import as_bodies, bbox_overlap, empty, fenster_flag, prepare

_EPS = 1e-9


def _solid_volume(shape) -> float:
    if shape is None:
        return 0.0
    try:
        if hasattr(shape, 'volume'):
            return float(shape.volume)
        return float(sum(s.volume for s in shape))
    except Exception as e:
        raise KernelFehler(f'Volumen nicht bestimmbar: {e}') from e


def _intersect_volume(sa, sb):
    """(Volumen, Ort) des Schnitts. Ort ist None, wenn der Wächter gerechnet hat --
    der liefert nur eine Zahl zurück, und einen Ort zu erfinden wäre schlimmer als
    keiner."""
    if kernel.aktiv():
        # Im Rechenprozess wird auch ein harter Absturz zu einem KernelFehler statt
        # zum stillen Ende des ganzen Laufs.
        return kernel.rechne('schnitt', kernel.schreibe(sa), kernel.schreibe(sb)), None
    try:
        r = sa.intersect(sb)
    except Exception as e:
        raise KernelFehler(f'Schnitt gescheitert: {e}') from e
    v = _solid_volume(r)
    ort = None
    if v > _EPS:
        try:
            ort = [round(float(x), 4) for x in tuple(r.center())]
        except Exception:
            ort = None
    return v, ort


def _side_empty(bodies, within) -> bool:
    """Hat diese Seite nach dem Beschneiden auf `within` überhaupt noch Geometrie?"""
    return not any(not empty(prepare(b, within)) for b in bodies)


def overlap(a, b, at=None, within=None, max_mm3=None) -> OverlapResult:
    A = as_bodies(a, at)
    B = as_bodies(b, at)
    exact = bool(A) and bool(B) and all(x.solid is not None for x in A) and all(x.solid is not None for x in B)
    pairs = []
    total = 0.0
    collides = False
    contacts = 0
    depth = 0.0
    touching = False
    touch_pairs = []
    orte: list = []
    region_solid = None
    kernel_fehler: list[str] = []
    if exact and within is not None:
        region_solid = within.solid()
    for ba in A:
        ma = None if exact else prepare(ba, within)
        if not exact and empty(ma):
            continue
        for bb in B:
            if ba is bb:
                continue
            if exact:
                if not bbox_overlap(ba.mesh, bb.mesh, 0.5):
                    continue
                sa = ba.solid
                if region_solid is not None:
                    try:
                        sa = sa.intersect(region_solid)
                        if _solid_volume(sa) <= _EPS:
                            continue
                    except Exception as e:
                        kernel_fehler.append(f'{ba.key}: Beschnitt auf die Region gescheitert ({e})')
                        continue
                try:
                    v, ort = _intersect_volume(sa, bb.solid)
                except KernelFehler as e:
                    kernel_fehler.append(f'{ba.key} gegen {bb.key}: {e}')
                    continue
                total += v
                hit = v > _EPS
                collides = collides or hit
                pairs.append((ba.key, bb.key, round(v, 6), hit))
                if hit and ort is not None:
                    orte.append(ort)
            else:
                mb = prepare(bb, within)
                if empty(mb) or not bbox_overlap(ma, mb, 0.5):
                    continue
                n, d, n_touch, punkte = _fcl.collide_punkte(ma, mb)
                if n:
                    collides = True
                    contacts += n
                    depth = max(depth, d)
                    pairs.append((ba.key, bb.key, None, True))
                    orte.extend(punkte)
                elif n_touch:
                    touching = True
                    touch_pairs.append((ba.key, bb.key))
    volume = round(total, 6) if exact else None
    leer_seite = ''
    if _side_empty(A, within):
        leer_seite = 'a'
    elif _side_empty(B, within):
        leer_seite = 'b'
    if max_mm3 is not None:
        ok = (volume is not None and volume <= max_mm3)
    else:
        ok = not collides
    ok = ok and not leer_seite
    r = OverlapResult(volume_mm3=volume, collides=collides, exact=exact, contacts=contacts,
                      max_penetration_mm=depth, pairs=pairs, touching=touching,
                      touch_pairs=touch_pairs, contact_points=orte[:64], passed=ok)
    r.urteil_auf = 'brep' if exact else 'mesh'
    r.fenster_schneidet_material = fenster_flag(within)
    if kernel_fehler:
        # Ein Paar, das der Kern nicht rechnen konnte, ist kein Paar ohne Überschneidung.
        r.technischer_fehler = True
        r.fehler_grund = '; '.join(kernel_fehler)
        r._publish()
        return r
    if leer_seite:
        r.nichts_gemessen = True
        r.leer_grund = f'Seite {leer_seite} ist im Ausschnitt leer'
    r._publish()
    return r
