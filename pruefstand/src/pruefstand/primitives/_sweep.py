"""Kollisionskern für geradlinige Sweeps: konservatives Vorrücken statt Abtasten.

Warum nicht abtasten: eine Bewegung in N gleich großen Schritten prüft nur N Posen. Alles,
was zwischen zwei Stützstellen liegt, wird nie gesehen. Eine 1,2 mm dünne Rippe quer im Weg
erzeugt bei einer 2-mm-Abtastung ein Kollisionsfenster von unter 2 mm Weglänge und rutscht
durch. Für ein Prüfwerkzeug ist das der schlimmste Fehlerfall: falsch grün.

Stattdessen **conservative advancement**. Der Abstand zweier starrer Körper ist unter einer
Translation 1-Lipschitz: verschiebt man einen um s, ändert sich der Abstand um höchstens s.
Ist der Abstand an der Stelle t also d, dann ist auf dem ganzen Intervall [t, t + (d - c)]
garantiert noch mindestens c Luft. Genau so groß wird der nächste Schritt gewählt. Damit
kann per Konstruktion nichts übersprungen werden -- unabhängig davon, wie dünn die Wand ist.
Je enger es wird, desto kleiner werden die Schritte von selbst.

Zwei Beschleuniger, beide ohne Verlust an Sicherheit:

* **AABB-Fenster:** für ein Paar ist in jeder Achse genau das t-Intervall bestimmbar, in dem
  sich die (um c aufgeblähten) Bounding-Boxen überhaupt überlappen. Der Schnitt über die drei
  Achsen ist wieder ein Intervall. Außerhalb ist das Paar beweisbar frei und wird nie an fcl
  gereicht.
* **Fälligkeitsliste:** jedes Paar merkt sich, ab wann es frühestens wieder eng werden kann
  (`t + d - c`). Der Marsch springt immer zum kleinsten dieser Zeitpunkte. Pro Schritt wird
  also nur das eine Paar neu gerechnet, das gerade den Takt vorgibt.

Fortschrittsgarantie: ein Paar gilt ab `d <= c + tol` als Kontakt, jeder Schritt ist deshalb
mindestens `tol` lang. Der Marsch endet also spätestens nach `weg / tol` Schritten.

Gehört fachlich nach `primitives/_fcl.py` -- dort fehlt eine Distanzfunktion, die einen
Körper um einen Vektor versetzt misst, ohne das Mesh zu kopieren (siehe Bericht).
"""
from __future__ import annotations

import numpy as np

from . import _fcl

_EPS = 1e-12


def distance_at(mesh_a, mesh_b, offset) -> float:
    """Abstand in mm, wobei `mesh_a` gedanklich um `offset` versetzt liegt.

    Das Mesh wird nicht angefasst: der Versatz sitzt in der fcl-Transform, das BVH-Modell
    kommt aus dem Cache von `_fcl.bvh`. Bei Durchdringung liefert fcl auf BVH-Modellen 0.0
    (keine negative Tiefe), das reicht hier -- 0.0 ist Kontakt.
    """
    fcl = _fcl.fcl
    if fcl is None:  # pragma: no cover
        raise RuntimeError('python-fcl fehlt')
    oa = fcl.CollisionObject(_fcl.bvh(mesh_a), fcl.Transform(np.asarray(offset, dtype=float)))
    ob = fcl.CollisionObject(_fcl.bvh(mesh_b), fcl.Transform())
    res = fcl.DistanceResult()
    d = fcl.distance(oa, ob, fcl.DistanceRequest(), res)
    if d is None or d < 0.0:
        return 0.0
    return float(d)


def penetration_at(mesh_a, mesh_b, offset) -> float:
    """Größte Eindringtiefe in mm, `mesh_a` um `offset` versetzt. 0.0 = nur Berührung.

    fcl liefert auf BVH-Modellen für Durchdringung wie für Berührung Abstand 0.0. Erst die
    Kontakttiefe trennt beides: konstruktiv aufeinanderliegende tessellierte Flächen (Passung,
    Auflage) geben 0.0, echtes Ineinanderstecken Größenordnungen mehr.
    """
    fcl = _fcl.fcl
    oa = fcl.CollisionObject(_fcl.bvh(mesh_a), fcl.Transform(np.asarray(offset, dtype=float)))
    ob = fcl.CollisionObject(_fcl.bvh(mesh_b), fcl.Transform())
    req = fcl.CollisionRequest(num_max_contacts=64, enable_contact=True)
    res = fcl.CollisionResult()
    fcl.collide(oa, ob, req, res)
    return max((abs(float(c.penetration_depth)) for c in res.contacts), default=0.0)


def aabb_window(bounds_a, bounds_b, u, length, clearance):
    """t-Intervall, in dem sich die AABBs (b um `clearance` aufgebläht) überlappen können.

    `bounds_a` gehört zum bewegten Körper, er läuft von t=0 bis t=`length` entlang `u`.
    Rückgabe (t_in, t_out) geschnitten mit [0, length], oder None wenn es nie überlappt.
    """
    a0, a1 = np.asarray(bounds_a[0], float), np.asarray(bounds_a[1], float)
    b0 = np.asarray(bounds_b[0], float) - clearance
    b1 = np.asarray(bounds_b[1], float) + clearance
    lo, hi = 0.0, float(length)
    for i in range(3):
        # a0+t*u <= b1  und  a1+t*u >= b0
        hi_i = b1[i] - a0[i]
        lo_i = b0[i] - a1[i]
        ui = float(u[i])
        if abs(ui) < 1e-15:
            if lo_i > 0.0 or hi_i < 0.0:
                return None
            continue
        t1, t2 = lo_i / ui, hi_i / ui
        if t1 > t2:
            t1, t2 = t2, t1
        lo = max(lo, t1)
        hi = min(hi, t2)
        if lo > hi:
            return None
    return lo, hi


def march(moving, fixed, direction, length, clearance=0.0, tol=0.01, max_step=None,
          ignore=frozenset(), stop_at_first=True, touch_depth=None):
    """Ein bewegter Satz Körper geradlinig gegen einen festen Satz.

    `moving`/`fixed`: Listen von (key, mesh). `direction`: Einheitsvektor. Alle Längen mm.
    Ein Paar gilt ab `d <= clearance + tol` als Kontakt.

    `touch_depth` (mm) trennt Streifen von Klemmen: ist es gesetzt, wird bei jedem Kontakt die
    Eindringtiefe gemessen; liegt sie darunter, zählt der Kontakt als Berührung (gleitende
    Passfläche) und der Marsch läuft weiter. Ohne den Wert blockiert jede Berührung.

    Rückgabe dict: first_contact (float|None), contacts (Liste), touches (Liste), min_gap,
    closest, steps, evaluations, pairs_considered.
    """
    u = np.asarray(direction, dtype=float).reshape(3)
    n = float(np.linalg.norm(u))
    if n <= 0:
        raise ValueError('Richtung ist der Nullvektor')
    u = u / n
    length = float(length)
    if length < 0:
        raise ValueError(f'weg muss >= 0 sein, ist {length}')
    tol = float(tol)
    if tol <= 0:
        raise ValueError('tol muss > 0 sein (sonst terminiert der Marsch nicht)')

    first = None
    contacts = []
    touches = []
    min_gap = float('inf')
    closest = ()
    steps = 0
    evals = 0
    considered = 0

    for mk, mm in moving:
        if mm is None or len(mm.faces) == 0:
            continue
        mb = mm.bounds
        cand = []
        for fk, fm in fixed:
            if fm is None or len(fm.faces) == 0:
                continue
            if fk == mk or frozenset((mk, fk)) in ignore:
                continue
            w = aabb_window(mb, fm.bounds, u, length, clearance)
            if w is None:
                continue
            cand.append([w[0], w[1], fk, fm, w[0]])      # t_in, t_out, key, mesh, next_eval
        considered += len(cand)
        if not cand:
            continue

        t = 0.0
        body_hit = None
        guard = int(length / tol) + len(cand) + 16
        while True:
            steps += 1
            if steps > guard:  # pragma: no cover -- Fortschrittsgarantie verletzt
                raise RuntimeError(f'Sweep terminiert nicht bei {mk} (t={t:.4f}, {steps} Schritte)')
            due = [c for c in cand if c[4] <= t + _EPS and t <= c[1] + _EPS]
            for c in due:
                evals += 1
                d = distance_at(mm, c[3], u * t)
                if d < min_gap:
                    min_gap = d
                    closest = (mk, c[2])
                if d <= clearance + tol:
                    depth = None
                    if touch_depth is not None:
                        depth = penetration_at(mm, c[3], u * t)
                    if depth is not None and depth <= touch_depth:
                        if len(touches) < 4096:
                            touches.append({'moving': mk, 'fixed': c[2], 'at_mm': round(t, 5),
                                            'depth_mm': round(depth, 5)})
                        c[4] = t + tol                 # streifen, weiterfahren
                        continue
                    entry = {'moving': mk, 'fixed': c[2], 'at_mm': round(t, 5),
                             'gap_mm': round(d, 5)}
                    if depth is not None:
                        entry['depth_mm'] = round(depth, 5)
                    contacts.append(entry)
                    body_hit = t if body_hit is None else min(body_hit, t)
                else:
                    step = d - clearance
                    if max_step is not None:
                        step = min(step, float(max_step))
                    c[4] = max(t + step, c[0])
            if body_hit is not None and stop_at_first:
                break
            nxt = None
            for c in cand:
                if c[4] > c[1] + _EPS:
                    continue                                  # Fenster durchlaufen, Paar erledigt
                if nxt is None or c[4] < nxt:
                    nxt = c[4]
            if nxt is None or nxt > length + _EPS:
                break
            if nxt <= t + _EPS:  # pragma: no cover -- darf nach Konstruktion nicht passieren
                raise RuntimeError(f'Sweep kommt bei {mk} nicht voran (t={t})')
            t = nxt
        if body_hit is not None:
            first = body_hit if first is None else min(first, body_hit)

    return {'first_contact': first, 'contacts': contacts, 'touches': touches, 'min_gap': min_gap,
            'closest': closest, 'steps': steps, 'evaluations': evals,
            'pairs_considered': considered}
