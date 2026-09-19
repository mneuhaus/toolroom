"""sweep(): fährt eine Teilemenge geradlinig durch die Maschine und meldet, wo es klemmt.

    sweep(parts, vector, distance, against, at=None, clearance_mm=0.0, resolution_mm=None)
    sweep(parts, motion='hub', to=130, against=scene.fixed)

Der Kern steckt in `_sweep.py`: konservatives Vorrücken statt Abtasten, damit dünne Wände
nicht zwischen zwei Stützstellen durchrutschen können.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..machine import Machine, Scene, State
from ..results import Result
from . import _fcl, _sweep
from ._common import as_bodies, empty, fenster_flag, prepare

#: Auflösung des Marsches in mm, wenn der Aufrufer nichts sagt. Zugleich Kontakttoleranz:
#: ein Abstand <= clearance_mm + resolution_mm gilt als Kontakt. Der Wert wirkt damit nur in
#: die sichere Richtung (früher Kontakt melden, nie später). 0,01 mm ist die Sehnentoleranz,
#: mit der die STL-Körper der Maschine tesselliert sind -- feiner zu messen wäre Fiktion.
RESOLUTION_MM = 0.01


@dataclass(repr=False)
class SweepResult(Result):
    collides: bool = False
    first_contact_mm: float | None = None
    pairs: list = field(default_factory=list)
    min_gap_mm: float = float('inf')
    travelled_mm: float = 0.0
    distance_mm: float = 0.0
    closest_pair: tuple = ()
    direction: object = None
    contacts: list = field(default_factory=list)
    touches: list = field(default_factory=list)
    touch_pairs: list = field(default_factory=list)
    steps: int = 0
    evaluations: int = 0
    passed: bool = True
    primitive: str = 'sweep'
    _fields: tuple = ('collides', 'first_contact_mm', 'travelled_mm', 'distance_mm',
                      'min_gap_mm', 'steps', 'evaluations', 'closest_pair', 'pairs', 'contacts',
                      'touch_pairs', 'direction')


def _machine_from(*cands) -> Machine | None:
    for c in cands:
        if isinstance(c, Machine):
            return c
        if isinstance(c, (Scene, State)):
            return c.machine
    from .. import context
    p = context.project()
    if p is None:
        return None
    cfg = p.spec / 'pruefstand.yaml'
    if not cfg.exists():
        return None
    import yaml
    data = yaml.safe_load(cfg.read_text()) or {}
    if not data.get('machine'):
        return None
    return Machine.load((p.spec / data['machine']).resolve())


def _from_motion(machine: Machine, motion: str, to, distance):
    if machine is None:
        raise ValueError(f"sweep(motion={motion!r}): Maschine unbekannt. `at=scene`, "
                         f"`machine=...` übergeben oder spec/pruefstand.yaml bereitstellen")
    m = machine.motions.get(motion)
    if m is None:
        raise KeyError(f'Motion {motion!r} unbekannt: {sorted(machine.motions)}')
    kind = m.get('kind', 'translation')
    if kind != 'translation':
        raise NotImplementedError(f'Motion-Art {kind!r} -- sweep kann bisher nur translation')
    axis = np.asarray(m.get('axis', (0, 0, 1)), dtype=float)
    vec = machine.frame(m.get('frame', 'local')).direction_to_world(axis)
    if to is None and distance is None:
        raise ValueError(f'sweep(motion={motion!r}) braucht `to=` (Zielwert) oder `distance=`')
    if to is None:
        return vec, float(distance)
    start = float(m.get('default', 0))
    span = float(to) - start
    return (vec if span >= 0 else -vec), abs(span)


def _norm_ignore(pairs):
    out = set()
    for p in pairs or ():
        a, b = p
        out.add(frozenset((str(a), str(b))))
    return frozenset(out)


def sweep(parts, vector=None, distance=None, against=None, at=None, clearance_mm=0.0,
          resolution_mm=None, motion=None, to=None, machine=None, ignore_pairs=(),
          within=None, ignore=None, max_step_mm=None, stop_at_first=True,
          allow_touch=False, touch_depth_mm=None) -> SweepResult:
    """`parts` um `vector` über `distance` mm gegen `against` fahren.

    vector wird normiert. Statt vector/distance kann `motion=` (Name aus machine.json) mit
    `to=` (Zielwert der Motion) stehen; Achse und Frame kommen dann aus der Maschine.

    clearance_mm: geforderte Luft. Alles enger gilt als Kollision.
    resolution_mm: Auflösung des Marsches und zugleich Kontakttoleranz (Default 0,01 mm).
      Wirkt nur konservativ: Kontakte werden eher zu früh als zu spät gemeldet.
    ignore_pairs: [(key_a, key_b), ...] -- nominale Dauerkontakte (Schiene im Wagen,
      Schraube im Gewinde). Reihenfolge egal.
    within/ignore: Regionen, die beide Seiten vorher beschneiden (wie bei gap()).
    allow_touch: Passflächen, die aufeinander gleiten, sind keine Kollision. Bei jedem Kontakt
      wird dann zusätzlich die Eindringtiefe gemessen; bis `touch_depth_mm` (Default
      `_fcl.TOUCH_TOL_MM`) gilt er als Berührung und der Marsch läuft weiter. Nur mit
      clearance_mm = 0 sinnvoll, sonst Fehler. Streift etwas, schrumpft der Schritt auf
      resolution_mm -- auch beim Gleiten wird also nichts übersprungen.
    max_step_mm: deckelt die Schrittweite. Nur nötig, wenn `min_gap_mm` möglichst genau sein
      soll -- für die Kollisionsaussage ändert es nichts.

    min_gap_mm ist der kleinste an den Auswertestellen gemessene Abstand. Die Kollisionsaussage
    gilt lückenlos für den ganzen Weg, der Zahlenwert min_gap_mm ist eine obere Schranke des
    wahren Minimums (mit max_step_mm beliebig eng zu machen).
    """
    A = as_bodies(parts, at)
    B = as_bodies(against, at)
    if motion is not None:
        vector, distance = _from_motion(_machine_from(machine, at, against, parts), motion, to, distance)
    if vector is None or distance is None:
        raise ValueError('sweep braucht vector + distance oder motion + to')
    u = np.asarray(vector, dtype=float).reshape(3)
    if not np.any(u):
        raise ValueError('vector ist der Nullvektor')
    u = u / float(np.linalg.norm(u))
    dist = float(distance)
    res = RESOLUTION_MM if resolution_mm is None else float(resolution_mm)

    mov = [(b.key, prepare(b, within, ignore)) for b in A]
    fix = [(b.key, prepare(b, within, ignore)) for b in B]
    mov = [(k, m) for k, m in mov if not empty(m)]
    fix = [(k, m) for k, m in fix if not empty(m)]

    if not mov or not fix:
        r = SweepResult(distance_mm=dist, direction=u, travelled_mm=dist, passed=False)
        r.urteil_auf = 'mesh'
        r.fenster_schneidet_material = fenster_flag(within, ignore)
        r.nichts_gemessen = True
        r.leer_grund = ('keine bewegten Körper' if not mov else 'keine Gegenkörper')
        r._publish()
        return r

    touch = None
    if allow_touch or touch_depth_mm is not None:
        if float(clearance_mm) != 0.0:
            raise ValueError('allow_touch nur mit clearance_mm=0 sinnvoll: eine geforderte Luft '
                             'und eine erlaubte Berührung schließen sich aus')
        touch = _fcl.TOUCH_TOL_MM if touch_depth_mm is None else float(touch_depth_mm)

    out = _sweep.march(mov, fix, u, dist, clearance=float(clearance_mm), tol=res,
                       max_step=max_step_mm, ignore=_norm_ignore(ignore_pairs),
                       stop_at_first=stop_at_first, touch_depth=touch)
    first = out['first_contact']
    pairs = sorted({(c['moving'], c['fixed']) for c in out['contacts']})
    tpairs = sorted({(c['moving'], c['fixed']) for c in out['touches']})
    r = SweepResult(
        collides=first is not None,
        first_contact_mm=None if first is None else round(float(first), 5),
        pairs=[list(p) for p in pairs],
        min_gap_mm=out['min_gap'],
        travelled_mm=dist if first is None else float(first),
        distance_mm=dist,
        closest_pair=out['closest'],
        direction=u,
        contacts=out['contacts'][:64],
        touches=out['touches'][:64],
        touch_pairs=[list(p) for p in tpairs],
        steps=out['steps'],
        evaluations=out['evaluations'],
        passed=first is None,
    )
    # Der Marsch fragt den Kollisionskern, und der kennt nur Netze. „Bewegung frei"
    # ist deshalb eine Aussage über die Tessellation, nicht über die exakten Flächen.
    r.urteil_auf = 'mesh'
    r.fenster_schneidet_material = fenster_flag(within, ignore)
    r._publish()
    return r
