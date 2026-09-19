"""sweep() und der Montage-Lader.

Der wichtigste Test hier ist `test_duennwand_wird_gefunden_abtastung_nicht`: er zeigt an einem
Fall, den eine Abtastung mit grober Schrittzahl übersieht, dass der Marsch die Wand findet.
"""
import time
from pathlib import Path

import numpy as np
import pytest
from build123d import Box, Location

from pruefstand import Body, Machine, load_step, results
from pruefstand.assembly import MontageError, Step, load_assembly
from pruefstand.primitives._sweep import distance_at, penetration_at
from pruefstand.primitives.sweep import SweepResult, sweep

R6D = Path('/Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d/machine/machine.json')
KLEMME = Path('/Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d-belt-clamp-r1')


def bx(key, size, at=(0, 0, 0), moving=False):
    return Body(key, key, solid=Box(*size).locate(Location(tuple(float(x) for x in at))),
                moving=moving)


# --------------------------------------------------------------------------- Dünnwand-Beweis

#: Die Sonde ist eine 1,2 mm dünne Rippe, sie läuft von x=0 aus 130 mm in +X.
SONDE = (1.2, 4.0, 4.0)
#: Die Wand steht quer im Weg, 0,6 mm dick, Mitte bei x = 49,0.
WAND_X, WAND_D = 49.0, 0.6
#: Vorderkante Sonde 0,6; Vorderkante Wand 48,7  ->  Kontakt bei 48,1 mm Weg.
ERWARTET = (WAND_X - WAND_D / 2) - SONDE[0] / 2          # 48.1
#: Hinterkante Sonde -0,6 verlässt die Wand bei 49,9 -> Kollisionsfenster nur 1,8 mm lang.
FENSTER = ((WAND_X + WAND_D / 2) + SONDE[0] / 2) - ERWARTET


def kanal_mit_wand():
    """Ein einziger fester Körper: langer Kanal über den ganzen Weg + dünne Wand quer darin.

    Alles in einem Körper, damit das Paar genau eine Bounding-Box hat, die den kompletten Weg
    überdeckt. Das AABB-Fenster kann hier also nichts wegschneiden -- die Wand muss vom Marsch
    selbst gefunden werden, nicht von der Vorfilterung.
    """
    links = Box(170, 4, 20).locate(Location((65.0, 6.5, 0)))     # Innenkante y=4,5 -> 2,5 mm Luft
    rechts = Box(170, 4, 20).locate(Location((65.0, -6.5, 0)))
    wand = Box(WAND_D, 8, 8).locate(Location((WAND_X, 0, 0)))
    return Body('KANAL', 'KANAL', solid=links + rechts + wand)


def test_duennwand_wird_gefunden_abtastung_nicht():
    sonde = bx('SONDE', SONDE, moving=True)
    kanal = kanal_mit_wand()

    # 1) Was eine Abtastung mit grober Schrittzahl sieht: nichts.
    mesh_s, mesh_k = sonde.mesh, kanal.mesh
    u = np.array([1.0, 0.0, 0.0])
    grob = [distance_at(mesh_s, mesh_k, u * t) for t in np.arange(0.0, 130.0 + 1e-9, 2.0)]
    assert min(grob) > 0.0, 'Abtastung soll die Wand gerade verfehlen, sonst beweist der Test nichts'
    assert FENSTER < 2.0, f'Kollisionsfenster {FENSTER} mm muss kleiner als die Schrittweite sein'

    # 2) Was der Marsch sieht: die Wand, auf 0,01 mm genau.
    t0 = time.perf_counter()
    r = sweep(sonde, vector=(1, 0, 0), distance=130, against=kanal)
    dauer = time.perf_counter() - t0

    assert r.collides and not r.passed, r
    assert abs(r.first_contact_mm - ERWARTET) < 0.02, (r.first_contact_mm, ERWARTET)
    assert r.pairs == [['SONDE', 'KANAL']]
    assert r.steps > 10, f'nur {r.steps} Schritte -- der Marsch ist hier nicht gelaufen'
    assert dauer < 10.0


def test_duennwand_auch_bei_grober_aufloesung():
    """Auch mit absichtlich grob gesetzter Auflösung darf nichts durchrutschen.

    resolution_mm ist die Kontakttoleranz, nicht eine Schrittweite -- ein größerer Wert meldet
    den Kontakt also früher, niemals gar nicht.
    """
    r = sweep(bx('SONDE', SONDE, moving=True), vector=(1, 0, 0), distance=130,
              against=kanal_mit_wand(), resolution_mm=0.5)
    assert r.collides
    assert ERWARTET - 0.6 <= r.first_contact_mm <= ERWARTET + 1e-6, r.first_contact_mm


def test_duennwand_seitlich_daneben_ist_frei():
    """Gegenprobe: dieselbe Wand, aber die Sonde läuft daran vorbei."""
    sonde = bx('SONDE', SONDE, at=(0, 0, 30), moving=True)       # über dem Kanal
    r = sweep(sonde, vector=(1, 0, 0), distance=130, against=kanal_mit_wand())
    assert not r.collides and r.passed, r
    assert r.travelled_mm == 130.0
    assert r.first_contact_mm is None


# --------------------------------------------------------------------------- Grundverhalten

def test_freier_weg_und_clearance():
    a = bx('A', (10, 10, 10), moving=True)
    b = bx('B', (10, 10, 10), (40, 0, 0))
    frei = sweep(a, vector=(0, 1, 0), distance=20, against=b)
    assert frei.passed and frei.min_gap_mm > 0

    treffer = sweep(a, vector=(1, 0, 0), distance=50, against=b)
    assert treffer.collides and abs(treffer.first_contact_mm - 30.0) < 0.02

    # geforderte Luft verschiebt den Kontakt genau um clearance_mm nach vorn
    luft = sweep(a, vector=(1, 0, 0), distance=50, against=b, clearance_mm=2.0)
    assert luft.collides and abs(luft.first_contact_mm - 28.0) < 0.05


def test_ignore_pairs_und_nichts_gemessen():
    a = bx('A', (10, 10, 10), moving=True)
    b = bx('B', (10, 10, 10), (40, 0, 0))
    r = sweep(a, vector=(1, 0, 0), distance=50, against=b, ignore_pairs=[('B', 'A')])
    assert r.passed and not r.collides, r

    leer = sweep(a, vector=(1, 0, 0), distance=10, against=[])
    assert leer.nichts_gemessen and not leer.passed and isinstance(leer, SweepResult)
    # Absicht des Plugins: ein leeres Messergebnis färbt den Test rot. Hier ist die Leere der
    # Prüfgegenstand, deshalb wird der Vermerk nach der Zusicherung wieder abgeräumt.
    assert results.forget_empty()


def test_falsche_eingaben_fliegen_auf():
    a = bx('A', (10, 10, 10), moving=True)
    b = bx('B', (10, 10, 10), (40, 0, 0))
    with pytest.raises(ValueError):
        sweep(a, vector=(0, 0, 0), distance=10, against=b)
    with pytest.raises(ValueError):
        sweep(a, against=b)
    with pytest.raises(ValueError):
        sweep(a, vector=(1, 0, 0), distance=10, against=b, clearance_mm=1.0, allow_touch=True)


def test_anliegendes_teil_klemmt_sofort():
    """Ein eingebautes Teil liegt an seinen Nachbarn an -- der Kontakt steht also schon bei 0."""
    a = bx('A', (10, 10, 10), moving=True)
    auflage = bx('AUF', (10, 10, 10), (0, 0, -10))       # A liegt satt darauf
    sperre = bx('SPERRE', (10, 10, 10), (30, 0, 0))

    ohne = sweep(a, vector=(1, 0, 0), distance=50, against=[auflage, sperre])
    assert ohne.collides and ohne.first_contact_mm == 0.0 and ohne.pairs == [['A', 'AUF']]

    # Wer den nominalen Sitz kennt, nennt ihn beim Namen -- dann kommt die echte Sperre heraus.
    echt = sweep(a, vector=(1, 0, 0), distance=50, against=[auflage, sperre],
                 ignore_pairs=[('A', 'AUF')])
    assert echt.collides and abs(echt.first_contact_mm - 20.0) < 0.05, echt
    assert echt.pairs == [['A', 'SPERRE']]


def test_eindringtiefe_taugt_nicht_fuer_grosse_ebene_flaechen():
    """Bekannte Grenze von allow_touch, hier festgenagelt statt stillschweigend hingenommen.

    fcl misst auf BVH-Modellen keine echte Eindringtiefe, sondern die Überdeckung der beteiligten
    Dreieckspaare. Bei zwei großen, deckungsgleichen Planflächen ist das die Dreiecksausdehnung
    (hier 10 mm) statt 0 -- eine satte Auflage sieht damit aus wie tiefes Stecken. Auf fein
    tessellierten realen Teilen funktioniert das Maß (gemessen: 0,16 mm für den Bügelsitz), auf
    Quadern nicht. Nominale Sitze deshalb lieber über `ignore_pairs` benennen.
    """
    a = bx('A', (10, 10, 10), moving=True)
    auflage = bx('AUF', (10, 10, 10), (0, 0, -10))
    assert penetration_at(a.mesh, auflage.mesh, np.zeros(3)) == pytest.approx(10.0)

    mit = sweep(a, vector=(1, 0, 0), distance=50, against=[auflage], allow_touch=True)
    assert mit.collides and mit.first_contact_mm == 0.0        # nicht als Berührung erkannt
    assert mit.contacts[0]['depth_mm'] == pytest.approx(10.0)


# --------------------------------------------------------------------------- Maschinenkontext

@pytest.fixture(scope='module')
def r6d():
    if not R6D.exists():
        pytest.skip(f'{R6D} nicht vorhanden')
    return Machine.load(R6D)


def test_motion_hub_kommt_aus_der_maschine(r6d):
    sc = r6d.scene()
    r = sweep(sc.only('R55'), motion='hub', to=130, against=sc.only('R30'), machine=r6d)
    soll = r6d.frame('local').direction_to_world(np.array([0.0, 0.0, 1.0]))
    assert np.allclose(r.direction, soll / np.linalg.norm(soll), atol=1e-9)
    assert r.distance_mm == 130.0
    # R55 (alter Zugbügel) betätigt am Hubende den Endschalter-Hebel R30 -- nominal so gewollt.
    assert r.collides and r.pairs == [['R55', 'R30']], r


def test_motion_unbekannt(r6d):
    with pytest.raises(KeyError):
        sweep(r6d.scene().only('R55'), motion='gibtsnicht', to=1,
              against=r6d.scene().only('R30'), machine=r6d)


# --------------------------------------------------------------------------- montage.yaml

GUT = """
schema: pruefstand.montage/1
ersetzt: [X9]
schritte:
  - name: Erst der Sockel
    teil: P01
    bewegung: {frame: local, richtung: [0, 0, -1], weg: 20}
    gegen: fest
  - name: Dann der Bügel
    teil: P03
    bewegung: {frame: local, richtung: [0, -1, 0], weg: 40}
    gegen: [T05, T41L]
    bereits_montiert: [P01]
    nominale_kontakte: [[P03, T05]]
    beruehrung_erlaubt: true
    motionen: {hub: 100}
"""


def schreib(tmp_path, text):
    p = tmp_path / 'montage.yaml'
    p.write_text(text)
    return p


def test_lader_liest_schritte(tmp_path):
    s = load_assembly(schreib(tmp_path, GUT))
    assert [x.teil for x in s] == ['P01', 'P03']
    assert isinstance(s[0], Step)
    assert s[0].spaeter == ['P03'] and s[1].spaeter == []
    assert np.allclose(s[1].richtung, [0, -1, 0]) and s[1].weg == 40.0
    assert s[1].gegen == ['T05', 'T41L'] and s[1].beruehrung_erlaubt
    assert s[1].motionen == {'hub': 100.0}
    assert s[1].nominale_kontakte == [('P03', 'T05')]
    # Was später kommt und was ersetzt wird, ist im Schritt nicht da.
    assert s[0].nicht_vorhanden() == {'P01', 'P03', 'X9'}


@pytest.mark.parametrize('kaputt, muster', [
    ('schema: falsch/9\nschritte: [{name: a, teil: P1, bewegung: {richtung: [1,0,0], weg: 1}}]',
     'Schema'),
    ('schema: pruefstand.montage/1\nschritte: []', 'schritte'),
    ('schema: pruefstand.montage/1\nschritte: [{name: a, bewegung: {richtung: [1,0,0], weg: 1}}]',
     'teil'),
    ('schema: pruefstand.montage/1\nschritte: [{name: a, teil: P1}]', 'bewegung'),
    ('schema: pruefstand.montage/1\nschritte: [{name: a, teil: P1, bewegung: {richtung: [0,0,0], weg: 1}}]',
     'Nullvektor'),
    ('schema: pruefstand.montage/1\nschritte: [{name: a, teil: P1, bewegung: {richtung: [1,0,0], weg: 0}}]',
     'weg'),
    ('schema: pruefstand.montage/1\nschritte: [{name: a, teil: P1, bewegung: {richtung: [1,0,0], weg: 1}, gegen: garnix}]',
     'gegen'),
    ('schema: pruefstand.montage/1\nschritte: [{name: a, teil: P1, bewegung: {richtung: [1,0,0], weg: 1}, tippfehler: 1}]',
     'unbekannte'),
])
def test_lader_weist_muell_ab(tmp_path, kaputt, muster):
    with pytest.raises(MontageError, match=muster):
        load_assembly(schreib(tmp_path, kaputt))


def test_lader_prueft_die_reihenfolge(tmp_path):
    zwei = """
schema: pruefstand.montage/1
schritte:
  - {name: a, teil: P1, bewegung: {richtung: [1,0,0], weg: 1}}
  - {name: b, teil: P2, bewegung: {richtung: [1,0,0], weg: 1}, bereits_montiert: %s}
"""
    # P1 war vorher dran und muss genannt sein
    with pytest.raises(MontageError, match='vergisst'):
        load_assembly(schreib(tmp_path, zwei % '[]'))
    load_assembly(schreib(tmp_path, zwei % '[P1]'))
    # das eigene Teil darf nicht dastehen
    with pytest.raises(MontageError, match='eigenen'):
        load_assembly(schreib(tmp_path, zwei % '[P1, P2]'))
    # und nichts, was erst später kommt
    drei = zwei + '  - {name: c, teil: P3, bewegung: {richtung: [1,0,0], weg: 1}, bereits_montiert: [P1, P2]}\n'
    with pytest.raises(MontageError, match='später'):
        load_assembly(schreib(tmp_path, drei % '[P1, P3]'))


def test_lader_verbietet_doppelte_teile(tmp_path):
    doppelt = """
schema: pruefstand.montage/1
schritte:
  - {name: a, teil: P1, bewegung: {richtung: [1,0,0], weg: 1}}
  - {name: b, teil: P1, bewegung: {richtung: [1,0,0], weg: 1}, bereits_montiert: [P1]}
"""
    with pytest.raises(MontageError, match='zweimal'):
        load_assembly(schreib(tmp_path, doppelt))


def test_fehlende_datei(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_assembly(tmp_path / 'gibtsnicht.yaml')


# --------------------------------------------------------------------------- Einbauweg real

def test_einbauweg_zugbuegel(r6d):
    """Der Einbauweg des neuen Zugbügels P03, geprüft gegen den Bestand von diesem Augenblick."""
    yml = KLEMME / 'spec' / 'montage.yaml'
    step_datei = KLEMME / 'native' / 'belt-clamp-r1-native.step'
    if not yml.exists() or not step_datei.exists():
        pytest.skip('Riemenklemme nicht vorhanden')

    schritte = load_assembly(yml)
    assert [s.teil for s in schritte] == ['P03', 'R49', 'R74', 'T50']
    st = schritte[0]
    assert st.neue_teile(r6d) == []          # der erste Schritt bringt nichts Fremdes mit

    teil = load_step(step_datei, moving=True).find('P03')
    teil.key = 'P03'
    sc = r6d.scene(**st.motionen)
    gegen = sc.only(*st.against_keys(r6d))
    assert len(gegen) > 40, f'nur {len(gegen)} Gegenkörper -- da stimmt die Auswahl nicht'
    # Die Schrauben, die P03 halten, sind zu diesem Zeitpunkt noch nicht drin.
    assert not {'R49', 'R74'} & set(gegen.keys())

    t0 = time.perf_counter()
    r = sweep(teil, vector=st.richtung_welt(r6d), distance=st.weg_mm(r6d), against=gegen, at=sc,
              allow_touch=st.beruehrung_erlaubt, ignore_pairs=st.nominale_kontakte)

    dauer = time.perf_counter() - t0

    assert dauer < 60.0
    assert r.passed, (f'Einbauweg klemmt nach {r.travelled_mm:.2f} von {r.distance_mm} mm '
                      f'an {r.pairs}')
