"""Stabilitätsindex: exakte Sollwerte synthetisch + die vier Probestäbe.

Die Schwellen in `KALIBRIERUNG` sind nicht geeicht (die Stäbe sind gedruckt-
bereit, aber noch nicht gebrochen). Die Tests prüfen deshalb die *Rechnung* und
die Anker-Normierung, nicht die Richtigkeit der Schwellenwerte.
"""
import math
from pathlib import Path

import pytest
from build123d import Box, Cylinder, Pos
from shapely.geometry import box as sbox

from pruefstand import Body, results
from pruefstand.body import load_mesh
from pruefstand.primitives.stability import (KALIBRIERUNG, anker_mm2, stability,
                                             wirksamer_querschnitt)
from pruefstand.printing import Profil

PROBESTAEBE = Path(__file__).resolve().parents[1] / 'probestaebe/var/print/parts_posed'


def koerper(key, solid):
    return Body(key, key, solid=solid)


def stab(name):
    return load_mesh(PROBESTAEBE / f'{name}-posed.stl')


# ------------------------------------------------------ wirksamer Schnitt ----
def test_wirksamer_querschnitt_quadrat_exakt():
    """20x20 mit 3 Wänden à 0,42 mm und 25 % Infill.

    Kern 17,48² = 305,5504 mm², Schale 400 − 305,5504 = 94,4496 mm²,
    wirksam = 94,4496 + 0,25 · 305,5504 = 170,8372 mm².
    """
    assert wirksamer_querschnitt(sbox(-10, -10, 10, 10), Profil()) == pytest.approx(170.8372, abs=1e-3)


def test_wirksamer_querschnitt_voll_bei_infill_1():
    assert wirksamer_querschnitt(sbox(0, 0, 20, 20), Profil(infill=1.0)) == pytest.approx(400.0, abs=1e-3)


def test_anker_ist_der_senkrechte_d10_rundstab():
    """Ø10, 3 Wände, 25 % Infill: Kern Ø7,48 -> 45,58 mm² wirksam."""
    assert anker_mm2() == pytest.approx(45.582, abs=0.01)


# ---------------------------------------------------------------- cos²θ ----
@pytest.mark.parametrize('richtung,cos2', [((1, 0, 0), 1.0), ((1, 0, 1), 0.5), ((0, 0, 1), 0.0)])
def test_cos2_theta(richtung, cos2):
    """θ = Winkel zwischen Last und Schichtebene. Quer = 1, 45° = 0,5, senkrecht = 0."""
    r = stability(koerper('Q', Box(20, 20, 40)), ((0, 0, 0), (0, 0, 1)), richtung)
    assert r.cos2 == pytest.approx(cos2, abs=1e-9)
    assert r.theta_deg == pytest.approx(math.degrees(math.acos(math.sqrt(cos2))), abs=1e-6)


def test_last_senkrecht_zur_fuge_ist_index_null():
    r = stability(koerper('Q', Box(20, 20, 40)), ((0, 0, 0), (0, 0, 1)), (0, 0, 1))
    assert r.index == pytest.approx(0.0, abs=1e-12)
    assert r.level == 'fehler' and not r.passed


# ------------------------------------------------------------ Kerbe/Fuge ----
def test_kerbe_und_fuge_am_absatz():
    """Fuß 30x30x8 mit 10x10-Stab: am Absatz Kerbe und Schichtfuge.

    Schnitt = dünne Seite 10x10 = 100 mm², wirksam
    100 − 7,48² + 0,25 · 7,48² = 58,0369 mm².
    """
    k = koerper('K', Pos(0, 0, 4) * Box(30, 30, 8) + Pos(0, 0, 28) * Box(10, 10, 40))
    r = stability(k, ((0, 0, 8), (0, 0, 1)), (1, 0, 0))
    assert r.area_mm2 == pytest.approx(100.0, abs=1e-6)
    assert r.effective_mm2 == pytest.approx(58.0369, abs=1e-3)
    assert r.notch is True and r.seam is True
    # Kerbe und Fuge stecken auch im Anker-Nenner (S1 hat beides), sie kürzen sich
    # hier also heraus: Index = wirksamer Querschnitt / Anker.
    assert r.index == pytest.approx(58.0369 / anker_mm2(), rel=1e-4)


def test_ohne_absatz_keine_kerbe():
    r = stability(koerper('Q', Box(20, 20, 40)), ((0, 0, 0), (0, 0, 1)), (1, 0, 0))
    assert r.notch is False


def test_fuge_nur_parallel_zur_schichtebene():
    """Senkrechte Schnittebene ist keine Schichtfuge."""
    r = stability(koerper('Q', Box(20, 20, 40)), ((0, 0, 0), (1, 0, 0)), (0, 1, 0))
    assert r.seam is False


def test_profil_beeinflusst_den_wirksamen_querschnitt():
    """Mehr Wandlinien = mehr tragender Querschnitt (der Anker verschiebt sich mit,
    deshalb ist der Index selbst nicht monoton in `waende` — das ist gewollt: der
    Index vergleicht immer gegen denselben Stab im selben Profil)."""
    k = koerper('Q', Box(20, 20, 40))
    duenn = stability(k, ((0, 0, 0), (0, 0, 1)), (1, 0, 0), profile=Profil(waende=2))
    dick = stability(k, ((0, 0, 0), (0, 0, 1)), (1, 0, 0), profile=Profil(waende=5))
    assert dick.effective_mm2 > duenn.effective_mm2
    assert dick.anker_mm2 > duenn.anker_mm2


# ------------------------------------------------------------- leer/Kalib ----
def test_schnittebene_verfehlt_koerper_ist_nichts_gemessen():
    r = stability(koerper('Q', Box(20, 20, 40)), ((0, 0, 500), (0, 0, 1)), (1, 0, 0))
    assert r.nichts_gemessen and not r.passed
    assert results.forget_empty(), 'Leer-Markierung muss gesetzt worden sein'


def test_kalibrierung_ist_als_ungeeicht_markiert():
    """Solange die Stäbe nicht gebrochen sind, darf niemand die Schwellen glauben."""
    assert KALIBRIERUNG['geeicht'] is False
    r = stability(koerper('Q', Box(20, 20, 40)), ((0, 0, 0), (0, 0, 1)), (1, 0, 0))
    assert r.geeicht is False


# ------------------------------------------------------------ Probestäbe ----
@pytest.mark.skipif(not PROBESTAEBE.exists(), reason='Probestäbe nicht gebaut')
def test_s1_ist_der_anker_genau_eins():
    """Ø10 senkrecht am Fußabsatz = definitionsgemäß Index 1,0 (K.o.-Fall)."""
    r = stability(stab('S1_d10_senkrecht'), ((0, 0, 8.0), (0, 0, 1)), (1, 0, 0))
    assert r.index == pytest.approx(1.0, abs=0.01), r
    assert r.notch and r.seam and r.level == 'fehler'


@pytest.mark.skipif(not PROBESTAEBE.exists(), reason='Probestäbe nicht gebaut')
@pytest.mark.parametrize('name,punkt,normale,index', [
    ('S1_d10_senkrecht', (0, 0, 8.0), (0, 0, 1), 1.000),
    ('S2_d20_senkrecht', (0, 0, 8.0), (0, 0, 1), 2.943),
    ('S3_d10_45grad', (0, 0, 20.0), (0, 0, 1), 1.649),
    ('S4_d10_liegend', (0, 140.0, 0), (0, 1, 0), 1.382),
])
def test_probestaebe_index(name, punkt, normale, index):
    r = stability(stab(name), (punkt, normale), (1, 0, 0))
    assert r.index == pytest.approx(index, abs=0.01), r


@pytest.mark.skipif(not PROBESTAEBE.exists(), reason='Probestäbe nicht gebaut')
def test_s2_traegt_mehr_als_s1():
    s1 = stability(stab('S1_d10_senkrecht'), ((0, 0, 8.0), (0, 0, 1)), (1, 0, 0))
    s2 = stability(stab('S2_d20_senkrecht'), ((0, 0, 8.0), (0, 0, 1)), (1, 0, 0))
    assert s2.index > s1.index and s2.area_mm2 == pytest.approx(4 * s1.area_mm2, rel=0.01)


@pytest.mark.skipif(not PROBESTAEBE.exists(), reason='Probestäbe nicht gebaut')
def test_s4_hat_keine_schichtfuge_im_lastschnitt():
    """Liegend gedruckt liegt der Wurzelschnitt quer zu den Schichten — keine Fuge."""
    r = stability(stab('S4_d10_liegend'), ((0, 140.0, 0), (0, 1, 0)), (1, 0, 0))
    assert r.seam is False and r.notch is True
