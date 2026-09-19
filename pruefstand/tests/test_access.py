"""access(): kommt der Schrauber an den Kopf?

Hülle vom Kopf nach außen: Bit Ø5,7 (M3), Schaft Ø4,8 x 112, Griff Ø18 x 55.
"""
import numpy as np
import pytest
from build123d import Box, Cylinder, Location

from pruefstand import Body, Machine, load_step, results
from pruefstand.primitives.access import AccessResult, Tool, access
from pruefstand.screws import Screw, screws_by_id, load_screws
from test_screw_chain import BELT_CLAMP, R6D, platte, schraube


def wand(key, z_unten, dicke=10.0, loch_d=0.0, breite=40.0):
    """Platte quer über der Achse, optional mit Loch auf der Achse."""
    s = Box(breite, breite, dicke).locate(Location((0, 0, z_unten + dicke / 2)))
    if loch_d > 0:
        s = s - Cylinder(loch_d / 2, dicke * 2).locate(Location((0, 0, z_unten + dicke / 2)))
    return Body(key, key, solid=s)


@pytest.fixture
def verschraubung():
    return [platte('A', 5.0, 0.0, 3.4), platte('B', 15.0, -5.0, 2.62)]


# -- Werkzeug ------------------------------------------------------------

def test_werkzeug_masse():
    t = Tool()
    assert t.bit(3.0) == 5.7 and t.bit(5.0) == 8.5
    assert abs(t.total_mm - (0.12 + 25 + 112 + 55)) < 1e-9
    segs = t.segments(3.0)
    assert [round(d, 2) for _, _, d in segs] == [5.7, 4.8, 18.0]
    assert abs(segs[0][0] - 0.12) < 1e-9 and abs(segs[-1][1] - t.total_mm) < 1e-9


def test_unbekannte_groesse_wird_gemeldet():
    with pytest.raises(ValueError, match='Bit-Durchmesser'):
        Tool().bit(4.0)


# -- freier Zugang -------------------------------------------------------

def test_freier_zugang(verschraubung):
    r = access(schraube(), verschraubung)
    assert isinstance(r, AccessResult) and bool(r) and r.free
    assert r.blocked_by == []
    assert abs(r.reach_mm - r.envelope_mm) < 1e-6
    # Die Hülle startet 0,12 mm über der Kopfauflage -- das ist der engste Abstand.
    assert abs(r.min_clearance_mm - 0.12) < 0.02, r.min_clearance_mm


def test_wand_blockiert_und_reach_zeigt_wo(verschraubung):
    r = access(schraube(), verschraubung + [wand('Wand', 47.5)])
    assert not r.free and not r.passed and r.blocked_by == ['Wand']
    assert abs(r.reach_mm - 47.5) < 0.2, r.reach_mm
    assert r.min_clearance_mm == 0.0


def test_kurzes_werkzeug_kommt_unter_der_wand_durch(verschraubung):
    kurz = Tool(bit_len_mm=10.0, shaft_len_mm=20.0, grip_len_mm=10.0)
    r = access(schraube(), verschraubung + [wand('Wand', 47.5)], tool=kurz)
    assert bool(r) and r.free and abs(r.envelope_mm - 40.12) < 1e-9


def test_gestufte_huelle_bit_passt_nicht_durch_oeffnung(verschraubung):
    """Ø5 Loch über dem Kopf: der Ø5,7-Bit bleibt hängen, ein Ø4-Bit kommt durch."""
    szene = verschraubung + [wand('Deckel', 10.0, dicke=5.0, loch_d=5.0)]
    assert not access(schraube(), szene).free
    assert access(schraube(), szene, tool=Tool(bit_d_mm=4.0)).free


def test_nichts_gemessen_ist_nicht_bestanden():
    r = access(schraube(), [])
    assert not r.passed and r.nichts_gemessen and r.checked == 0
    assert len(results.forget_empty()) == 1


def test_eigener_schraubenkoerper_blockiert_nicht(verschraubung):
    bolzen = Body('Schraube', 'Schraube', solid=Cylinder(1.5, 16).locate(Location((0, 0, -8))))
    r = access(schraube(), verschraubung + [bolzen])
    assert r.free and 'Schraube' not in r.blocked_by


# -- echter Fall: Riemenklemme R1 in der Maschine -----------------------

@pytest.mark.skipif(not __import__('pathlib').Path(BELT_CLAMP).exists(),
                    reason='step-feeder/rocking-photo-tray-r6d-belt-clamp-r1 nicht vorhanden')
def test_echte_riemenklemme_zugang():
    """Die beiden unteren Schrauben sind frei; die oberen laufen nach 92-94 mm in den
    Antriebskern P14 (R62) -- gemessen, nicht geschätzt."""
    s = screws_by_id(load_screws(f'{BELT_CLAMP}/spec/schrauben.yaml'))
    m = Machine.load(f'{R6D}/machine/machine.json')
    parts = load_step(f'{BELT_CLAMP}/native/belt-clamp-r1-native.step')
    # die alten P03/Backen/Schrauben/Riemen ersetzt die Klemme R1 (vgl. spec/test_belt_clamp.py)
    ersetzt = ['R55', 'R15', 'R06', 'R11', 'R01', 'R05', 'R29', 'R51']
    szene = m.scene().without(*ersetzt)
    bodies = list(szene.bodies) + list(parts)

    unten = access(s['M3x16-1'], bodies, at=szene, frame=m)
    assert unten.free and bool(unten), unten.blocked_by
    assert abs(unten.reach_mm - unten.envelope_mm) < 1e-6

    oben = access(s['M3x16-3'], bodies, at=szene, frame=m)
    assert not oben.free and oben.blocked_by == ['R62'], oben.blocked_by
    assert 90.0 < oben.reach_mm < 96.0, oben.reach_mm
