"""screw_chain(): Kette, Lochdurchmesser, Einschraubtiefe, Restwand.

Synthetische Fälle mit exakt bekannten Nennmaßen (Platten mit gebohrten Löchern)
plus ein Fall an der echten Riemenklemme R1.
"""
import numpy as np
import pytest
from build123d import Box, Cylinder, Location

from pruefstand import Body, Machine, load_step, results
from pruefstand.primitives.screw_chain import ScrewChainResult, lochtabelle, screw_chain
from pruefstand.screws import Screw, load_screws, screws_by_id

BELT_CLAMP = '/Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d-belt-clamp-r1'
R6D = '/Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d'


# -- Bausteine -----------------------------------------------------------

def platte(key, dicke, z_oben, loch_d, breite=30.0, loch_tiefe=None, ribs=0):
    """Platte mit Loch auf der Z-Achse; Oberseite bei `z_oben`, Material nach unten."""
    p = Box(breite, breite, dicke).locate(Location((0, 0, z_oben - dicke / 2)))
    tiefe = dicke if loch_tiefe is None else loch_tiefe
    bohrung = Cylinder(loch_d / 2, tiefe).locate(Location((0, 0, z_oben - tiefe / 2)))
    p = p - bohrung
    for k in range(ribs):
        a = 2 * np.pi * k / ribs
        r = loch_d / 2
        rippe = Cylinder(0.5, tiefe).locate(Location((r * np.cos(a), r * np.sin(a),
                                                      z_oben - tiefe / 2)))
        p = p + rippe
    return Body(key, key, solid=p)


def schraube(sid='S', norm='M3x16', z=0.0, beisst=None, xy=(0.0, 0.0)):
    return Screw(id=sid, norm=norm, kopf='zylinder', frame='world',
                 punkt=np.array([xy[0], xy[1], z], dtype=float),
                 richtung=np.array([0.0, 0.0, -1.0]), beisst=beisst)


@pytest.fixture
def gute_kette():
    """Durchgang Ø3,4 in 5 mm Platte, darunter Pilot Ø2,62 in 15 mm Platte."""
    return [platte('A', 5.0, 0.0, 3.4), platte('B', 15.0, -5.0, 2.62)]


# -- Lochtabelle ---------------------------------------------------------

def test_lochtabelle_m3_aus_tabelle():
    tab, quelle = lochtabelle(3.0)
    assert quelle == 'tabelle'
    assert tab == {'durchgang': 3.4, 'pilot': 2.62, 'crush': 4.2}


def test_lochtabelle_m5_skaliert():
    tab, quelle = lochtabelle(5.0)
    assert quelle == 'skaliert' and tab['durchgang'] > tab['pilot']


# -- Messgenauigkeit -----------------------------------------------------

@pytest.mark.parametrize('soll', [2.62, 3.4, 4.2])
def test_lochdurchmesser_auf_hundertstel(soll):
    """Der gemessene Durchmesser trifft das Nennmaß; der Tessellationsfehler ist
    kleiner als 0,01 mm und damit rund 80-mal kleiner als der Abstand Pilot/Durchgang."""
    r = screw_chain(schraube(), [platte('A', 10.0, 0.0, soll)])
    gemessen = r.link('A')['hole_d_mm']
    assert abs(gemessen - soll) < 0.01, (gemessen, soll)


def test_pilot_und_durchgang_werden_getrennt():
    a = screw_chain(schraube(), [platte('A', 10.0, 0.0, 2.62)]).link('A')
    b = screw_chain(schraube(), [platte('B', 10.0, 0.0, 3.4)]).link('B')
    assert a['kind'] == 'pilot' and b['kind'] == 'durchgang'
    assert b['hole_d_mm'] - a['hole_d_mm'] > 0.7


def test_crush_grip_hat_drei_rippen():
    r = screw_chain(schraube(), [platte('A', 10.0, 0.0, 4.2, ribs=3)])
    glied = r.link('A')
    assert glied['ribs'] == 3 and glied['kind'] == 'crush', glied
    assert abs(glied['hole_d_max_mm'] - 4.2) < 0.05


def test_rundes_loch_hat_keine_rippen():
    assert screw_chain(schraube(), [platte('A', 10.0, 0.0, 4.2)]).link('A')['ribs'] == 0


def test_ein_und_austritt_treffen_die_plattendicke():
    r = screw_chain(schraube(), [platte('A', 5.0, 0.0, 3.4)])
    g = r.link('A')
    assert abs(g['entry_mm'] - 0.0) < 0.01 and abs(g['exit_mm'] - 5.0) < 0.01, g


# -- Kettenregeln --------------------------------------------------------

def test_gute_kette_besteht(gute_kette):
    r = screw_chain(schraube(beisst='B'), gute_kette)
    assert isinstance(r, ScrewChainResult) and bool(r), r.reasons
    assert [g['key'] for g in r.links] == ['A', 'B']
    assert r.biting == ['B']
    assert abs(r.engagement_mm - 11.0) < 0.05, r.engagement_mm
    assert r.required_engagement_mm == 9.0


def test_restwand_wird_gemessen():
    """Pilotplatte 20 mm breit: Restwand = (20 - 2,62)/2 = 8,69 mm."""
    r = screw_chain(schraube(), [platte('A', 5.0, 0.0, 3.4),
                                 platte('B', 15.0, -5.0, 2.62, breite=20.0)])
    assert abs(r.min_wall_mm - 8.69) < 0.05, r.min_wall_mm


def test_zwei_beissende_glieder_fallen_durch():
    r = screw_chain(schraube(), [platte('A', 5.0, 0.0, 2.62), platte('B', 15.0, -5.0, 2.62)])
    assert not r.passed and r.biting == ['A', 'B']
    assert any('beißende Glieder' in g for g in r.reasons), r.reasons


def test_kein_beissendes_glied_faellt_durch(gute_kette):
    r = screw_chain(schraube(), [platte('A', 5.0, 0.0, 3.4), platte('B', 15.0, -5.0, 3.4)])
    assert not r.passed and r.biting == []
    assert 'kein beißendes Glied' in r.reasons


def test_zu_kurze_einschraubtiefe_faellt_durch(gute_kette):
    """M3x6 durch eine 5 mm dicke Backe: 1 mm im Pilotloch, gefordert 3 x M3 = 9 mm."""
    r = screw_chain(schraube(norm='M3x6'), gute_kette)
    assert not r.passed
    assert abs(r.engagement_mm - 1.0) < 0.05, r.engagement_mm
    assert r.required_engagement_mm == 9.0
    assert any('Einschraubtiefe' in g for g in r.reasons), r.reasons


def test_kurzes_teil_darf_kuerzer_greifen():
    """Ist das beißende Teil nur 4 mm dick, ist 4 mm Eingriff das Maximum -- die
    Forderung 3 x M3 wird auf das Machbare begrenzt, nicht gelockert."""
    r = screw_chain(schraube(), [platte('A', 5.0, 0.0, 3.4), platte('B', 4.0, -5.0, 2.62)])
    assert abs(r.engagement_mm - 4.0) < 0.05
    assert abs(r.required_engagement_mm - 4.0) < 0.05 and bool(r), r.reasons


def test_erwartetes_beissendes_teil_wird_geprueft(gute_kette):
    r = screw_chain(schraube(beisst='A'), gute_kette)
    assert not r.passed and any('erwartet beißend' in g for g in r.reasons), r.reasons


def test_material_auf_der_achse_faellt_durch():
    r = screw_chain(schraube(), [platte('A', 5.0, 0.0, 3.4),
                                 Body('Voll', 'Voll', solid=Box(20, 20, 10).locate(
                                     Location((0, 0, -10))))])
    assert not r.passed and r.material_on_axis == ['Voll']


def test_nichts_gemessen_ist_nicht_bestanden(gute_kette):
    r = screw_chain(schraube(xy=(100.0, 100.0)), gute_kette)
    assert r.links == [] and not r.passed and r.nichts_gemessen
    # Das Plugin würde den Test wegen der Leermessung rot machen -- hier ist sie der
    # Prüfgegenstand (vgl. tests/test_primitives.py).
    assert len(results.forget_empty()) == 1


def test_eigener_schraubenkoerper_wird_uebersprungen(gute_kette):
    bolzen = Body('Schraube', 'Schraube',
                  solid=Cylinder(1.5, 16).locate(Location((0, 0, -8))))
    r = screw_chain(schraube(beisst='B'), gute_kette + [bolzen])
    assert r.own_bodies == ['Schraube']
    assert [g['key'] for g in r.links] == ['A', 'B'] and bool(r), r.reasons


# -- Ergebnisobjekt ------------------------------------------------------

def test_link_meldet_mehrdeutigkeit(gute_kette):
    r = screw_chain(schraube(beisst='B'), gute_kette)
    with pytest.raises(ValueError):
        r.link('x-gibt-es-nicht')
    assert 'beisst' in r.summary()


# -- echter Fall: Riemenklemme R1 ---------------------------------------

@pytest.mark.skipif(not __import__('pathlib').Path(BELT_CLAMP).exists(),
                    reason='step-feeder/rocking-photo-tray-r6d-belt-clamp-r1 nicht vorhanden')
def test_echte_riemenklemme_vier_m3x16():
    schrauben = load_screws(f'{BELT_CLAMP}/spec/schrauben.yaml')
    assert len(schrauben) == 4
    m = Machine.load(f'{R6D}/machine/machine.json')
    parts = load_step(f'{BELT_CLAMP}/native/belt-clamp-r1-native.step')
    s = screws_by_id(schrauben)['M3x16-1']
    r = screw_chain(s, parts, frame=m)
    assert bool(r), (r.reasons, r.links)
    durchgang, pilot = r.links
    assert 'Klemmbacke' in durchgang['key'] and durchgang['kind'] == 'durchgang'
    assert abs(durchgang['hole_d_mm'] - 3.4) < 0.01, durchgang
    assert 'P03' in pilot['key'] and pilot['kind'] == 'pilot'
    assert abs(pilot['hole_d_mm'] - 2.62) < 0.01, pilot
    assert r.engagement_mm > 10.0 and r.required_engagement_mm == 9.0
    assert r.min_wall_mm > 3.0


# -- YAML-Loader ---------------------------------------------------------

def test_yaml_fehlerfaelle(tmp_path):
    def schreib(text):
        p = tmp_path / 'x.yaml'
        p.write_text(text)
        return p

    kopf = 'schema: pruefstand.schrauben/1\nschrauben:\n'
    eintrag = ('  - id: A\n    norm: M3x16\n    kopf: zylinder\n    frame: world\n'
               '    punkt: [0, 0, 0]\n    richtung: [0, 0, -1]\n')
    assert len(load_screws(schreib(kopf + eintrag))) == 1
    with pytest.raises(ValueError, match='Schema'):
        load_screws(schreib('schema: anderes/1\nschrauben: []\n'))
    with pytest.raises(ValueError, match='leer'):
        load_screws(schreib('schema: pruefstand.schrauben/1\nschrauben: []\n'))
    with pytest.raises(ValueError, match='doppelte'):
        load_screws(schreib(kopf + eintrag + eintrag))
    with pytest.raises(ValueError, match='Pflichtfelder'):
        load_screws(schreib(kopf + '  - id: A\n    norm: M3x16\n'))
    with pytest.raises(ValueError, match='norm'):
        load_screws(schreib(kopf + eintrag.replace('M3x16', 'M3-16')))
    with pytest.raises(ValueError, match='kopf'):
        load_screws(schreib(kopf + eintrag.replace('zylinder', 'linsenkopf')))
    with pytest.raises(ValueError, match='Nullvektor'):
        load_screws(schreib(kopf + eintrag.replace('[0, 0, -1]', '[0, 0, 0]')))
    with pytest.raises(FileNotFoundError):
        load_screws(tmp_path / 'fehlt.yaml')


def test_screw_norm_und_achse():
    s = schraube(norm='M5x20', z=3.0)
    assert s.nominal_mm == 5.0 and s.laenge_mm == 20.0 and s.groesse == 'M5'
    origin, u = s.axis_points(None)
    assert np.allclose(origin, [0, 0, 3.0]) and np.allclose(u, [0, 0, -1])
