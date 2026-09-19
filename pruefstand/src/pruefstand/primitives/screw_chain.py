"""screw_chain(): Kette der Körper entlang einer Schraubenachse.

Marcs Regel (M3 in PLA): Durchgangsloch Ø3,4, Pilotloch Ø2,62 (das Gewinde schneidet
sich selbst), Crush-Grip Ø4,2 mit 3 Rippen. **Nur das letzte Glied der Kette beißt** --
eine Schraube, die in zwei Teilen gleichzeitig beißt, verspannt sie gegeneinander.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..results import Result
from . import _axis
from ._common import as_bodies

#: Lochdurchmesser je Nenndurchmesser. M3 aus Marcs Konstruktionspraxis.
LOCHTABELLE = {
    3.0: {'durchgang': 3.4, 'pilot': 2.62, 'crush': 4.2},
}
#: Für Größen ohne Eintrag skaliert der Prüfstand die M3-Verhältnisse und sagt es im Ergebnis.
_SKALIERT = {'durchgang': 3.4 / 3.0, 'pilot': 2.62 / 3.0, 'crush': 4.2 / 3.0}

RIPPEN_SOLL = 3
KIND_FREI = 'frei'


def lochtabelle(nominal: float) -> tuple[dict, str]:
    for d, tab in LOCHTABELLE.items():
        if abs(d - nominal) < 1e-9:
            return dict(tab), 'tabelle'
    return {k: round(v * nominal, 3) for k, v in _SKALIERT.items()}, 'skaliert'


def _kind(d_min: float, d_max: float, lobes: int, tab: dict) -> str:
    """Nächstliegende Nennbohrung. Grenzen liegen auf den Mittelwerten benachbarter
    Nennmaße (M3: 3,01 zwischen Pilot und Durchgang; 3,80 zwischen Durchgang und Crush)."""
    pilot, durch, crush = tab['pilot'], tab['durchgang'], tab['crush']
    if d_min < 0.5 * (pilot + durch):
        return 'pilot'
    if d_min < 0.5 * (durch + crush):
        # Crush-Grip: Rippen ragen unter den Durchgang, der Grundkreis liegt auf Ø crush
        if lobes == RIPPEN_SOLL and abs(d_max - crush) <= 0.4 and d_min < durch:
            return 'crush'
        return 'durchgang'
    return KIND_FREI


@dataclass(repr=False)
class ScrewChainResult(Result):
    links: list = field(default_factory=list)
    biting: list = field(default_factory=list)
    engagement_mm: float = 0.0
    min_wall_mm: float = float('inf')
    required_engagement_mm: float = 0.0
    hole_source: str = 'tabelle'
    own_bodies: list = field(default_factory=list)
    material_on_axis: list = field(default_factory=list)
    screw_id: str = ''
    reasons: list = field(default_factory=list)
    passed: bool = True
    primitive: str = 'screw_chain'
    _fields: tuple = ('screw_id', 'biting', 'engagement_mm', 'required_engagement_mm',
                      'min_wall_mm', 'hole_source', 'links', 'own_bodies',
                      'material_on_axis', 'reasons')

    def link(self, key_teil: str) -> dict:
        hits = [l for l in self.links if key_teil.lower() in l['key'].lower()]
        if len(hits) != 1:
            raise ValueError(f'{key_teil!r} trifft {len(hits)} Glieder: {[l["key"] for l in self.links]}')
        return hits[0]

    def summary(self) -> str:
        kette = ' -> '.join(f"{l['key'].split('_')[0]}:{l['kind']}@{l['hole_d_mm']:.2f}" for l in self.links)
        return (f'screw_chain({self.screw_id}: {kette} | beisst={self.biting} '
                f'einschraubtiefe={self.engagement_mm:.2f} restwand={self.min_wall_mm:.2f})')


def screw_chain(screw, parts, at=None, *, frame=None, step_mm=0.25, directions=72, r_max_mm=None,
                engagement_factor=3.0, wall_margin_mm=0.5, overrun_mm=2.0) -> ScrewChainResult:
    """Kette entlang der Schraubenachse messen.

    `screw` ist ein `Screw` aus `schrauben.yaml`, `parts` eine Körpermenge (`Parts`,
    Liste von `Body` oder `Scene`). `at` verschiebt die **Körper** (bewegte Teile), nicht
    die Achse: die Schraubenlage in der YAML gilt in der Ruhelage der Maschine.
    `frame` löst `screw.frame` auf (ein `Frame` oder eine `Machine`); ohne Angabe kommt
    es aus `at` bzw. `parts`, wenn das eine `Scene`/`State` ist.
    """
    if getattr(screw, 'nicht_gebaut', False):
        # Die Schraube steht in der Pflegedatei, ihr Gegenstück ist noch nicht gebaut.
        # Eine Kette durch nicht vorhandenes Material hat kein Urteil.
        from ..results import NICHT_GEBAUT_MELDUNG, ohne_urteil
        return ohne_urteil('screw_chain', f'{screw.id}: {NICHT_GEBAUT_MELDUNG}')
    bodies = as_bodies(parts, at)
    nominal = screw.nominal_mm
    laenge = screw.laenge_mm
    tab, quelle = lochtabelle(nominal)
    r_max = float(r_max_mm) if r_max_mm is not None else 4.0 * nominal
    origin, u = screw.axis_points(resolve_frame(screw, frame, at, parts))
    _, e1, e2 = _axis.basis(u)
    dirs = _axis.ring(e1, e2, directions)

    eigene = _axis.self_bodies(bodies, origin, u, dirs, nominal, laenge)
    # über die Schraubenlänge hinaus abtasten, damit `exit_mm` die echte Materiallänge
    # trifft; Material auf der Achse ist aber nur bis zur Schraubenspitze ein Fehler.
    # Mindestens bis Spitze + geforderter Eingriff, sonst würde das Abtastfenster die
    # Frage „gibt das Teil überhaupt 3 x d her?" selbst beantworten.
    ueberlauf = max(float(overrun_mm), engagement_factor * nominal)
    depths = np.arange(0.0, laenge + ueberlauf + 1e-9, step_mm)

    links = []
    material = []
    for b in bodies:
        if b.key in eigene:
            continue
        slices = _axis.scan(b.mesh, origin, u, dirs, depths, r_max)
        aktiv = [i for i, s in enumerate(slices) if s.enclosed or s.material]
        if not aktiv:
            continue
        i0, i1 = aktiv[0], aktiv[-1]
        if any(slices[i].material for i in aktiv if depths[i] <= laenge):
            material.append(b.key)
            continue
        aktiv = [i for i in aktiv if not slices[i].material]
        if not aktiv:
            continue
        i0, i1 = aktiv[0], aktiv[-1]
        entry = depths[i0] if i0 == 0 else _axis.refine(b.mesh, origin, u, dirs, r_max,
                                                        depths[i0], depths[i0 - 1])
        exit_ = (depths[i1] if i1 == len(depths) - 1
                 else _axis.refine(b.mesh, origin, u, dirs, r_max, depths[i1], depths[i1 + 1]))
        if depths[i0] >= laenge:
            continue                      # liegt vollständig hinter der Schraubenspitze
        eng_slices = [slices[i] for i in aktiv if depths[i] <= laenge]
        tight = min(eng_slices, key=lambda s: s.d_min)
        kind = _kind(tight.d_min, tight.d_max, tight.lobes(), tab)
        links.append({'key': b.key, 'entry_mm': float(entry), 'exit_mm': float(exit_),
                      'hole_d_mm': round(float(tight.d_min), 4),
                      'hole_d_max_mm': round(float(tight.d_max), 4),
                      'ribs': int(tight.lobes()), 'kind': kind,
                      'nominal_d_mm': tab.get(kind)})
    links.sort(key=lambda l: l['entry_mm'])

    biting = [l['key'] for l in links if l['kind'] in ('pilot', 'crush')]
    gruende = []
    engagement = 0.0
    required = 0.0
    min_wall = float('inf')
    if len(biting) == 1 and links and links[-1]['key'] == biting[0]:
        last = links[-1]
        engagement = max(0.0, min(last['exit_mm'], laenge) - last['entry_mm'])
        verfuegbar = last['exit_mm'] - last['entry_mm']
        required = min(engagement_factor * nominal, verfuegbar)
        lo = last['entry_mm'] + wall_margin_mm
        hi = min(last['exit_mm'], laenge) - wall_margin_mm
        if hi > lo:
            body = next(b for b in bodies if b.key == last['key'])
            tiefen = np.arange(lo, hi + 1e-9, max(step_mm, 0.25))
            min_wall = _axis.wall(body.mesh, origin, u, dirs, tiefen, r_max=6.0 * nominal)
        if engagement + 1e-6 < required:
            gruende.append(f'Einschraubtiefe {engagement:.2f} mm < {required:.2f} mm '
                           f'({engagement_factor:g} x M{nominal:g}, verfügbar {verfuegbar:.2f} mm)')
    elif not biting:
        gruende.append('kein beißendes Glied')
    else:
        gruende.append(f'{len(biting)} beißende Glieder: {biting}')
    if links and biting and links[-1]['key'] != biting[-1]:
        gruende.append(f'das beißende Glied ist nicht das letzte (letztes: {links[-1]["key"]})')
    vorher = [l for l in links[:-1]] if links else []
    falsch = [l['key'] for l in vorher if l['kind'] != 'durchgang']
    if falsch:
        gruende.append(f'Glieder vor dem letzten ohne Durchgangsloch: {falsch}')
    if material:
        gruende.append(f'Material auf der Achse (kein Loch): {material}')
    if screw.beisst:
        soll = str(screw.beisst).lower()
        if not (len(biting) == 1 and soll in biting[0].lower()):
            gruende.append(f'erwartet beißend {screw.beisst!r}, gemessen {biting}')

    r = ScrewChainResult(links=links, biting=biting, engagement_mm=float(engagement),
                         min_wall_mm=float(min_wall), required_engagement_mm=float(required),
                         hole_source=quelle, own_bodies=sorted(eigene), material_on_axis=material,
                         screw_id=screw.id, reasons=gruende, passed=not gruende and bool(links))
    if not links:
        r.nichts_gemessen = True
        r.leer_grund = 'kein Körper auf der Schraubenachse'
    r._publish()
    return r


def resolve_frame(screw, frame=None, *quellen):
    """Bezugssystem der Schraube auflösen: `frame` (Frame/Machine), sonst die Machine
    aus einer übergebenen Scene/State, sonst `world` = Identität."""
    from ..frame import Frame
    if frame is not None:
        return frame
    for q in quellen:
        m = getattr(q, 'machine', None)
        if m is not None:
            return m
    if str(screw.frame).lower() == 'world':
        return Frame.identity()
    raise ValueError(f'Schraube {screw.id!r}: Frame {screw.frame!r} nicht auflösbar -- '
                     f'`frame=` (Frame oder Machine) übergeben oder `at`/`parts` als Scene.')
