"""protrusion(): steht ein Teil in ein Volumen vor?"""
from __future__ import annotations

import numpy as np

from ..results import ProtrusionResult
from ._common import one_body


def protrusion(part, volume, at=None, max_mm3=0.0) -> ProtrusionResult:
    b = one_body(part, at)
    if b.solid is not None:
        rs = volume.solid()
        try:
            inter = b.solid.intersect(rs)
        except Exception:
            inter = None
        v = 0.0
        if inter is not None:
            v = float(inter.volume) if hasattr(inter, 'volume') else float(sum(s.volume for s in inter))
        hits = int(volume.contains(b.vertices()).sum())
        r = ProtrusionResult(volume_mm3=round(v, 6), hits=hits, exact=True, passed=v <= max_mm3 + 1e-9)
        r.urteil_auf = 'brep'
    else:
        hits = int(volume.contains(b.vertices()).sum())
        r = ProtrusionResult(volume_mm3=None, hits=hits, exact=False, passed=hits == 0)
        # Gezählte Eckpunkte im Quader: eine Wand kann mitten hindurchlaufen, ohne dass
        # eine Ecke drinliegt. Deshalb steht am Messwert, wie grob er zustande kam.
        r.urteil_auf = 'mesh'
    r._publish()
    return r
