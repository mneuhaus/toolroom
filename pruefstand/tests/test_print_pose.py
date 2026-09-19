"""Druckpose: synthetische Körper mit exakt bekannten Sollwerten + die echten Probestäbe."""
from pathlib import Path

import pytest
from build123d import Box, Pos

from pruefstand import Body
from pruefstand.body import load_mesh, load_step
from pruefstand.primitives.print_pose import print_pose
from pruefstand.printing import DruckSpecFehler, Profil, lade_druck_spec, pose_matrix

PROBESTAEBE = Path(__file__).resolve().parents[1] / 'probestaebe/var/print/parts_posed'
HOPPER = Path('/Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d-hopper-floor-r1'
              '/native/hopper-floor-r1-native.step')


def koerper(key, solid):
    return Body(key, key, solid=solid)


# ------------------------------------------------------------ synthetisch ----
def test_quader_auflage_exakt():
    """20x10x5-Quader: Auflage exakt 200 mm², kein Überhang, keine Stützen."""
    r = print_pose(koerper('K', Box(20, 10, 5)))
    assert r.contact_mm2 == pytest.approx(200.0, abs=1e-6)
    assert list(r.bbox_mm) == pytest.approx([20.0, 10.0, 5.0], abs=1e-6)
    assert r.overhang_mm2 == 0.0 and r.max_overhang_deg == 0.0
    assert r.max_step_mm == 0.0 and r.needs_support is False
    assert r.fits_bed and r.passed and r.level == 'ok'


def test_bett_zu_klein():
    r = print_pose(koerper('K', Box(20, 10, 5)), bed=(15, 15))
    assert r.fits_bed is False and not r.passed
    assert r.level == 'warnung', 'Druckpose ist eine Warnung, kein Fehler'


def test_kragarm_braucht_stuetzen():
    """Arm springt in einer Schicht um 10 mm nach außen -> Stützen."""
    t = Box(10, 10, 20) + Pos(10, 0, 5) * Box(10, 10, 10)
    r = print_pose(koerper('T', t))
    assert r.max_step_mm == pytest.approx(10.0, abs=0.05)
    assert r.needs_support is True and not r.passed
    assert r.bridges == []


def test_bruecke_braucht_keine_stuetzen():
    """Platte über zwei Pfeilern: zwei getrennte Auflager = Brücke, kein Kragarm."""
    br = (Pos(-10, 0, 5) * Box(5, 10, 10) + Pos(10, 0, 5) * Box(5, 10, 10)
          + Pos(0, 0, 12.5) * Box(25, 10, 5))
    r = print_pose(koerper('B', br))
    assert len(r.bridges) == 1
    assert r.bridges[0]['laenge_mm'] == pytest.approx(10.0, abs=0.2)
    assert r.max_step_mm == 0.0
    assert r.needs_support is False and r.passed


def test_pose_dreht_die_messung():
    """Gleicher Quader, 90° um X: Auflage wechselt von 200 auf 100 mm²."""
    k = koerper('K', Box(20, 10, 5))
    assert print_pose(k, pose={'rotate': [90, 0, 0]}).contact_mm2 == pytest.approx(100.0, abs=1e-6)


# ------------------------------------------------------------ Probestäbe ----
@pytest.mark.skipif(not PROBESTAEBE.exists(), reason='Probestäbe nicht gebaut')
@pytest.mark.parametrize('name,contact', [
    ('S1_d10_senkrecht', 832.2),
    ('S2_d20_senkrecht', 832.2),
    ('S3_d10_45grad', 1269.6),
    ('S4_d10_liegend', 1205.1),
])
def test_probestaebe_bettauflage(name, contact):
    r = print_pose(load_mesh(PROBESTAEBE / f'{name}-posed.stl'))
    assert r.contact_mm2 == pytest.approx(contact, abs=0.2), r
    assert r.fits_bed


@pytest.mark.skipif(not PROBESTAEBE.exists(), reason='Probestäbe nicht gebaut')
@pytest.mark.parametrize('name', ['S1_d10_senkrecht', 'S2_d20_senkrecht',
                                  'S3_d10_45grad', 'S4_d10_liegend'])
def test_probestaebe_stuetzenfrei(name):
    """Alle vier wurden ohne Stützen gesliced — das muss die Messung bestätigen."""
    r = print_pose(load_mesh(PROBESTAEBE / f'{name}-posed.stl'))
    assert r.needs_support is False, r


@pytest.mark.skipif(not PROBESTAEBE.exists(), reason='Probestäbe nicht gebaut')
def test_liegender_rundstab_ueberhang_ohne_stuetzen():
    """S4: 15,6 mm² steiler als 50° und 60,2° Maximum — trotzdem stützenfrei,
    weil der Rücksprung je Schicht (0,236 mm) unter einer Düsenbreite bleibt."""
    r = print_pose(load_mesh(PROBESTAEBE / 'S4_d10_liegend-posed.stl'))
    assert r.overhang_mm2 > 10.0 and r.max_overhang_deg > 55.0
    assert r.max_step_mm == pytest.approx(0.236, abs=0.01)
    assert r.max_step_mm < Profil().duese
    assert r.needs_support is False


# ---------------------------------------------------------- Hopper-Boden ----
@pytest.mark.skipif(not HOPPER.exists(), reason='Hopper-Boden-STEP nicht da')
def test_hopper_boden_flach_stuetzenfrei():
    body = load_step(HOPPER).one()
    r = print_pose(body, pose={'rotate': [18, 0, 0]})
    assert r.fits_bed and r.contact_mm2 > 20000.0
    assert r.overhang_mm2 == 0.0
    assert r.max_step_mm < Profil().duese
    assert r.needs_support is False and r.passed


@pytest.mark.skipif(not HOPPER.exists(), reason='Hopper-Boden-STEP nicht da')
def test_hopper_boden_falsch_herum_braucht_stuetzen():
    """Gegenprobe: umgedreht ist dasselbe Teil nicht mehr stützenfrei."""
    body = load_step(HOPPER).one()
    r = print_pose(body, pose={'rotate': [18, 180, 0]})
    assert r.overhang_mm2 > 100.0
    assert r.needs_support is True and not r.passed


# ------------------------------------------------------------ druck.yaml ----
GUT = """
schema: pruefstand.druck/1
teile:
  - key: T05
    pose: {rotate: [18, 0, 0]}
    profil: {waende: 3, infill: 0.25, duese: 0.42, schicht: 0.2}
    lastabschnitte:
      - name: Fuss
        ebene: {frame: local, punkt: [0, 0, 8], normale: [0, 0, 1]}
        richtung: [0, 1, 0]
"""


def schreib(tmp_path, text):
    p = tmp_path / 'druck.yaml'
    p.write_text(text)
    return p


def test_druck_spec_laden(tmp_path):
    spec = lade_druck_spec(schreib(tmp_path, GUT))
    assert spec.keys() == ['T05'] and 'T05' in spec
    t = spec['T05']
    assert t.profil == Profil(3, 0.25, 0.42, 0.2)
    assert t.profil.wandstaerke_mm == pytest.approx(1.26)
    a = t.abschnitt('Fuss')
    assert list(a.punkt) == [0, 0, 8] and list(a.richtung) == [0, 1, 0]
    assert pose_matrix(t.pose)[2, 2] == pytest.approx(0.95105651629, abs=1e-9)


@pytest.mark.parametrize('kaputt', [
    'schema: pruefstand.druck/2\nteile: [{key: A}]\n',          # falsches Schema
    'schema: pruefstand.druck/1\nteile: []\n',                   # leer
    'schema: pruefstand.druck/1\nteile: [{key: A, tippfehler: 1}]\n',
    'schema: pruefstand.druck/1\nteile: [{key: A, profil: {wande: 3}}]\n',
    'schema: pruefstand.druck/1\nteile: [{key: A}, {key: A}]\n',  # doppelt
    ('schema: pruefstand.druck/1\nteile: [{key: A, lastabschnitte: '
     '[{name: F, ebene: {punkt: [0,0,0], normale: [0,0,0]}, richtung: [0,1,0]}]}]\n'),
    ('schema: pruefstand.druck/1\nteile: [{key: A, lastabschnitte: '
     '[{name: F, ebene: {punkt: [0,0,0], normale: [0,0,1]}, richtung: [0,0,0]}]}]\n'),
    'teile: [{key: A}]\n',                                        # Schema fehlt
    'nur text\n',                                                 # keine Abbildung
])
def test_druck_spec_weist_kaputtes_zurueck(tmp_path, kaputt):
    with pytest.raises(DruckSpecFehler):
        lade_druck_spec(schreib(tmp_path, kaputt))


def test_druck_spec_datei_fehlt(tmp_path):
    with pytest.raises(DruckSpecFehler):
        lade_druck_spec(tmp_path / 'gibtsnicht.yaml')


def test_profil_grenzen():
    with pytest.raises(DruckSpecFehler):
        Profil(waende=0)
    with pytest.raises(DruckSpecFehler):
        Profil(infill=1.5)
    with pytest.raises(DruckSpecFehler):
        Profil(duese=0)
