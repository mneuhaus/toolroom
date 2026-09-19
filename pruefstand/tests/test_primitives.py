import numpy as np
import pytest
from build123d import Box, Cylinder, Location

from pruefstand import Body, Frame, Region, coverage, gap, overlap, protrusion, results, same_as
from conftest import box


def test_gap_zwei_wuerfel(wuerfel_paar):
    a, b = wuerfel_paar
    r = gap(a, b)
    assert abs(r.min_mm - 0.5) < 1e-3, r
    assert r.pair == ('A', 'B') and not r.penetrating
    assert abs(r.per_body['B'] - 0.5) < 1e-3


def test_gap_liste_und_per_body():
    a = box('A', (10, 10, 10))
    b1 = box('B1', (10, 10, 10), (10.5, 0, 0))
    b2 = box('B2', (10, 10, 10), (0, 12.0, 0))
    r = gap(a, [b1, b2])
    assert abs(r.min_mm - 0.5) < 1e-3
    assert abs(r.per_body['B2'] - 2.0) < 1e-3


def test_gap_durchdringung_null():
    r = gap(box('A', (10, 10, 10)), box('B', (10, 10, 10), (5, 0, 0)))
    assert r.min_mm == 0.0 and r.penetrating
    assert r.penetration_auf == 'brep'


def test_buendiger_formschluss_ist_keine_durchdringung():
    """Zwei Quader Fläche an Fläche: Abstand 0,0 mm, aber kein Material im Material.

    Das war der Befund an T40 gegen T41 (`r7-analyse-bericht.md`, Werkzeuglücke 1):
    `gap` meldete `penetrating=True`, `overlap` daneben exakt 0,0 mm³. Der Netzkern
    liefert für koinzidente Flächen dieselbe Tiefe wie für echte Durchdringung --
    also entscheidet jetzt der exakte Schnitt.
    """
    r = gap(box('A', (10, 10, 10)), box('B', (10, 10, 10), (10, 0, 0)))
    assert r.min_mm == pytest.approx(0.0, abs=1e-9)
    assert not r.penetrating, r
    assert r.penetration_auf == 'brep'
    assert overlap(box('A', (10, 10, 10)), box('B', (10, 10, 10), (10, 0, 0))).volume_mm3 == 0.0


def test_fuenf_hundertstel_durchdringung_wird_gemeldet():
    """0,05 mm Überschneidung ist eine -- die Regel darf nicht alles wegerklären."""
    r = gap(box('A', (10, 10, 10)), box('B', (10, 10, 10), (9.95, 0, 0)))
    assert r.min_mm == 0.0 and r.penetrating
    assert r.penetration_auf == 'brep'


def test_durchdringung_ohne_brep_entscheidet_das_netz(tmp_path):
    """Netzkörper: kein exakter Schnitt möglich, also zählt die Eindringtiefe.

    Bündig -> keine Durchdringung (die Tiefe bleibt unter 0,01 mm), 0,05 mm -> eine.
    """
    from build123d import export_stl
    from pruefstand import load_mesh

    def netz(key, at):
        p = tmp_path / f'{key}.stl'
        export_stl(Box(10, 10, 10).locate(Location(tuple(float(x) for x in at))), str(p))
        return load_mesh(p, key=key)

    buendig = gap(netz('A', (0, 0, 0)), netz('B', (10, 0, 0)))
    assert buendig.min_mm == pytest.approx(0.0, abs=1e-9)
    assert not buendig.penetrating and buendig.penetration_auf == 'mesh'
    tief = gap(netz('A', (0, 0, 0)), netz('C', (9.95, 0, 0)))
    assert tief.penetrating and tief.penetration_auf == 'mesh'
    assert tief.durchdringung_mm == pytest.approx(0.05, abs=0.01)


def test_overlap_exakt_volumen():
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), (8, 0, 0))     # 2 mm Überdeckung -> 2*10*10
    r = overlap(a, b)
    assert r.exact and abs(r.volume_mm3 - 200.0) < 1e-3, r
    assert r.collides and r.pairs[0][:2] == ('A', 'B')


def test_overlap_within_region():
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), (8, 0, 0))
    halb = Region.box(Frame.identity(), (-50, -50, 0), (50, 50, 50))    # obere Hälfte
    r = overlap(a, b, within=halb)
    assert abs(r.volume_mm3 - 100.0) < 1e-3, r


def test_overlap_kein_kontakt(wuerfel_paar):
    r = overlap(*wuerfel_paar)
    assert not r.collides and r.volume_mm3 == 0.0


def test_overlap_mesh_kern(wuerfel_paar):
    """Sobald eine Seite nur ein Mesh ist, läuft der fcl-Kern."""
    a, b = wuerfel_paar
    b_mesh = Body('Bm', 'Bm', mesh=b.mesh)
    assert not overlap(a, b_mesh).collides
    c_mesh = Body('Cm', 'Cm', mesh=box('C', (10, 10, 10), (5, 0, 0)).mesh)
    r = overlap(a, c_mesh)
    assert r.collides and not r.exact and r.volume_mm3 is None and r.max_penetration_mm > 0


def test_coverage_platte_mit_loch():
    """Platte 40x40x2 mit Ø10-Loch: nur die Punkte im Loch bleiben offen."""
    plate = Box(40, 40, 2) - Cylinder(radius=5, height=10)
    b = Body('PLATTE', 'Platte', solid=plate)
    region = Region.plane_grid(Frame.identity(), 'xy', u=(-18, 18, 2.0), v=(-18, 18, 2.0), w=0.0)
    r = coverage(by=[b], region=region, direction=(0, 0, -1))
    pts = region.sample_points()
    erwartet = int((np.hypot(pts[:, 0], pts[:, 1]) < 5.0).sum())
    assert r.total == len(pts)
    assert r.open == erwartet, (r, erwartet)
    assert r.fraction == pytest.approx((r.total - r.open) / r.total)


def test_protrusion_in_keepout():
    teil = box('T', (10, 10, 10))
    frei = Region.box(Frame.identity(), (2, -50, -50), (50, 50, 50))   # X > 2 ist verboten
    r = protrusion(teil, frei)
    assert r.exact and abs(r.volume_mm3 - 3 * 10 * 10) < 1e-3, r
    assert not r
    weg = Region.box(Frame.identity(), (20, -50, -50), (50, 50, 50))
    assert protrusion(teil, weg)


def test_same_as_verschobene_kopie():
    a = box('A', (20, 20, 10))
    b = box('B', (20, 20, 10), (0.3, 0, 0))
    region = Region.box(Frame.identity(), (-30, -30, -30), (30, 30, 30))
    gleich = same_as(a, box('A2', (20, 20, 10)), region)
    assert gleich.max_deviation_mm < 1e-6, gleich
    versetzt = same_as(a, b, region)
    assert abs(versetzt.max_deviation_mm - 0.3) < 0.02, versetzt
    assert versetzt.diff_mm3 is not None and abs(versetzt.diff_mm3 - 2 * 0.3 * 20 * 10) < 1.0


def test_gap_ignore_blendet_kontaktzone_aus():
    """Ein Nubbel berührt A; wird seine Zone ausgenommen, zählt nur noch der echte Abstand."""
    a = box('A', (10, 10, 10))
    b_solid = Box(10, 10, 10).locate(Location((15, 0, 0))) + Box(5, 2, 2).locate(Location((7.5, 0, 0)))
    b = Body('B', 'B', solid=b_solid)
    assert gap(a, b).min_mm == 0.0
    nubbel = Region.box(Frame.identity(), (4, -2, -2), (11, 2, 2))
    r = gap(a, b, ignore=nubbel)
    assert abs(r.min_mm - 5.0) < 1e-3, r


def test_protrusion_mesh_fallback():
    teil = box('T', (10, 10, 10))
    nur_mesh = Body('Tm', 'Tm', mesh=teil.mesh)
    frei = Region.box(Frame.identity(), (2, -50, -50), (50, 50, 50))
    r = protrusion(nur_mesh, frei)
    assert not r.exact and r.volume_mm3 is None and r.hits > 0, r
    assert protrusion(nur_mesh, Region.box(Frame.identity(), (20, -50, -50), (50, 50, 50)))


def test_crop_schneidet_grosse_dreiecke_ab():
    """FEHLER 1: eine Messbox kleiner als ein Dreieck darf nicht alles wegwerfen.

    Die Würfelflächen bestehen aus 20-mm-Dreiecken; kein einziges liegt vollständig in
    der Box. Vor dem Fix blieben 0 Dreiecke übrig und `gap` meldete stillschweigend inf.
    """
    a = box('A', (20, 20, 20))
    b = box('B', (20, 20, 20), (20.5, 0, 0))
    fenster = Region.box(Frame.identity(), (8, -3, -3), (13, 3, 3))
    geschnitten = fenster.crop(a.mesh)
    assert len(geschnitten.faces) > 0
    lokal = fenster.frame.to_local(geschnitten.vertices)
    assert np.all(lokal >= np.array(fenster.lo) - 1e-6) and np.all(lokal <= np.array(fenster.hi) + 1e-6)
    r = gap(a, b, within=fenster)
    assert abs(r.min_mm - 0.5) < 1e-3, r


def test_nearest_distanzen_sind_exakt():
    """FEHLER 2, Kern: die Abstandsschranke war auf großen Dreiecken bis zu mm zu groß."""
    import trimesh
    from pruefstand.primitives import _nearest

    mesh = box('Z', (20, 20, 20)).mesh
    rng = np.random.default_rng(0)
    pts = rng.uniform(-14, 14, size=(400, 3))
    d = _nearest.distances(pts, mesh)
    exakt = trimesh.proximity.ProximityQuery(mesh).on_surface(pts)[1]
    assert np.abs(d - np.asarray(exakt)).max() < 1e-6


def test_same_as_misst_beide_richtungen_im_ausschnitt():
    """FEHLER 2: außerhalb der Region darf eine Änderung das Ergebnis nicht verfälschen."""
    a = box('A', (20, 20, 10))
    b_solid = Box(20, 20, 10) + Box(10, 10, 10).locate(Location((15, 0, 0)))
    b = Body('B', 'B', solid=b_solid)
    links = Region.box(Frame.identity(), (-11, -11, -6), (0, 11, 6))
    r = same_as(a, b, links)
    assert r.samples > 0
    assert r.max_deviation_mm < 0.01, r


def test_leere_messung_ist_nicht_bestanden():
    """FEHLER 3: „nichts gemessen" darf nicht als bestanden durchgehen."""
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), (10.5, 0, 0))
    weit_weg = Region.box(Frame.identity(), (500, 500, 500), (510, 510, 510))

    g = gap(a, b, within=weit_weg)
    assert g.min_mm == float('inf') and not g.passed and g.nichts_gemessen

    o = overlap(a, b, within=weit_weg)
    assert not o.passed and o.nichts_gemessen

    s = same_as(a, box('A2', (10, 10, 10)), weit_weg)
    assert s.samples == 0 and not s.passed and s.nichts_gemessen

    c = coverage(by=[a], region=Region.points(Frame.identity(), np.zeros((0, 3))), direction=(0, 0, -1))
    assert c.total == 0 and not c.passed and c.nichts_gemessen

    # Das Plugin würde diesen Test wegen der vier Leermessungen rot machen -- hier ist
    # das der Prüfgegenstand, nicht der Fehler. (Dass es rot machen WÜRDE: test_plugin.)
    assert len(results.forget_empty()) == 4


def test_jedes_primitiv_sagt_woher_sein_urteil_kommt():
    """`urteil_auf` ist Pflicht, nicht Zierde.

    Ein exakt gerechneter Nebenwert macht ein abgetastetes Urteil nicht exakt, und ein
    Kollisionskern rechnet immer auf Netzen -- wer das nicht am Messwert sieht, hält
    einen Sweep-Befund für eine CAD-Aussage. `overlap` ist das einzige Primitiv, das
    beides kann, und sagt entsprechend beides.
    """
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), (10.5, 0, 0))
    keepout = Region.box(Frame.identity(), (20, -5, -5), (30, 5, 5))
    punkte = Region.points(Frame.identity(), [[0, 0, 20], [3, 3, 20]])
    aus_netz = Body('M', 'M', mesh=b.mesh)

    assert gap(a, b).urteil_auf == 'mesh'
    assert overlap(a, b).urteil_auf == 'brep'
    assert overlap(a, aus_netz).urteil_auf == 'mesh'
    assert coverage([a], punkte, (0, 0, -1)).urteil_auf == 'mesh'
    assert protrusion(a, keepout).urteil_auf == 'brep'
    assert protrusion(Body('N', 'N', mesh=a.mesh), keepout).urteil_auf == 'mesh'
    assert same_as(a, b, Region.box(Frame.identity(), (-30, -30, -30), (30, 30, 30))).urteil_auf == 'mesh'


def test_sweep_und_access_urteilen_auf_mesh():
    from pruefstand import Screw, Tool, access, sweep
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), (40, 0, 0))
    assert sweep([a], (1, 0, 0), 5.0, [b]).urteil_auf == 'mesh'

    s = Screw(id='s1', norm='M3x12', kopf='zylinder', frame='world',
              punkt=np.array([0.0, 0.0, 5.0]), richtung=np.array([0.0, 0.0, -1.0]))
    assert access(s, [a, b], tool=Tool(bit_len_mm=5, shaft_len_mm=5, grip_len_mm=5)).urteil_auf == 'mesh'
