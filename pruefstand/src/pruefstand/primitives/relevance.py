"""relevance(): Material ohne Funktion finden.

Material gilt als **funktional**, wenn eines von drei Dingen zutrifft:

1. **Ankernähe** — es liegt innerhalb `r_anker` um einen Anker.
2. **Lastpfad, konvex** — es liegt in der um `r_anker` aufgeweiteten konvexen Hülle
   aller Anker, also eingeschlossen zwischen ihnen.
3. **Lastpfad, geodätisch** — es liegt auf einer (fast) direkten Materialverbindung
   zwischen zwei verschiedenen Ankerquellen: geodätischer Umweg höchstens `2·r_anker`.

Anker sind Kontaktstellen zu anderen Körpern über **alle** Posen, die die Maschine
kennt, Bohrungen und die in `spec/relevanz.yaml` erklärten Bereiche. Jede Quelle
(je Kontaktpartner, je Bohrung, je erklärter Bereich) zählt einzeln — geometrisch
zusammenhängende Kontaktflächen sind trotzdem verschiedene Anker, sonst gäbe es auf
einem Teil, dessen Auflagen alle zusammenhängen, überhaupt keinen Lastpfad.

Der Rest ist fraglich. Bevor er gemeldet wird, wird er morphologisch **geöffnet**:
was nirgends dicker als zwei Voxel ist, fällt weg. Ohne das meldet jede dünne Wand
ihre vom Anker abgewandte Deckschicht — der teuerste Fehlalarm, den es hier gibt.
Alle drei Regeln zeigen in dieselbe konservative Richtung: im Zweifel funktional.

Das Primitiv **warnt**, es blockiert nicht (`pytest.mark.warnung`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..results import Result
from . import _relevance as _r
from ._common import one_body

__all__ = ['relevance', 'RelevanceResult']


@dataclass(repr=False)
class RelevanceResult(Result):
    funktional_mm3: float = 0.0
    fraglich_mm3: float = 0.0
    anteil: float = 0.0
    befunde: list = field(default_factory=list)
    anker: dict = field(default_factory=dict)
    aufloesung_mm: float = 0.0
    level: str = 'ok'
    passed: bool = True
    primitive: str = 'relevance'
    _fields: tuple = ('funktional_mm3', 'fraglich_mm3', 'anteil', 'level',
                      'aufloesung_mm', 'anker', 'befunde')


def _quellen_kappen(quellen, grenze):
    """Zu viele Ankerquellen auf `grenze` eindampfen (Laufzeit der Geodäten)."""
    if len(quellen) <= grenze:
        return quellen
    nach_groesse = sorted(quellen, key=lambda q: -int(q[1].sum()))
    behalten = nach_groesse[:grenze - 1]
    rest = np.zeros_like(nach_groesse[0][1])
    for _, m in nach_groesse[grenze - 1:]:
        rest |= m
    return behalten + [('rest', rest)]


def relevance(body, context, at=None, r_anker=3.0, kontakt_mm=1.0, min_volumen_mm3=50.0,
              aufloesung_mm=1.0, relevanz=None, erklaert=None) -> RelevanceResult:
    """Funktionsloses Material eines Körpers suchen.

    `context` ist die Maschine (alle bekannten Posen werden geprüft), eine Szene oder
    eine Liste von Körpern. `relevanz` ist eine `TeilRelevanz` bzw. `Relevanz`; ohne
    Angabe wird `spec/relevanz.yaml` des laufenden Projekts genommen, falls vorhanden.
    `erklaert` nimmt zusätzliche `Region`-Anker direkt entgegen.
    """
    from scipy import ndimage

    from ..relevanz import Relevanz, TeilRelevanz, find_relevanz

    teil = one_body(body, at)
    pitch = float(aufloesung_mm)
    if pitch <= 0:
        raise ValueError(f'aufloesung_mm muss positiv sein, bekommen {aufloesung_mm!r}')

    frames = context if hasattr(context, 'frame') else getattr(context, 'machine', None)
    if relevanz is None:
        relevanz = find_relevanz()
    if isinstance(relevanz, Relevanz):
        relevanz = relevanz.teil(teil.key)
    if relevanz is not None and not isinstance(relevanz, TeilRelevanz):
        raise TypeError(f'relevanz erwartet Relevanz oder TeilRelevanz, '
                        f'bekommen {type(relevanz).__name__}')

    grid = _r.voxelize(teil.mesh, pitch)
    material = grid.occ
    vox = grid.voxel_mm3

    # -- ausgeschlossene Bereiche ---------------------------------------
    raus = np.zeros(grid.shape, dtype=bool)
    if relevanz is not None:
        for e in relevanz.ausgeschlossen():
            raus |= grid.contains_mask(e.region(frames))
    material = material & ~raus
    if not material.any():
        r = RelevanceResult(aufloesung_mm=pitch, passed=False)
        r.nichts_gemessen = True
        r.leer_grund = 'kein Material im Voxelgitter'
        r._publish()
        return r

    # -- Ankerquellen -----------------------------------------------------
    rand = material & ~ndimage.binary_erosion(material,
                                              ndimage.generate_binary_structure(3, 1),
                                              border_value=0)
    rand_idx = np.argwhere(rand)
    rand_pts = grid.centers(rand_idx) if len(rand_idx) else np.zeros((0, 3))

    quellen: list[tuple[str, np.ndarray]] = []
    kontakt_bodies: dict[str, int] = {}
    kontakt_masken: dict[str, np.ndarray] = {}
    zustaende = _r.poses(context, at)
    for st in zustaende:
        for fremd in _r.scene_bodies(context, st, ausser={teil.key}):
            s, tr = _r.contact_anchors(grid, rand_idx, rand_pts, [fremd], float(kontakt_mm))
            if not s.any():
                continue
            vorher = kontakt_masken.get(fremd.key)
            kontakt_masken[fremd.key] = s if vorher is None else (vorher | s)
            kontakt_bodies[fremd.key] = max(kontakt_bodies.get(fremd.key, 0),
                                            int(tr.get(fremd.key, 0)))
    quellen += [(f'kontakt:{k}', m) for k, m in sorted(kontakt_masken.items())]

    bohrungen = _r.bores(teil.solid)
    n_bohr = 0
    for i, b in enumerate(bohrungen):
        s, _ = _r.bore_anchors(grid, material, [b])
        if s.any():
            quellen.append((f'bohrung:{i}', s))
            n_bohr += 1

    n_erk = 0
    regionen = [(f'erklaert:{i}', reg) for i, reg in enumerate(erklaert or [])]
    if relevanz is not None:
        regionen += [(f'erklaert:{e.name}', e.region(frames)) for e in relevanz.anker()]
    for name, reg in regionen:
        m = grid.contains_mask(reg) & material
        if m.any():
            quellen.append((name, m))
            n_erk += 1

    quellen = [(n, m & material) for n, m in quellen]
    quellen = [(n, m) for n, m in quellen if m.any()]
    anker = {'kontakt': len(kontakt_bodies), 'bohrung': n_bohr, 'erklaert': n_erk,
             'kontakt_koerper': sorted(kontakt_bodies), 'posen': len(zustaende),
             'quellen': len(quellen)}
    if len(quellen) < 2:
        # Mit weniger als zwei Quellen gibt es keinen Lastpfad, und alles jenseits von
        # `r_anker` fiele auf einen Schlag als fraglich an — das wäre kein Befund,
        # sondern ein Fehlalarm über das halbe Teil.
        r = RelevanceResult(anker=anker, aufloesung_mm=pitch, passed=False)
        r.nichts_gemessen = True
        r.leer_grund = (f'{len(quellen)} Ankerquelle(n) gefunden, mindestens zwei nötig — '
                        'ohne zwei Anker ist jede Aussage über Funktion wertlos')
        r._publish()
        return r
    quellen = _quellen_kappen(quellen, _r.MAX_QUELLEN)

    seeds = np.zeros(grid.shape, dtype=bool)
    for _, m in quellen:
        seeds |= m

    # -- Funktionsmenge ---------------------------------------------------
    dist = ndimage.distance_transform_edt(~seeds, sampling=pitch)
    funktional = material & (dist <= float(r_anker))
    huelle = _r.hull_mask(grid, material, grid.centers(np.argwhere(seeds)), float(r_anker))
    if huelle is not None:
        funktional |= huelle
    funktional |= _r.detour_mask(material, pitch, [m for _, m in quellen], 2.0 * float(r_anker))

    roh = material & ~funktional
    fraglich = _r.opening(roh) if roh.any() else roh

    # -- Befunde ----------------------------------------------------------
    befunde = []
    if fraglich.any():
        insel, n_insel = ndimage.label(fraglich, structure=np.ones((3, 3, 3), dtype=bool))
        groessen = np.bincount(insel.ravel(), minlength=n_insel + 1)
        for lab in range(1, n_insel + 1):
            volumen = int(groessen[lab]) * vox
            if volumen < float(min_volumen_mm3):
                continue
            idx = np.argwhere(insel == lab)
            pts = grid.centers(idx)
            befunde.append({
                'volumen_mm3': float(volumen),
                'schwerpunkt': pts.mean(axis=0),
                'bbox_mm': [pts.min(axis=0) - pitch / 2.0, pts.max(axis=0) + pitch / 2.0],
                'max_abstand_mm': float(dist[tuple(idx.T)].max()),
            })
    befunde.sort(key=lambda b: -b['volumen_mm3'])

    fraglich_vox = int(fraglich.sum())
    gesamt_vox = int(material.sum())
    r = RelevanceResult(
        funktional_mm3=(gesamt_vox - fraglich_vox) * vox,
        fraglich_mm3=fraglich_vox * vox,
        anteil=(fraglich_vox / gesamt_vox) if gesamt_vox else 0.0,
        befunde=befunde,
        anker=anker,
        aufloesung_mm=pitch,
        level='warnung' if befunde else 'ok',
        passed=not befunde,
    )
    r._publish()
    return r
