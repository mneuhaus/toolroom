"""coverage(): Strahltest je Abtastpunkt einer Region."""
from __future__ import annotations

import re

import numpy as np

from .. import context
from ..results import CoverageResult
from ._common import as_bodies, empty, fenster_flag, total_diagonal


def _map_png(region, pts_world, covered, name):
    rev = context.review_dir()
    if rev is None or len(pts_world) == 0:
        return None
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    loc = region.frame.to_local(pts_world)
    spread = loc.max(axis=0) - loc.min(axis=0)
    drop = int(np.argmin(spread))
    axes = [i for i in range(3) if i != drop]
    xy = loc[:, axes]
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    span = np.maximum(hi - lo, 1e-6)
    w = h = 700
    pad = 30
    img = Image.new('RGB', (w, h), 'white')
    d = ImageDraw.Draw(img)
    px = pad + (xy[:, 0] - lo[0]) / span[0] * (w - 2 * pad)
    py = h - pad - (xy[:, 1] - lo[1]) / span[1] * (h - 2 * pad)
    for i in range(len(xy)):
        c = (40, 160, 60) if covered[i] else (210, 40, 40)
        d.ellipse([px[i] - 3, py[i] - 3, px[i] + 3, py[i] + 3], fill=c)
    d.text((8, 8), f'{name}  covered {int(covered.sum())}/{len(covered)}  Achsen {"xyz"[axes[0]]}/{"xyz"[axes[1]]}',
           fill=(20, 20, 20))
    out = rev / f'coverage-{re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:100]}.png'
    img.save(out)
    return out


def coverage(by, region, direction, at=None, max_open=None) -> CoverageResult:
    bodies = as_bodies(by, at)
    pts = np.atleast_2d(region.sample_points())
    dirn = np.asarray(direction, dtype=float).reshape(3)
    n = np.linalg.norm(dirn)
    if n == 0:
        raise ValueError('direction darf nicht null sein')
    dirn = dirn / n
    back = total_diagonal(bodies) + 50.0
    origins = pts - dirn * back
    dirs = np.tile(dirn, (len(pts), 1))
    covered = np.zeros(len(pts), dtype=bool)
    for b in bodies:
        m = b.mesh
        if empty(m):
            continue
        todo = ~covered
        if not todo.any():
            break
        hit = m.ray.intersects_any(origins[todo], dirs[todo])
        covered[todo] = np.asarray(hit, dtype=bool)
    total = int(len(pts))
    ncov = int(covered.sum())
    nopen = total - ncov
    tid = (context.test_id() or 'coverage').split('::')[-1]
    png = _map_png(region, pts, covered, tid)
    ok = (nopen == 0) if max_open is None else (nopen <= max_open)
    r = CoverageResult(total=total, covered=ncov, open=nopen, open_points=pts[~covered],
                       fraction=(ncov / total if total else 0.0), map_png=png,
                       passed=ok and total > 0)
    # Strahlen gegen Körpernetze -- abgedeckt/offen ist ein Mesh-Urteil.
    r.urteil_auf = 'mesh'
    r.fenster_schneidet_material = fenster_flag(region)
    if total == 0:
        r.nichts_gemessen = True
        r.leer_grund = 'total=0, kein Abtastpunkt'
    r._publish()
    return r
