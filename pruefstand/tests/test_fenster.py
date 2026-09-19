"""Ein Fenster, das Material schneidet, sagt das.

Der häufigste Werkzeugfehler der ersten beiden Etappen war nie ein falsches Teil,
sondern ein von Hand gesetztes Messfenster, dessen Wand im Material lag: die Box über
der Auflage, die Box über dem Stirnwandmaterial (3,94 mm „Abweichung"), der Zylinder
r 4,5 über dem Bund Ø10,5 (liefert 4,41 statt 3,95 -- den Fensterradius, nicht das
Teil). Kein Urteil, nur ein Hinweis; aber er muss am Messwert stehen.
"""
import numpy as np
import pytest
import trimesh

from pruefstand import Frame, Region, gap, same_as

from conftest import box


def wuerfel(kante=10.0, at=(0, 0, 0)):
    m = trimesh.creation.box(extents=(kante, kante, kante))
    m.apply_translation(at)
    return m


# -- Quaderfenster ----------------------------------------------------------

def test_box_fenster_das_nichts_anschneidet_meldet_false():
    """Der Würfel liegt ganz im Fenster -- keine Wand berührt Material."""
    f = Region.box(Frame.identity(), (-20, -20, -20), (20, 20, 20))
    teil = f.crop(wuerfel())
    assert len(teil.faces) > 0
    assert f.meta['rand_schneidet_material'] is False


def test_box_fenster_mitten_im_material_meldet_true():
    """Dieselbe Messung, Fenster 2 mm kürzer: die Wand steht im Würfel."""
    f = Region.box(Frame.identity(), (-3, -20, -20), (20, 20, 20))
    teil = f.crop(wuerfel())
    assert teil.bounds[0][0] == pytest.approx(-3.0, abs=1e-9)
    assert f.meta['rand_schneidet_material'] is True


def test_box_fenster_sammelt_ueber_beide_seiten():
    """Ein Primitiv schneidet beide Körper mit derselben Region.

    Berührt auch nur einer die Wand, ist der Hinweis fällig -- deshalb wird der Merker
    aufgesammelt und nicht je Zuschnitt zurückgesetzt.
    """
    f = Region.box(Frame.identity(), (-3, -20, -20), (20, 20, 20))
    f.crop(wuerfel(at=(30, 0, 0)))          # ganz außerhalb: nichts angeschnitten
    assert f.meta['rand_schneidet_material'] is False
    f.crop(wuerfel())
    assert f.meta['rand_schneidet_material'] is True


# -- Zylinderfenster: der Bund-Fall -----------------------------------------

def zapfen_mit_bund(r_zapfen=3.95, r_bund=5.25):
    """Zapfen Ø7,9 auf der X-Achse, hinten ein Bund Ø10,5 -- wie T60 der Schale R1."""
    z = trimesh.creation.cylinder(radius=r_zapfen, height=8.0, sections=96)
    z.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
    z.apply_translation((-100.0, 0, 0))
    b = trimesh.creation.cylinder(radius=r_bund, height=4.0, sections=96)
    b.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
    b.apply_translation((-94.0, 0, 0))
    return trimesh.util.concatenate([z, b])


def test_zylinderfenster_ueber_dem_freien_zapfen_meldet_false():
    """r 4,5 über dem Ø7,9-Zapfen: 0,55 mm Luft zur Mantelwand, nichts angeschnitten."""
    f = Region.cylinder(Frame.identity(), (-103.0, 0, 0), (1, 0, 0), radius=4.5, length=6.0)
    teil = f.crop(zapfen_mit_bund())
    gemessen = np.linalg.norm(np.asarray(teil.vertices)[:, 1:], axis=1).max()
    assert gemessen == pytest.approx(3.95, abs=0.01)
    assert f.meta['rand_schneidet_material'] is False


def test_zylinderfenster_ueber_dem_bund_meldet_true():
    """Dasselbe Fenster über den Bund verlängert: gemessen wird der Fensterradius.

    Genau dieser Fall hat an der echten T60 4,41 statt 3,95 geliefert. Der Messwert ist
    nicht falsch gerechnet -- er ist die Wand des Fensters. Ohne Hinweis sieht man das
    einem Ergebnis nicht an.
    """
    f = Region.cylinder(Frame.identity(), (-103.0, 0, 0), (1, 0, 0), radius=4.5, length=12.0)
    teil = f.crop(zapfen_mit_bund())
    gemessen = np.linalg.norm(np.asarray(teil.vertices)[:, 1:], axis=1).max()
    assert gemessen > 4.0, 'der Bund füllt das Fenster bis kurz vor die Wand'
    assert f.meta['rand_schneidet_material'] is True


def test_die_unschaerfe_wuerde_beide_faelle_verwechseln():
    """Warum der Kreuzungstest und nicht `rand_unschaerfe_mm`.

    Die Unschärfe ist radius/8 = 0,5625 mm; der freie Zapfen endet 0,55 mm vor der
    Wand. Über die Unschärfe gemessen wäre der saubere Fall als „schneidet" gemeldet
    worden -- ein Hinweis, der immer angeht, ist keiner.
    """
    f = Region.cylinder(Frame.identity(), (-103.0, 0, 0), (1, 0, 0), radius=4.5, length=6.0)
    f.crop(zapfen_mit_bund())
    assert 4.5 - 3.95 < f.meta['rand_unschaerfe_mm']
    assert f.meta['rand_schneidet_material'] is False


def test_deckel_zaehlen_nicht_mit_aber_stehen_in_meta():
    """Die Länge eines Zylinderfensters schneidet fast immer -- das ist kein Befund."""
    f = Region.cylinder(Frame.identity(), (-103.0, 0, 0), (1, 0, 0), radius=4.5, length=6.0)
    f.crop(zapfen_mit_bund())
    assert f.meta['rand_deckel_schneidet_material'] is True
    assert f.meta['rand_schneidet_material'] is False


def test_ringfenster_meldet_auch_die_innere_wand():
    """Beim Ring ist der Innenradius ebenso eine Wand wie der Außenradius.

    Das Fenster reicht bis über die Bundstirnfläche; die spannt r 0…5,25 und kreuzt
    damit die Innenwand bei r 4,5. Ein Ringfenster, das nur den Zapfenmantel sieht,
    kreuzt dagegen gar nichts -- das ist der Fall daneben.
    """
    ring = Region.cylinder(Frame.identity(), (-103.0, 0, 0), (1, 0, 0),
                           radius=8.0, length=12.0, inner_radius=4.5)
    ring.crop(zapfen_mit_bund())
    assert ring.meta['rand_schneidet_material'] is True

    nur_mantel = Region.cylinder(Frame.identity(), (-103.0, 0, 0), (1, 0, 0),
                                 radius=8.0, length=6.0, inner_radius=2.0)
    nur_mantel.crop(zapfen_mit_bund())
    assert nur_mantel.meta['rand_schneidet_material'] is False


# -- Weg in die Ergebnisse --------------------------------------------------

def test_gap_traegt_den_hinweis_weiter():
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), at=(10.5, 0, 0))
    fenster = Region.box(Frame.identity(), (-3, -20, -20), (20, 20, 20))
    r = gap(a, b, within=fenster)
    assert r.min_mm == pytest.approx(0.5, abs=1e-6)
    assert r.fenster_schneidet_material is True
    assert r.as_dict()['fenster_schneidet_material'] is True


def test_same_as_traegt_den_hinweis_weiter():
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10))
    weit = Region.box(Frame.identity(), (-20, -20, -20), (20, 20, 20))
    r = same_as(a, b, weit, max_deviation_mm=0.01)
    assert r.fenster_schneidet_material is False


def test_ohne_fenster_gibt_es_keine_aussage():
    """`None` heißt: nichts zugeschnitten, also auch nichts zu melden.

    Ein `False` an dieser Stelle wäre eine Behauptung über einen Rand, den niemand
    angesehen hat.
    """
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), at=(10.5, 0, 0))
    r = gap(a, b)
    assert r.fenster_schneidet_material is None
    assert 'fenster_schneidet_material' not in r.as_dict()


# -- Erwartete Unterschiede -------------------------------------------------

def test_same_as_ohne_und_mit_erwarteter_bohrung():
    """Eine ergänzte Bohrung ist eine Änderung -- aber nicht unbedingt eine Abweichung.

    Ohne `erwartet` misst `same_as` die Bohrung als Abweichung in Lochtiefe; benannt
    man sie, bleibt das Grundrauschen der Abtastung übrig. Beide Zahlen gehören in den
    Test, sonst liest sich das Ausnehmen wie ein Weichrechnen.
    """
    from build123d import Box, Cylinder

    from pruefstand import Body
    gebohrt = Body('neu', 'neu', solid=Box(10, 10, 10) - Cylinder(1.0, 20))
    voll = Body('alt', 'alt', solid=Box(10, 10, 10))
    fenster = Region.box(Frame.identity(), (-6, -6, -6), (6, 6, 6))

    ohne = same_as(gebohrt, voll, fenster)
    assert ohne.max_deviation_mm > 4.0, ohne
    assert ohne.erwartet_ausgenommen == 0

    loch = Region.cylinder(Frame.identity(), (0, 0, -6), (0, 0, 1), radius=1.3, length=12.0)
    mit = same_as(gebohrt, voll, fenster, erwartet=[loch], max_deviation_mm=0.05)
    assert mit.max_deviation_mm < 0.05, mit
    assert mit.erwartet_ausgenommen > 0
    assert mit.passed
    assert mit.diff_mm3 == pytest.approx(ohne.diff_mm3, rel=1e-6), \
        'das Differenzvolumen zählt den erwarteten Unterschied weiter mit'


def test_erwartete_region_die_nichts_trifft_aendert_nichts():
    from build123d import Box, Cylinder

    from pruefstand import Body
    gebohrt = Body('neu', 'neu', solid=Box(10, 10, 10) - Cylinder(1.0, 20))
    voll = Body('alt', 'alt', solid=Box(10, 10, 10))
    fenster = Region.box(Frame.identity(), (-6, -6, -6), (6, 6, 6))
    daneben = Region.box(Frame.identity(), (50, 50, 50), (60, 60, 60))
    r = same_as(gebohrt, voll, fenster, erwartet=[daneben])
    assert r.erwartet_ausgenommen == 0
    assert r.max_deviation_mm > 4.0
