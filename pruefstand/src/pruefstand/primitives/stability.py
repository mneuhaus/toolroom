"""stability(): Stabilitätsindex eines Lastabschnitts aus dem wirksamen Querschnitt.

Warnung, kein Fehler: ein Fehlschlag blockiert das Slicen nicht, der Test wird mit
`@pytest.mark.warnung` geführt. `level` trägt die Abstufung ok / warnung / fehler.

Rechenweg
---------
1. Querschnitt an der Schnittebene (roh, `area_mm2`).
2. **Wirksamer** Querschnitt statt Vollmaterial: die Wandlinien tragen voll, der Kern
   nur mit seinem Füllgrad::

       kern      = Querschnitt, um (waende × duese) nach innen versetzt
       effective = (Querschnitt − kern) + infill × kern
3. × cos²θ, θ = Winkel zwischen Lastrichtung und Schichtebene (θ = 0: die Last liegt
   in der Schichtebene, bester Fall; θ = 90°: die Last zieht senkrecht an der
   Schichtfuge, schlechtester Fall).
4. Ab-/Zuschläge für eine Kerbe am Fuß (`notch`) und eine durchgehende Schichtfuge im
   Querschnitt (`seam`).
5. Normiert auf den Anker.

Eichung — Stand ehrlich
-----------------------
Anker ist ein **Ø10 runder Stab, senkrecht gedruckt, mit Kerbe am Fuß und
Schichtfuge im Schnitt** — also genau der Probestab S1. Der bekommt per Definition
Index **1,0** und gilt als K.o.-Fall.

**Die Schwellen sind NICHT geeicht.** Die vier Probestäbe (S1–S4) sind konstruiert
und gesliced, aber zum Zeitpunkt dieser Implementierung **weder gedruckt noch
gebrochen**. Die Werte in `KALIBRIERUNG` — Schwellen und die Faktoren für Kerbe und
Schichtfuge — sind Annahmen aus dem Entwurf, keine Messwerte. Sie stehen bewusst an
**einer** Stelle und werden nach dem Bruchversuch nachgezogen; der Anker rechnet sich
aus denselben Konstanten, S1 bleibt also auch danach exakt 1,0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..printing import STANDARD_PROFIL, Profil, pose_matrix
from ..region import Region
from ..results import Result

#: Alle Stellschrauben des Index an einer Stelle. UNGEEICHT — s. Modul-Docstring.
KALIBRIERUNG = {
    'anker_durchmesser_mm': 10.0,   # Ø10 runder Stab
    'kerbe_faktor': 0.8,            # Abschlag bei Kerbe am Fuß
    'fuge_faktor': 0.7,             # Abschlag bei durchgehender Schichtfuge im Schnitt
    'schwelle_fehler': 1.5,         # darunter: fehler
    'schwelle_warnung': 4.0,        # darunter: warnung, darüber: ok
    'geeicht': False,               # True erst nach dem Bruchversuch der Probestäbe
}
#: Toleranz, ab der die Schnittebene als parallel zur Schichtebene gilt.
FUGE_TOLERANZ_DEG = 5.0
#: Stufe (mm) für die Sondierungen ober-/unterhalb der Schnittebene.
SONDE_MM = (0.2, 0.5, 1.0, 2.0)


@dataclass(repr=False)
class StabilityResult(Result):
    """Messwerte eines Lastabschnitts. `level` ∈ ok / warnung / fehler."""

    index: float = 0.0
    area_mm2: float = 0.0
    effective_mm2: float = 0.0
    theta_deg: float = 0.0
    cos2: float = 1.0
    notch: bool = False
    seam: bool = False
    level: str = 'fehler'
    anker_mm2: float = 0.0
    profil: dict = field(default_factory=dict)
    details: dict = field(default_factory=dict)
    geeicht: bool = False
    passed: bool = False
    primitive: str = 'stability'
    _fields: tuple = ('index', 'area_mm2', 'effective_mm2', 'theta_deg', 'cos2',
                      'notch', 'seam', 'level', 'anker_mm2', 'geeicht', 'profil', 'details')


# ------------------------------------------------------------- Bausteine ----
def wirksamer_querschnitt(poly, profil: Profil) -> float:
    """Wandlinien × Düsenbreite tragen voll, der Kern nur mit seinem Füllgrad."""
    if poly is None or poly.is_empty:
        return 0.0
    kern = poly.buffer(-profil.wandstaerke_mm, join_style='mitre', mitre_limit=8.0)
    kern_mm2 = max(0.0, float(kern.area))
    wand_mm2 = max(0.0, float(poly.area) - kern_mm2)
    return wand_mm2 + profil.infill * kern_mm2


def anker_mm2(profil: Profil = None) -> float:
    """Wirksamer Querschnitt des Ankers (Ø10 Kreis) mit dem gegebenen Profil."""
    from shapely.geometry import Point
    profil = profil or STANDARD_PROFIL
    r = 0.5 * float(KALIBRIERUNG['anker_durchmesser_mm'])
    return wirksamer_querschnitt(Point(0.0, 0.0).buffer(r, quad_segs=512), profil)


def _anker_nenner(profil: Profil) -> float:
    """Nenner des Index: der Anker mit seinen eigenen Abschlägen (Kerbe + Fuge, θ=0)."""
    return anker_mm2(profil) * float(KALIBRIERUNG['kerbe_faktor']) * float(KALIBRIERUNG['fuge_faktor'])


def _ebene(section, pose_m):
    """(punkt, normale, clip_region) aus der Abschnittsangabe, in Druckpose-Koordinaten."""
    clip = None
    frame = 'local'
    if isinstance(section, Region):
        if section.kind != 'box':
            raise TypeError('stability(): Region muss ein Quader sein (Region.box)')
        size = section.hi - section.lo
        achse = int(np.argmin(size))
        n_local = np.zeros(3)
        n_local[achse] = 1.0
        punkt = section.frame.to_world(0.5 * (section.lo + section.hi))
        normale = section.frame.direction_to_world(n_local)
        clip = section
    elif hasattr(section, 'als_ebene'):
        punkt, normale = section.als_ebene()
        frame = getattr(section, 'frame', 'local')
    elif isinstance(section, dict):
        p = section.get('punkt', section.get('point'))
        n = section.get('normale', section.get('normal'))
        if p is None or n is None:
            raise TypeError("stability(): Schnittebene braucht 'punkt' und 'normale'")
        punkt, normale, frame = p, n, section.get('frame', 'local')
    else:
        try:
            punkt, normale = section
        except Exception:
            raise TypeError('stability(): section erwartet (punkt, normale), dict, '
                            'Lastabschnitt oder Region.box') from None
    punkt = np.asarray(punkt, dtype=float).reshape(3)
    normale = np.asarray(normale, dtype=float).reshape(3)
    if np.linalg.norm(normale) < 1e-12:
        raise ValueError('stability(): Normale ist ein Nullvektor')
    normale = normale / np.linalg.norm(normale)
    if str(frame) == 'local':
        punkt = (pose_m[:3, :3] @ punkt) + pose_m[:3, 3]
        normale = pose_m[:3, :3] @ normale
        normale = normale / np.linalg.norm(normale)
    return punkt, normale, clip


def _clip_poly(poly, clip: Region, punkt, normale, pose_m):
    """Querschnitt auf eine Quader-Region begrenzen (grob über die Bounding-Box)."""
    if clip is None or poly is None or poly.is_empty:
        return poly
    # Der Quader wird über seine acht Ecken in die 2D-Schnittebene projiziert.
    from shapely.geometry import MultiPoint
    ecken = np.array([[x, y, z] for x in (clip.lo[0], clip.hi[0])
                      for y in (clip.lo[1], clip.hi[1])
                      for z in (clip.lo[2], clip.hi[2])])
    welt = clip.frame.to_world(ecken)
    u, v = _basis(normale)
    rel = welt - punkt
    zweid = np.column_stack([rel @ u, rel @ v])
    return poly.intersection(MultiPoint([tuple(p) for p in zweid]).convex_hull)


def _basis(normale):
    hilfs = np.array([1.0, 0.0, 0.0]) if abs(normale[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(normale, hilfs)
    u /= np.linalg.norm(u)
    v = np.cross(normale, u)
    return u, v


def _schnitte(mesh, punkt, normale, hoehen):
    """Querschnitts-Polygone bei den Höhen `hoehen` entlang der Normalen."""
    from shapely.geometry import MultiPolygon
    from shapely.ops import unary_union
    sec = mesh.section_multiplane(plane_origin=[float(x) for x in punkt],
                                 plane_normal=[float(x) for x in normale],
                                 heights=list(hoehen))
    out = []
    for s in sec:
        if s is None:
            out.append(MultiPolygon())
            continue
        ps = [p for p in s.polygons_full if p is not None and p.area > 0]
        out.append(unary_union(ps) if ps else MultiPolygon())
    return out


def _mesh_of(body):
    import trimesh
    if isinstance(body, trimesh.Trimesh):
        return body.copy()
    m = getattr(body, 'mesh', None)
    if m is None:
        raise TypeError(f'Body oder trimesh.Trimesh erwartet, bekommen {type(body).__name__}')
    m = m.copy()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    m.merge_vertices()
    return m


# ------------------------------------------------------------- Primitive ----
def stability(body, section, direction, profile=None, pose=None, frame='local') -> StabilityResult:
    """Stabilitätsindex eines Lastabschnitts.

    body      `Body` (oder trimesh.Trimesh), wie modelliert
    section   Schnittebene: `(punkt, normale)`, dict mit punkt/normale/frame,
              `printing.Lastabschnitt` oder `Region.box` (dann ist die Ebene die
              Mittelebene senkrecht zur dünnsten Quaderachse, und der Quader
              begrenzt den Querschnitt)
    direction Lastrichtung. θ ist der Winkel zwischen ihr und der Schichtebene.
    profile   `Profil`; Standard 3 Wände × 0,42 mm, 25 % Infill, 0,2 mm Schicht
    pose      Druckpose (s. `printing.pose_matrix`); bestimmt, wo die Schichtebenen
              liegen. Ohne Pose ist die Schichtebene die XY-Ebene des Modells.
    frame     Bezug von `direction` (und der Ebene, falls dort nicht gesetzt):
              'local' = wie modelliert (wird mit der Pose gedreht), 'print' = bereits
              in Druckkoordinaten.

    Die Schwellen sind ungeeicht, s. Modul-Docstring.
    """
    profil = profile or STANDARD_PROFIL
    if not isinstance(profil, Profil):
        profil = Profil.from_dict(profil)
    pose_m = pose_matrix(pose)

    mesh = _mesh_of(body)
    mesh.apply_transform(pose_m)

    punkt, normale, clip = _ebene(section, pose_m)

    d = np.asarray(direction, dtype=float).reshape(3)
    if np.linalg.norm(d) < 1e-12:
        raise ValueError('stability(): Lastrichtung ist ein Nullvektor')
    if str(frame) == 'local':
        d = pose_m[:3, :3] @ d
    d = d / np.linalg.norm(d)

    # θ: Winkel zwischen Lastrichtung und Schichtebene (die Schichten liegen in der
    # XY-Ebene der Druckpose, ihre Normale ist +Z).
    theta_deg = float(math.degrees(math.asin(min(1.0, abs(float(d[2]))))))
    cos2 = float(math.cos(math.radians(theta_deg)) ** 2)

    eps = min(SONDE_MM)
    hoehen = [-h for h in reversed(SONDE_MM)] + [-eps / 2, eps / 2] + list(SONDE_MM)
    polys = _schnitte(mesh, punkt, normale, hoehen)
    idx = {round(h, 4): p for h, p in zip(hoehen, polys)}
    unter = _clip_poly(idx[round(-eps / 2, 4)], clip, punkt, normale, pose_m)
    ueber = _clip_poly(idx[round(eps / 2, 4)], clip, punkt, normale, pose_m)
    a_unter, a_ueber = float(unter.area), float(ueber.area)

    # Am Absatz ist der Querschnitt in der Ebene selbst mehrdeutig; maßgeblich ist die
    # dünne Seite — das ist die, die bricht.
    if a_unter <= 0.0 and a_ueber <= 0.0:
        r = StabilityResult(theta_deg=theta_deg, cos2=cos2, passed=False, level='fehler',
                            anker_mm2=anker_mm2(profil), profil=profil.as_dict(),
                            geeicht=bool(KALIBRIERUNG['geeicht']))
        r.nichts_gemessen = True
        r.leer_grund = 'Schnittebene trifft den Körper nicht'
        r._publish()
        return r
    duenne_seite = 1.0 if (a_ueber <= a_unter or a_unter <= 0.0) else -1.0
    poly = ueber if duenne_seite > 0 else unter
    area_mm2 = float(poly.area)

    effective_mm2 = wirksamer_querschnitt(poly, profil)

    # -- Kerbe am Fuß: auf der dünnen Seite kein Auslauf, auf der dicken ein Absatz --
    def _a(h):
        p = _clip_poly(idx[round(h, 4)], clip, punkt, normale, pose_m)
        return float(p.area)

    a_duenn_fern = _a(duenne_seite * SONDE_MM[-1])
    a_dick_fern = _a(-duenne_seite * SONDE_MM[-1])
    absatz = a_dick_fern >= 1.5 * max(area_mm2, 1e-9)
    kein_auslauf = area_mm2 <= 1.05 * max(a_duenn_fern, 1e-9)
    notch = bool(absatz and kein_auslauf)

    # -- Schichtfuge: Schnittebene parallel zur Schichtebene und lokal dünnste Stelle --
    parallel = abs(float(normale[2])) >= math.cos(math.radians(FUGE_TOLERANZ_DEG))
    umgebung = min([_a(h) for h in hoehen if _a(h) > 0.0] or [area_mm2])
    duennste = area_mm2 <= 1.05 * max(umgebung, 1e-9)
    seam = bool(parallel and duennste)

    faktor = 1.0
    if notch:
        faktor *= float(KALIBRIERUNG['kerbe_faktor'])
    if seam:
        faktor *= float(KALIBRIERUNG['fuge_faktor'])

    nenner = _anker_nenner(profil)
    index = float(effective_mm2 * cos2 * faktor / nenner) if nenner > 0 else 0.0

    if index < float(KALIBRIERUNG['schwelle_fehler']):
        level = 'fehler'
    elif index < float(KALIBRIERUNG['schwelle_warnung']):
        level = 'warnung'
    else:
        level = 'ok'

    r = StabilityResult(
        index=index, area_mm2=area_mm2, effective_mm2=effective_mm2,
        theta_deg=theta_deg, cos2=cos2, notch=notch, seam=seam, level=level,
        anker_mm2=anker_mm2(profil), profil=profil.as_dict(),
        geeicht=bool(KALIBRIERUNG['geeicht']),
        details={'faktor': round(faktor, 4), 'nenner_mm2': round(nenner, 4),
                 'duenne_seite': '+n' if duenne_seite > 0 else '-n',
                 'a_duenn_fern_mm2': round(a_duenn_fern, 3),
                 'a_dick_fern_mm2': round(a_dick_fern, 3),
                 'normale': [round(float(x), 5) for x in normale],
                 'richtung': [round(float(x), 5) for x in d]},
        passed=(level == 'ok'))
    r._publish()
    return r
