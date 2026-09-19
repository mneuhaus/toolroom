"""Gemeinsame Helfer der Primitive."""
from __future__ import annotations

import numpy as np

from ..body import Body
from ..machine import Scene, State

_crop_cache: dict = {}


def as_bodies(x, at=None) -> list[Body]:
    from .. import results
    if isinstance(x, Scene):
        # Szenen werden je Pose gecacht: beim zweiten Test mit derselben Pose läuft
        # `State.apply` nicht mehr, und die Pose stünde nicht im Bericht. Deshalb hier
        # noch einmal -- `merke_pose` entdoppelt selbst.
        results.merke_pose(x.state.values)
        items = list(x.bodies)
    elif isinstance(x, Body):
        items = [x]
    elif x is None:
        items = []
    else:
        items = list(x)
    for b in items:
        if not isinstance(b, Body):
            raise TypeError(f'Body erwartet, bekommen {type(b).__name__}')
    if at is not None:
        state = at.state if isinstance(at, Scene) else at
        if not isinstance(state, State):
            raise TypeError('at erwartet State oder Scene')
        results.merke_pose(state.values)
        items = [state.apply(b) for b in items]
    # Hier laufen alle Körper aller Primitive durch -- der einzige Ort, an dem sich
    # fürs Prüfbudget mitschreiben lässt, *woran* gemessen wurde, ohne jedes Primitiv
    # anzufassen.
    for b in items:
        results.merke_koerper(b.key, b.solid is not None)
    return items


def one_body(x, at=None) -> Body:
    items = as_bodies(x, at)
    if len(items) != 1:
        raise ValueError(f'genau ein Körper erwartet, bekommen {len(items)}')
    return items[0]


def cropped(mesh, region, complement=False):
    """Region.crop / crop_complement mit Cache je (Mesh, Region)."""
    if region is None:
        return mesh
    key = (id(mesh), id(region), complement)
    hit = _crop_cache.get(key)
    if hit is not None:
        return hit[0]
    m = region.crop_complement(mesh) if complement else region.crop(mesh)
    # Mesh UND Region festhalten: sonst wird ein freigegebenes Objekt recycelt und
    # eine spätere Region mit derselben id() bekommt stillschweigend den alten Schnitt.
    _crop_cache[key] = (m, mesh, region)
    return m


def prepare(body: Body, within=None, ignore=None):
    m = body.mesh
    if within is not None:
        m = cropped(m, within)
    if ignore is not None:
        m = cropped(m, ignore, complement=True)
    return m


def fenster_flag(*regionen):
    """Haben die Messfenster beim Zuschneiden Material angeschnitten?

    `None`, solange keine der Regionen zugeschnitten wurde -- der exakte Weg von
    `overlap` etwa schneidet mit `region.solid()` statt mit `crop()`, und dann hat
    niemand gemessen, ob die Fensterwand im Material liegt. Ein `False` an dieser
    Stelle wäre eine Behauptung, kein Messwert.
    """
    werte = [r.meta.get('rand_schneidet_material') for r in regionen if r is not None]
    werte = [v for v in werte if v is not None]
    return any(werte) if werte else None


def empty(mesh) -> bool:
    return mesh is None or len(mesh.faces) == 0


def bbox_overlap(ma, mb, buffer=0.5) -> bool:
    if empty(ma) or empty(mb):
        return False
    a0, a1 = ma.bounds
    b0, b1 = mb.bounds
    return bool(np.all(a1 >= b0 - buffer) and np.all(a0 <= b1 + buffer))


def total_diagonal(bodies) -> float:
    lo = None
    hi = None
    for b in bodies:
        m = b.mesh
        if empty(m):
            continue
        l, h = m.bounds
        lo = l if lo is None else np.minimum(lo, l)
        hi = h if hi is None else np.maximum(hi, h)
    if lo is None:
        return 0.0
    return float(np.linalg.norm(hi - lo))
