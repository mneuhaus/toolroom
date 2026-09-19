"""Schnittstellen als Objekte -- und die Gegenfälle, an denen sie scheitern müssen.

Die Research vom 17.09.2026 nennt als Erfolgskriterium für das Datenmodell: „jeder
Defekt wird FAIL oder INDETERMINATE, **niemals** falsches PASS". Genau das wird hier
durchgespielt: korrekter Fall, zu kleine Bohrung, Achsversatz, Zwischenhindernis,
fehlendes Mapping. Grün darf nur der erste werden.
"""
import numpy as np
import pytest
from build123d import Box, Cylinder, Location, Plane

from pruefstand import AMBIGUOUS, Body, MISSING, UNIQUE, interface_ok
from pruefstand.interface import (SCHEMA, Interface, interface_from_dict, interfaces_by_id,
                                  load_interfaces)
from pruefstand.results import forget_open


def zapfenteil(key='P', r=4.0, laenge=10.0, versatz=(0.0, 0.0), neigung_deg=0.0):
    """Platte in der YZ-Ebene, daraus ein Zapfen entlang +X.

    `versatz` schiebt den Zapfen quer zur Sollachse, `neigung_deg` kippt ihn -- die
    beiden Defekte, die ein Radiusvergleich allein nicht sieht.
    """
    platte = Box(4, 40, 40).locate(Location((-2.0, 0.0, 0.0)))
    richtung = (float(np.cos(np.radians(neigung_deg))), float(np.sin(np.radians(neigung_deg))), 0.0)
    lage = Plane(origin=(laenge / 2 * richtung[0], versatz[0] + laenge / 2 * richtung[1], versatz[1]),
                 z_dir=richtung)
    return Body(key, key, solid=platte + lage * Cylinder(r, laenge))


def bohrteil(key='B', r=1.31, tiefe=20.0, versatz=(0.0, 0.0)):
    """Klotz mit einer Bohrung entlang X -- Gegenstück zum Zapfen."""
    klotz = Box(10, 40, 40)
    loch = Plane(origin=(0.0, versatz[0], versatz[1]), z_dir=(1, 0, 0)) * Cylinder(r, tiefe)
    return Body(key, key, solid=klotz - loch)


def iface(**kw):
    d = {'id': 'x', 'kind': 'pin', 'body': 'P', 'axis': [1, 0, 0], 'origin': [0, 0, 0],
         'radius': 4.0, 'length': 10.0}
    d.update(kw)
    return interface_from_dict(d)


# -- Der Fall, der grün werden darf -----------------------------------------

def test_korrekter_zapfen_ist_unique_und_besteht():
    teil = zapfenteil(r=4.0)
    r = interface_ok(iface(), [teil])
    assert r.status == UNIQUE
    assert r.radius_mm == pytest.approx(4.0, abs=1e-6)
    assert r.axis_deg == pytest.approx(0.0, abs=1e-9)
    assert r.passed, r.verletzt
    assert r.urteil_auf == 'brep', 'Radius und Achse kommen aus den exakten Flächen'


# -- Gegenfall 1: zu kleine Bohrung -----------------------------------------

def test_zu_kleine_bohrung_faellt_durch():
    """Ø2,4 statt Ø2,62: nah genug, um die Fläche zu erkennen, zu weit fürs Urteil."""
    teil = bohrteil(r=1.2)
    r = interface_ok(iface(kind='bore', body='B', radius=1.31), [teil])
    assert r.status == UNIQUE
    assert r.radius_mm == pytest.approx(1.2, abs=1e-6)
    assert not r.passed
    assert any('radius' in v for v in r.verletzt), r.verletzt


def test_viel_zu_kleine_bohrung_ist_unentschieden_nicht_gruen():
    """Ø1,0: das ist keine verfehlte Schnittstelle mehr, das ist eine andere Fläche."""
    teil = bohrteil(r=0.5)
    r = interface_ok(iface(kind='bore', body='B', radius=1.31), [teil])
    assert r.status == MISSING
    assert r.unentschieden and not r.passed
    assert forget_open(), 'der Lauf muss den offenen Ausgang sehen'


# -- Gegenfall 2: Achsversatz -----------------------------------------------

def test_achsversatz_faellt_durch():
    """0,15 mm quer zur Sollachse -- gefunden, aber außerhalb der Toleranz 0,05."""
    teil = zapfenteil(versatz=(0.15, 0.0))
    r = interface_ok(iface(), [teil])
    assert r.status == UNIQUE
    assert r.offset_mm == pytest.approx(0.15, abs=1e-6)
    assert not r.passed
    assert any('offset' in v for v in r.verletzt), r.verletzt


def test_schiefe_achse_faellt_durch():
    """Ein gekippter Zapfen hat denselben Radius -- der Winkel verrät ihn."""
    teil = zapfenteil(neigung_deg=0.6)
    r = interface_ok(iface(tolerance={'axis_deg': 0.1, 'offset': 1.0}), [teil])
    assert r.status == UNIQUE
    assert r.axis_deg == pytest.approx(0.6, abs=1e-3)
    assert not r.passed
    assert any('axis_deg' in v for v in r.verletzt), r.verletzt


# -- Gegenfall 3: Zwischenhindernis -----------------------------------------

def test_zwischenhindernis_bricht_den_formschluss():
    """Eine Scheibe zwischen Zapfen und Lager: Maße stimmen, der Sitz sitzt nicht.

    Ohne den Partnerabstand wäre das grün -- der Zapfen selbst ist ja tadellos. Genau
    dafür steht `partner` in der Pflegedatei.
    """
    def lager(bohrung_r):
        ring = Box(6, 40, 40).locate(Location((6.0, 0.0, 0.0)))
        ring -= Plane(origin=(0, 0, 0), z_dir=(1, 0, 0)) * Cylinder(bohrung_r, 40)
        return Body('L608', 'L608', solid=ring)

    teil = zapfenteil(r=4.0, laenge=10.0)
    sitzt = interface_ok(iface(partner='L608'), [teil], partner_body=lager(4.0))
    assert sitzt.status == UNIQUE
    assert sitzt.gap_mm == pytest.approx(0.0, abs=1e-3), 'Ø8 im Ø8: Formschluss'
    assert sitzt.passed, sitzt.verletzt

    # Zwischen Zapfen und Lagerinnenring steckt eine Hülse von 0,3 mm Wand. Am Zapfen
    # selbst ist nichts auszusetzen -- der Sitz sitzt trotzdem nicht.
    r = interface_ok(iface(partner='L608'), [teil], partner_body=lager(4.3))
    assert r.status == UNIQUE, 'der Zapfen ist tadellos, nur sitzt er nicht mehr'
    assert r.gap_mm == pytest.approx(0.3, abs=0.02)
    assert not r.passed
    assert any('gap' in v for v in r.verletzt), r.verletzt


# -- Gegenfall 4: fehlendes Mapping -----------------------------------------

def test_fehlendes_mapping_ist_unentschieden():
    """Kein Körper zum Suchbegriff: das beweist keinen Verstoß, aber auch nichts Gutes."""
    r = interface_ok(iface(body='gibt_es_nicht'), [zapfenteil()])
    assert r.unentschieden and not r.passed
    assert 'gibt_es_nicht' in r.offen_grund
    assert forget_open()


def test_fehlender_partner_ist_unentschieden():
    r = interface_ok(iface(partner='H608'), [zapfenteil()])
    assert r.unentschieden and not r.passed
    assert 'H608' in r.offen_grund
    assert forget_open()


def test_nur_netz_geladen_ist_unentschieden():
    """Im Netz gibt es keine Flächen zu erkennen -- also auch kein Urteil."""
    teil = zapfenteil()
    ohne_solid = Body('P', 'P', mesh=teil.mesh)
    r = interface_ok(iface(), [ohne_solid])
    assert r.status == MISSING and r.unentschieden
    assert 'Solid' in r.offen_grund
    assert forget_open()


# -- Mehrdeutigkeit ---------------------------------------------------------

def test_zwei_passende_flaechen_sind_ambiguous():
    """Eine weite Toleranz findet Bund und Zapfen -- und darf sich nicht entscheiden."""
    platte = Box(4, 40, 40).locate(Location((-2.0, 0.0, 0.0)))
    zapfen = Plane(origin=(5.0, 0, 0), z_dir=(1, 0, 0)) * Cylinder(3.95, 10)
    bund = Plane(origin=(1.0, 0, 0), z_dir=(1, 0, 0)) * Cylinder(5.25, 2)
    teil = Body('P', 'P', solid=platte + zapfen + bund)
    r = interface_ok(iface(radius=4.5, tolerance={'radius': 2.0}), [teil])
    assert r.status == AMBIGUOUS
    assert len(r.candidates) == 2
    assert r.unentschieden and not r.passed
    assert forget_open()


def test_vier_bohrungen_sind_unique_drei_sind_missing():
    """`count: 4` heißt: alle vier oder keine Aussage."""
    klotz = Box(10, 40, 40)
    ecken = [(6.7175, 6.7175), (-6.7175, 6.7175), (6.7175, -6.7175), (-6.7175, -6.7175)]
    for y, z in ecken:
        klotz -= Plane(origin=(0, y, z), z_dir=(1, 0, 0)) * Cylinder(1.31, 20)
    vier = interface_ok(iface(kind='bore', body='B', radius=1.31, pitch_radius=9.5, count=4),
                        [Body('B', 'B', solid=klotz)])
    assert vier.status == UNIQUE and len(vier.candidates) == 4
    assert vier.offset_mm == pytest.approx(9.5, abs=1e-4)
    assert vier.passed, vier.verletzt

    drei = Box(10, 40, 40)
    for y, z in ecken[:3]:
        drei -= Plane(origin=(0, y, z), z_dir=(1, 0, 0)) * Cylinder(1.31, 20)
    r = interface_ok(iface(kind='bore', body='B', radius=1.31, pitch_radius=9.5, count=4),
                     [Body('B', 'B', solid=drei)])
    assert r.status == MISSING and not r.passed
    assert forget_open()


# -- Fenster ----------------------------------------------------------------

def test_region_steht_weiter_als_die_schnittstelle():
    """Ein Fenster exakt auf der Oberfläche ist eine Gussform, kein Fenster."""
    z = iface().region()
    assert z.kind == 'cylinder'
    assert z.radius == pytest.approx(4.5, abs=1e-9)      # 3,95 + 0,5 Zuschlag -> 4,0 + 0,5
    teil = zapfenteil()
    z.crop(teil.mesh)
    assert z.meta['rand_schneidet_material'] is False


def test_plane_region_liegt_um_die_flaeche_herum():
    p = iface(kind='plane', axis=[0, 0, 1], size=[20, 10], length=2.0, radius=None)
    z = p.region()
    lo, hi = z.lo, z.hi
    assert (hi - lo).tolist() == [20.0, 10.0, 2.0]
    assert lo[2] == pytest.approx(-1.0) and hi[2] == pytest.approx(1.0)


def test_unentschieden_ist_ein_eigener_ausgang_im_lauf(pytester):
    """Ein AMBIGUOUS, das der Test nicht behandelt, darf den Lauf nicht grün lassen."""
    pytester.makepyfile("""
from build123d import Box, Cylinder, Location, Plane
from pruefstand import Body, interface_ok
from pruefstand.interface import interface_from_dict

def test_mehrdeutig():
    platte = Box(4, 40, 40).locate(Location((-2.0, 0.0, 0.0)))
    teil = Body('P', 'P', solid=platte
                + Plane(origin=(5.0, 0, 0), z_dir=(1, 0, 0)) * Cylinder(3.95, 10)
                + Plane(origin=(1.0, 0, 0), z_dir=(1, 0, 0)) * Cylinder(5.25, 2))
    interface_ok(interface_from_dict(dict(
        id='x', kind='pin', body='P', axis=[1, 0, 0], origin=[0, 0, 0],
        radius=4.5, length=10.0, tolerance={'radius': 2.0})), [teil])
""")
    ergebnis = pytester.runpytest('-q')
    assert ergebnis.ret != 0, 'ein Lauf ohne Urteil darf nicht mit Erfolg enden'
    ergebnis.stdout.fnmatch_lines(['*unentschieden*'])


# -- Pflegedatei ------------------------------------------------------------

GUT = f"""
schema: {SCHEMA}
schnittstellen:
  - id: journal_pin
    kind: pin
    body: T60
    axis: [1, 0, 0]
    origin: [-104.3, 135, 236]
    radius: 3.95
    length: 7.4
    partner: H608
    tolerance: {{radius: 0.05, axis_deg: 0.1, offset: 0.05}}
"""


def test_lader_liest_eine_gute_datei(tmp_path):
    p = tmp_path / 'schnittstellen.yaml'
    p.write_text(GUT)
    ifs = load_interfaces(p)
    assert len(ifs) == 1
    j = interfaces_by_id(ifs)['journal_pin']
    assert isinstance(j, Interface)
    assert j.radius == 3.95 and j.partner == 'H608' and j.count == 1
    assert j.tol('radius') == 0.05
    assert j.tol('gap') == 0.02, 'nicht genannte Toleranzen kommen aus der Vorgabe'
    assert np.allclose(j.axis, [1, 0, 0])


MUELL = [
    ('schema: falsch/9\nschnittstellen: []', 'Schema'),
    (f'schema: {SCHEMA}\nschnittstellen: []', 'schnittstellen'),
    (f'schema: {SCHEMA}\nschnittstellen: [{{kind: pin, body: T, axis: [1,0,0], origin: [0,0,0]}}]', 'Pflichtfelder'),
    (f'schema: {SCHEMA}\nschnittstellen: [{{id: a, kind: haken, body: T, axis: [1,0,0], origin: [0,0,0]}}]', 'unbekannt'),
    (f'schema: {SCHEMA}\nschnittstellen: [{{id: a, kind: pin, body: T, axis: [0,0,0], origin: [0,0,0], radius: 1}}]', 'Nullvektor'),
    (f'schema: {SCHEMA}\nschnittstellen: [{{id: a, kind: pin, body: T, axis: [1,0,0], origin: [0,0,0]}}]', 'radius'),
    (f'schema: {SCHEMA}\nschnittstellen: [{{id: a, kind: plane, body: T, axis: [1,0,0], origin: [0,0,0]}}]', 'size'),
    (f'schema: {SCHEMA}\nschnittstellen: [{{id: a, kind: pin, body: T, axis: [1,0,0], origin: [0,0,0], radius: 1, count: 0}}]', 'count'),
    (f'schema: {SCHEMA}\nschnittstellen: [{{id: a, kind: pin, body: T, axis: [1,0,0], origin: [0,0,0], radius: 1, tolerance: {{durchmesser: 1}}}}]', 'Toleranzen'),
]


@pytest.mark.parametrize('text,meldung', MUELL)
def test_lader_weist_muell_ab(tmp_path, text, meldung):
    """Eine kaputte Pflegedatei fliegt früh und laut auf, nicht erst beim Messen."""
    p = tmp_path / 'schnittstellen.yaml'
    p.write_text(text)
    with pytest.raises(ValueError) as e:
        load_interfaces(p)
    assert meldung in str(e.value)


def test_lader_verbietet_doppelte_ids(tmp_path):
    p = tmp_path / 'schnittstellen.yaml'
    p.write_text(GUT + GUT.split('schnittstellen:')[1])
    with pytest.raises(ValueError, match='doppelte'):
        load_interfaces(p)


def test_fehlende_datei(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_interfaces(tmp_path / 'gibt_es_nicht.yaml')
