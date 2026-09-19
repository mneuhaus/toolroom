"""print_pose(): Bettauflage, Überhang, Brücken und Stützenbedarf einer Druckpose.

Warnung, kein Fehler: ein Fehlschlag blockiert das Slicen nicht, der Test wird mit
`@pytest.mark.warnung` geführt.

**Warum `needs_support` nicht am Flächenwinkel hängt.** Der Normalenwinkel einer
Fläche ist ein reines Geometriemaß. Ein liegender **runder** Stab hat über seinem
unteren Bogen rechnerisch Flächen steiler als 45° von der Senkrechten und braucht
trotzdem keine Stützen: von Lage zu Lage springt die Kontur nur um einen Bruchteil
der Düsenbreite nach außen, jede Lage liegt also noch auf der darunter auf. Deshalb
misst dieses Primitiv den **Rücksprung je Schicht** (`max_step_mm`): der Körper wird
in Lagen der Höhe `layer_mm` geschnitten, und für jede Lage wird der Teil der Fläche
bestimmt, der über der Lage darunter *übersteht*. Der größte laterale Überstand eines
solchen Stücks ist der Rücksprung. Ist er größer als eine Düsenbreite, hängt die
Lage in der Luft und braucht Stützen.

Stücke, die auf **mehreren Seiten** aufliegen — ein sich schließendes Loch (ringsum
umschlossen) oder ein Schlitz zwischen zwei Wänden (zwei getrennte Auflager) — sind
Brücken und keine Kragarme:
sie werden getrennt als `bridges` mit Spannweite gemeldet und gehen nicht in
`max_step_mm` ein, weil der Drucker sie freitragend zieht.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..printing import STANDARD_PROFIL, pose_matrix
from ..results import Result


@dataclass(repr=False)
class PrintPoseResult(Result):
    """Messwerte einer Druckpose. `level` ist immer 'ok' oder 'warnung'."""

    contact_mm2: float = 0.0
    z_min_mm: float = 0.0
    bbox_mm: object = None
    fits_bed: bool = False
    overhang_mm2: float = 0.0
    max_overhang_deg: float = 0.0
    overhang_deg: float = 50.0
    max_step_mm: float = 0.0
    step_z_mm: float | None = None
    selbsttragend_mm: float = 0.42
    layer_mm: float = 0.2
    layers: int = 0
    bridges: list = field(default_factory=list)
    max_bridge_mm: float = 0.0
    needs_support: bool = False
    passed: bool = False
    level: str = 'warnung'
    primitive: str = 'print_pose'
    _fields: tuple = ('contact_mm2', 'z_min_mm', 'bbox_mm', 'fits_bed', 'overhang_mm2',
                      'max_overhang_deg', 'overhang_deg', 'max_step_mm', 'step_z_mm',
                      'selbsttragend_mm', 'layer_mm', 'layers', 'max_bridge_mm',
                      'needs_support', 'level', 'bridges')

#: Rücksprung je Schicht, den eine Lage noch selbst trägt, als Vielfaches der
#: Düsenbreite. 1,0 = eine ganze Extrusionsbreite Überstand. Ungeeicht, aber durch
#: die Probestäbe gestützt (S4, Ø10 liegend: gemessener Rücksprung deutlich darunter).
SELBSTTRAGEND_X_DUESE = 1.0
#: Stücke kleiner als das sind Tessellierungsrauschen (in Vielfachen von duese²).
MIN_STUECK_X_DUESE2 = 1.0


def _mesh_of(body):
    import trimesh
    if isinstance(body, trimesh.Trimesh):
        return body.copy()
    m = getattr(body, 'mesh', None)
    if m is None:
        raise TypeError(f'Body oder trimesh.Trimesh erwartet, bekommen {type(body).__name__}')
    return m.copy()


def _clean(m):
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    m.merge_vertices()
    return m


def _polygons(mesh, z_min, z_max, layer):
    """Querschnitt je Lage: Liste (z_mitte, shapely-Geometrie) von unten nach oben."""
    from shapely.geometry import MultiPolygon
    from shapely.ops import unary_union

    n = max(1, int(np.floor((z_max - z_min) / layer)))
    heights = [z_min + (k + 0.5) * layer for k in range(n)]
    sec = mesh.section_multiplane(plane_origin=[0.0, 0.0, 0.0], plane_normal=[0.0, 0.0, 1.0],
                                  heights=heights)
    out = []
    for z, s in zip(heights, sec):
        if s is None:
            out.append((z, MultiPolygon()))
            continue
        # Alle Schnitte teilen dieselbe Ebenen-Normale, also dieselbe 2D-Basis:
        # die Polygone sind direkt miteinander verrechenbar.
        polys = [p for p in s.polygons_full if p is not None and p.area > 0]
        out.append((z, unary_union(polys) if polys else MultiPolygon()))
    return out


def _parts(geom):
    if geom.is_empty:
        return []
    return list(getattr(geom, 'geoms', [geom]))


def _gefuellt(geom):
    """Dieselbe Fläche ohne Löcher — für den Test „ringsum umschlossen?"."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    ps = [Polygon(p.exterior) for p in _parts(geom) if not p.is_empty]
    return unary_union(ps) if ps else geom


def _inkreis_r(piece):
    """Radius des größten einbeschriebenen Kreises (Bisektion über Erosion)."""
    lo, hi = 0.0, float(max(piece.bounds[2] - piece.bounds[0], piece.bounds[3] - piece.bounds[1])) / 2 + 1e-6
    for _ in range(24):
        mid = 0.5 * (lo + hi)
        if piece.buffer(-mid).is_empty:
            hi = mid
        else:
            lo = mid
    return lo


def _auflager(piece, lower, eps=0.01):
    """Auf wie vielen getrennten Stellen der Lage darunter liegt das Stück auf?

    Zwei und mehr = Brücke (der Drucker zieht sie freitragend von Auflager zu
    Auflager), eines = Kragarm.
    """
    if lower.is_empty:
        return 0
    beruehrung = piece.buffer(eps).intersection(lower)
    if beruehrung.is_empty:
        return 0
    return len([g for g in _parts(beruehrung) if g.area > eps * eps])


def _reichweite(piece, lower):
    """Größter lateraler Überstand eines Kragstücks über die Lage darunter."""
    from shapely.geometry import Point
    best = 0.0
    for p in _parts(piece):
        rings = [p.exterior] + list(p.interiors)
        for r in rings:
            for x, y in np.asarray(r.coords):
                d = Point(float(x), float(y)).distance(lower) if not lower.is_empty else float('inf')
                if d > best:
                    best = d
    return float(best)


def print_pose(body, pose=None, bed=(250.0, 250.0), overhang_deg=50.0, layer_mm=0.2,
               duese_mm=None, profil=None, bed_margin_mm=0.0) -> PrintPoseResult:
    """Druckpose eines Körpers bewerten.

    body        `Body` (oder trimesh.Trimesh) wie modelliert
    pose        Lage beim Drucken (None = wie modelliert), s. `printing.pose_matrix`
    bed         Bettmaß (x, y) in mm
    overhang_deg Grenzwinkel von der Senkrechten für die gemeldete Überhangfläche
    layer_mm    Schichthöhe für die Rücksprung-Analyse
    duese_mm    Extrusionsbreite; Standard aus `profil` bzw. 0,42
    profil      `Profil`; setzt layer_mm/duese_mm, wenn diese nicht angegeben sind
    """
    from shapely.geometry import MultiPolygon

    prof = profil or STANDARD_PROFIL
    if layer_mm is None:
        layer_mm = prof.schicht
    if duese_mm is None:
        duese_mm = prof.duese
    layer_mm = float(layer_mm)
    duese_mm = float(duese_mm)
    if layer_mm <= 0 or duese_mm <= 0:
        raise ValueError('layer_mm und duese_mm müssen > 0 sein')

    mesh = _clean(_mesh_of(body))
    mesh.apply_transform(pose_matrix(pose))

    if len(mesh.faces) == 0:
        r = PrintPoseResult(passed=False)
        r.nichts_gemessen = True
        r.leer_grund = 'Körper hat keine Dreiecke'
        r._publish()
        return r

    lo, hi = mesh.bounds
    bbox = (hi - lo)
    z_min = float(lo[2])
    z_max = float(hi[2])
    fits_bed = bool(bbox[0] <= float(bed[0]) - bed_margin_mm and bbox[1] <= float(bed[1]) - bed_margin_mm)

    # -- Bettauflage und Überhangflächen --------------------------------
    n = mesh.face_normals
    area = mesh.area_faces
    ctr = mesh.triangles_center
    ab = max(0.05, layer_mm / 4.0)
    down = n[:, 2] < -1e-6
    on_bed = down & (ctr[:, 2] < z_min + ab)
    contact_mm2 = float(area[on_bed].sum())

    polys = _polygons(mesh, z_min, z_max, layer_mm)

    # Eine abwärts gerichtete Fläche ist nur dann ein Überhang, wenn unter ihr Luft
    # ist. Deckungsgleiche Boolean-Splitter (cad-khana-quirks) sitzen mitten im
    # Vollmaterial und werden hier korrekt aussortiert — ohne Sonderfall fürs Teil.
    from shapely.geometry import Point
    kandidat = np.where(down & ~on_bed)[0]
    frei = []
    for i in kandidat:
        x, y, z = ctr[i]
        k = int(np.floor((z - z_min) / layer_mm)) - 1
        if k < 0:
            frei.append(i)
            continue
        k = min(k, len(polys) - 1)
        unten = polys[k][1]
        if unten.is_empty or not unten.contains(Point(float(x), float(y))):
            frei.append(i)
    frei = np.asarray(frei, dtype=int)

    if frei.size:
        nz = np.clip(-n[frei, 2], -1.0, 1.0)
        # 0° = senkrechte Wand, 90° = waagerechte Decke
        von_vertikal = np.degrees(np.arcsin(nz))
        max_overhang_deg = float(von_vertikal.max())
        overhang_mm2 = float(area[frei][von_vertikal > float(overhang_deg)].sum())
    else:
        max_overhang_deg = 0.0
        overhang_mm2 = 0.0

    # -- Rücksprung je Schicht ------------------------------------------
    min_area = MIN_STUECK_X_DUESE2 * duese_mm * duese_mm
    grenze = SELBSTTRAGEND_X_DUESE * duese_mm
    max_step_mm = 0.0
    step_z_mm = None
    bridges = []
    leer = MultiPolygon()
    for k in range(1, len(polys)):
        z, oben = polys[k]
        unten = polys[k - 1][1]
        if oben.is_empty:
            continue
        diff = oben.difference(unten) if not unten.is_empty else oben
        if diff.is_empty:
            continue
        gefuellt = _gefuellt(unten) if not unten.is_empty else leer
        for piece in _parts(diff):
            if piece.area < min_area:
                continue
            umschlossen = (not gefuellt.is_empty
                           and piece.difference(gefuellt).area <= 0.01 * piece.area)
            auflager = _auflager(piece, unten)
            if umschlossen or auflager >= 2:
                span = 2.0 * _inkreis_r(piece)
                if span > grenze:
                    bridges.append({'z_mm': round(float(z), 3),
                                    'laenge_mm': round(float(span), 3),
                                    'flaeche_mm2': round(float(piece.area), 3)})
                continue
            reach = _reichweite(piece, unten)
            if reach > max_step_mm:
                max_step_mm = reach
                step_z_mm = float(z)

    needs_support = bool(max_step_mm > grenze)
    max_bridge_mm = float(max(b['laenge_mm'] for b in bridges)) if bridges else 0.0
    passed = bool(fits_bed and not needs_support and contact_mm2 > 0.0)

    r = PrintPoseResult(
        contact_mm2=contact_mm2, z_min_mm=z_min, bbox_mm=bbox, fits_bed=fits_bed,
        overhang_mm2=overhang_mm2, max_overhang_deg=max_overhang_deg,
        overhang_deg=float(overhang_deg),
        max_step_mm=float(max_step_mm), step_z_mm=step_z_mm,
        selbsttragend_mm=float(grenze), layer_mm=layer_mm, layers=len(polys),
        bridges=bridges, max_bridge_mm=max_bridge_mm,
        needs_support=needs_support, passed=passed,
        level='ok' if passed else 'warnung')
    r._publish()
    return r
