"""access(): kommt das Werkzeug von außen an den Schraubenkopf?

Hülle als gestufter Zylinder entlang der Schraubenachse, vom Kopf nach außen:
Bit Ø5,7 (M3) bzw. Ø8,5 (M5), dann Schaft Ø4,8 x 112 mm, dann Griff Ø18 x 55 mm.
Die Hülle darf keinen anderen Körper schneiden. Der Startpunkt liegt 0,12 mm vor der
Kopfauflage (wie im Handbetrieb `check_access.py` der R6d-Baugruppe), damit die Hülle
nicht am angeschraubten Teil selbst hängenbleibt.

Bei bewegten Maschinen gilt der Zugang in der **Montagepose**: `at` nimmt einen `State`
(oder eine `Scene`) entgegen und verschiebt die bewegten Körper entsprechend.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..results import Result
from . import _axis, _fcl
from ._common import as_bodies, bbox_overlap, empty

#: Bit-Durchmesser je Nenngröße (Handbetrieb R6d).
BIT_D = {3.0: 5.7, 5.0: 8.5, 2.5: 4.5}


@dataclass(frozen=True)
class Tool:
    """Werkzeughülle. Längen in mm."""

    bit_d_mm: float | None = None      # None -> aus der Schraubengröße
    bit_len_mm: float = 25.0
    shaft_d_mm: float = 4.8
    shaft_len_mm: float = 112.0
    grip_d_mm: float = 18.0
    grip_len_mm: float = 55.0
    start_offset_mm: float = 0.12

    def bit(self, nominal: float) -> float:
        if self.bit_d_mm is not None:
            return float(self.bit_d_mm)
        for d, v in BIT_D.items():
            if abs(d - nominal) < 1e-9:
                return v
        raise ValueError(f'kein Bit-Durchmesser für M{nominal:g} bekannt; Tool(bit_d_mm=…) setzen')

    def segments(self, nominal: float) -> list[tuple[float, float, float]]:
        s = float(self.start_offset_mm)
        out = []
        for laenge, d in ((self.bit_len_mm, self.bit(nominal)),
                          (self.shaft_len_mm, self.shaft_d_mm),
                          (self.grip_len_mm, self.grip_d_mm)):
            if laenge > 0:
                out.append((s, s + float(laenge), float(d)))
                s += float(laenge)
        return out

    @property
    def total_mm(self) -> float:
        return float(self.start_offset_mm + self.bit_len_mm + self.shaft_len_mm + self.grip_len_mm)


@dataclass(repr=False)
class AccessResult(Result):
    free: bool = True
    blocked_by: list = field(default_factory=list)
    reach_mm: float = 0.0
    min_clearance_mm: float = float('inf')
    envelope_mm: float = 0.0
    screw_id: str = ''
    checked: int = 0
    passed: bool = True
    primitive: str = 'access'
    _fields: tuple = ('screw_id', 'free', 'reach_mm', 'envelope_mm', 'min_clearance_mm',
                      'checked', 'blocked_by')

    def summary(self) -> str:
        z = 'frei' if self.free else f'blockiert von {self.blocked_by}'
        return (f'access({self.screw_id}: {z}, reach={self.reach_mm:.1f}/{self.envelope_mm:.1f} mm, '
                f'clearance={self.min_clearance_mm:.2f} mm, {self.checked} Körper)')


def _envelope(origin, out_dir, segments, sections=48):
    return _axis.stepped_envelope(origin, out_dir, segments, sections=sections)


def _radius_at(segments, s):
    for s0, s1, d in segments:
        if s0 <= s < s1:
            return d / 2.0
    return segments[-1][2] / 2.0


def access(screw, scene, at=None, tool=None, *, frame=None, sections=48, slab_mm=1.0) -> AccessResult:
    """Werkzeugzugang zum Schraubenkopf prüfen."""
    from .screw_chain import resolve_frame
    if getattr(screw, 'nicht_gebaut', False):
        from ..results import NICHT_GEBAUT_MELDUNG, ohne_urteil
        return ohne_urteil('access', f'{screw.id}: {NICHT_GEBAUT_MELDUNG}')
    tool = tool or Tool()
    bodies = as_bodies(scene, at)
    nominal = screw.nominal_mm
    origin, u = screw.axis_points(resolve_frame(screw, frame, at, scene))
    out = -u
    _, e1, e2 = _axis.basis(u)
    dirs = _axis.ring(e1, e2, 36)
    eigene = _axis.self_bodies(bodies, origin, u, dirs, nominal, screw.laenge_mm)

    segs = tool.segments(nominal)
    huelle = _envelope(origin, out, segs, sections=sections)
    kandidaten = [b for b in bodies if b.key not in eigene and not empty(b.mesh)]

    blocked = []
    clearance = float('inf')
    for b in kandidaten:
        if not bbox_overlap(huelle, b.mesh, buffer=0.5):
            d, _, _ = _fcl.distance(huelle, b.mesh)
            clearance = min(clearance, d)
            continue
        tief, _, _ = _fcl.collide(huelle, b.mesh)
        if tief > 0:
            blocked.append(b.key)
        else:
            d, _, _ = _fcl.distance(huelle, b.mesh)
            clearance = min(clearance, d)

    gesamt = tool.total_mm
    reach = gesamt
    if blocked:
        clearance = 0.0
        stoerer = [b for b in kandidaten if b.key in blocked]
        reach = _reach(origin, out, segs, stoerer, gesamt, tool.start_offset_mm, slab_mm, sections)

    r = AccessResult(free=not blocked, blocked_by=sorted(blocked), reach_mm=float(reach),
                     min_clearance_mm=float(clearance), envelope_mm=float(gesamt),
                     screw_id=screw.id, checked=len(kandidaten), passed=not blocked and bool(kandidaten))
    # Werkzeughülle gegen Körpernetze: Freiheit und Reichweite sind Mesh-Urteile.
    r.urteil_auf = 'mesh'
    if not kandidaten:
        r.nichts_gemessen = True
        r.leer_grund = 'kein Körper, gegen den die Hülle geprüft werden könnte'
    r._publish()
    return r


def _reach(origin, out, segs, stoerer, gesamt, start, slab_mm, sections):
    """Erste Tiefe, an der ein Scheibchen der Hülle auf einen Störer trifft."""
    s = float(start)
    while s < gesamt - 1e-9:
        e = min(s + slab_mm, gesamt)
        scheibe = _envelope(origin, out, [(s, e, 2 * _radius_at(segs, s))], sections=sections)
        for b in stoerer:
            if bbox_overlap(scheibe, b.mesh, buffer=0.0) and _fcl.collide(scheibe, b.mesh)[0] > 0:
                return _verfeinern(origin, out, segs, stoerer, s, e, sections)
        s = e
    return gesamt


def _verfeinern(origin, out, segs, stoerer, lo, hi, sections, tol=0.05):
    frei = lo
    while hi - frei > tol:
        mid = 0.5 * (frei + hi)
        scheibe = _envelope(origin, out, [(lo, mid, 2 * _radius_at(segs, lo))], sections=sections)
        treffer = any(bbox_overlap(scheibe, b.mesh, buffer=0.0) and _fcl.collide(scheibe, b.mesh)[0] > 0
                      for b in stoerer)
        if treffer:
            hi = mid
        else:
            frei = mid
    return frei
