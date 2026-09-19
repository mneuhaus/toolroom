"""Tests für den HTML-Bericht (`pruefstand.report`).

Die Tests bauen einen kleinen Bericht samt Projektordner im tmp_path nach:

    <projekt>/var/review/pruefstand.json
    <projekt>/var/review/A.stl        (Prüfteil-Geometrie, wie body.Body.mesh sie ablegt)

Damit läuft der ganze Weg (JSON lesen -> Klartext -> Geometrie -> eine HTML-Datei)
ohne Onshape und ohne Netz.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import numpy as np
import pytest

from pruefstand.report import build_report
from pruefstand.report import geometry, model


def _wuerfel_stl(pfad: Path, mitte=(0, 0, 0), kante=10.0) -> None:
    trimesh = pytest.importorskip('trimesh')
    m = trimesh.creation.box(extents=(kante, kante, kante))
    m.apply_translation(np.asarray(mitte, dtype=float))
    m.export(str(pfad))


@pytest.fixture
def projekt(tmp_path: Path) -> Path:
    """Projektordner mit Bericht-JSON und zwei Prüfteil-STLs."""
    review = tmp_path / 'proj' / 'var' / 'review'
    review.mkdir(parents=True)
    _wuerfel_stl(review / 'A.stl', (0, 0, 0))
    _wuerfel_stl(review / 'B.stl', (10.5, 0, 0))
    bericht = {
        'erzeugt': '2026-09-17 19:00:00',
        'tests': [
            {'nodeid': 'spec/test_x.py::test_spalt', 'outcome': 'passed', 'dauer_s': 0.12,
             'messwerte': [{'primitive': 'gap', 'min_mm': 0.5, 'pair': ['A', 'B'],
                            'penetrating': False, 'per_body': {'B': 0.5},
                            'point_a': [5.0, 0.0, 0.0], 'point_b': [5.5, 0.0, 0.0]}]},
            {'nodeid': 'spec/test_x.py::test_durchdringung', 'outcome': 'failed', 'dauer_s': 0.34,
             'messwerte': [{'primitive': 'overlap', 'volume_mm3': 17.37, 'exact': True,
                            'collides': True, 'contacts': 0, 'touching': False,
                            'pairs': [['A', 'B', 17.37, True]]}]},
            {'nodeid': 'spec/test_x.py::test_abdeckung', 'outcome': 'xfailed', 'dauer_s': 0.01,
             'messwerte': [{'primitive': 'coverage', 'total': 100, 'covered': 98,
                            'open': 2, 'fraction': 0.98}]},
        ],
    }
    (review / 'pruefstand.json').write_text(json.dumps(bericht))
    return tmp_path / 'proj'


# -- Klartext -----------------------------------------------------------------

def test_masse_deutsch_formatiert():
    assert model.mm(1.0) == '1,000 mm'
    assert model.mm3(17.371) == '17,37 mm³'
    assert model.prozent(0.98) == '98,0 %'
    assert model.mm(float('inf')) == 'unendlich'
    assert model.mm(None) == '–'


def test_safe_key_wie_body_modul():
    from pruefstand.body import _safe
    for name in ('P03 R6d-C2 wide/pull [M]', 'REF_H10_M3x16', 'ä ö ü'):
        assert model.safe_key(name) == _safe(name)


def test_gap_wird_zu_klartext_mit_marke(projekt: Path):
    b = model.lade(projekt / 'var' / 'review' / 'pruefstand.json')
    w = b.tests[0].messwerte[0]
    assert w.titel == 'Spalt 0,500 mm'
    assert ('Kleinster Abstand', '0,500 mm') in w.zeilen
    assert w.koerper == ['A', 'B']
    assert w.marker['art'] == 'strecke'
    assert w.marker['label'] == '0,500 mm'


def test_overlap_ist_rot_und_nennt_die_naeherung(projekt: Path):
    b = model.lade(projekt / 'var' / 'review' / 'pruefstand.json')
    w = b.tests[1].messwerte[0]
    assert w.schwere == 'fehler'
    assert w.marker['art'] == 'ueberschneidung'
    assert 'Hüllquader' in w.hinweis


def test_coverage_nennt_die_fehlenden_koordinaten(projekt: Path):
    b = model.lade(projekt / 'var' / 'review' / 'pruefstand.json')
    w = b.tests[2].messwerte[0]
    assert w.titel.startswith('Abdeckung 98,0 %')
    assert w.marker is None
    assert 'Koordinaten' in w.hinweis


def test_ampel_zaehlt_ausgaenge(projekt: Path):
    b = model.lade(projekt / 'var' / 'review' / 'pruefstand.json')
    assert b.zaehlung() == {'passed': 1, 'failed': 1, 'xfailed': 1}
    assert b.projekt == 'proj'
    assert b.alle_koerper() == ['A', 'B']


# -- Geometrie ----------------------------------------------------------------

def test_reduziere_dampft_ein():
    trimesh = pytest.importorskip('trimesh')
    kugel = trimesh.creation.icosphere(subdivisions=4)
    v, f = np.asarray(kugel.vertices), np.asarray(kugel.faces)
    nv, nf = geometry.reduziere(v, f, 200)
    assert len(nf) < len(f)
    assert nf.max() < len(nv)
    # unter dem Budget bleibt die Geometrie unangetastet
    assert geometry.reduziere(v, f, len(f) + 1)[1] is f


def test_payload_quantisierung_bleibt_unter_einem_mikrometer(projekt: Path):
    szene = geometry.baue_szene(projekt / 'var' / 'review' / 'pruefstand.json', projekt, ['A'])
    k = szene.koerper[0]
    p = geometry.payload(k)
    q = np.frombuffer(base64.b64decode(p['pos']), dtype=np.int16).reshape(-1, 3).astype(float)
    zurueck = (q + 32767.0) / 65534.0 * np.asarray(p['qspan']) + np.asarray(p['qlo'])
    assert np.abs(zurueck - np.asarray(k.mesh[0])).max() < 1e-3
    assert p['idx16'] is True


def test_szene_findet_pruefteile_und_meldet_fehlende(projekt: Path):
    szene = geometry.baue_szene(projekt / 'var' / 'review' / 'pruefstand.json', projekt,
                                ['A', 'B', 'gibtsnicht'])
    assert sorted(k.key for k in szene.koerper) == ['A', 'B']
    assert all(k.quelle == 'prüfteil' for k in szene.koerper)
    assert any('gibtsnicht' in w for w in szene.warnungen)


def test_huell_schnitt():
    a = geometry.Koerper(key='A', name='A', bounds=[[0, 0, 0], [10, 10, 10]])
    b = geometry.Koerper(key='B', name='B', bounds=[[8, 0, 0], [20, 10, 10]])
    box = geometry.huell_schnitt(a, b)
    assert box['genau'] is True
    assert box['min'][0] == pytest.approx(8.0) and box['max'][0] == pytest.approx(10.0)
    # ohne echten Überlapp bleibt eine kleine Behelfsmarke
    weit = geometry.Koerper(key='C', name='C', bounds=[[100, 100, 100], [110, 110, 110]])
    assert geometry.huell_schnitt(a, weit)['genau'] is False
    assert geometry.huell_schnitt(a, None) is None


# -- Ganze Seite --------------------------------------------------------------

def test_build_report_erzeugt_eine_offline_datei(projekt: Path):
    js = projekt / 'var' / 'review' / 'pruefstand.json'
    out = build_report(js)
    assert out == js.with_suffix('.html')
    text = out.read_text(encoding='utf-8')
    # keine externen Quellen: alles steckt in der Datei
    assert not re.search(r'<script[^>]+src=', text)
    assert not re.search(r'<(link|img)[^>]+(href|src)="(?!data:)', text)
    assert 'THREE' in text and 'OrbitControls' in text
    # Daten eingebettet und lesbar
    m = re.search(r'<script type="application/json" id="daten">(.*?)</script>', text, re.S)
    d = json.loads(m.group(1))
    assert len(d['tests']) == 3
    assert [k['key'] for k in d['koerper']] == ['A', 'B']
    assert d['tests'][1]['messwerte'][0]['marker']['art'] == 'kaesten'
    assert d['kopf']['projekt'] == 'proj'


def test_build_report_mit_eigenem_ziel(projekt: Path, tmp_path: Path):
    ziel = tmp_path / 'raus' / 'bericht.html'
    out = build_report(projekt / 'var' / 'review' / 'pruefstand.json', ziel)
    assert out == ziel and ziel.exists()
    assert ziel.stat().st_size > 100_000        # three.js ist mit drin


def test_cli(projekt: Path, capsys):
    from pruefstand.report.__main__ import main
    ziel = projekt / 'var' / 'review' / 'cli.html'
    assert main([str(projekt / 'var' / 'review' / 'pruefstand.json'), '-o', str(ziel)]) == 0
    assert 'KiB' in capsys.readouterr().out
    assert ziel.exists()


def test_kontaktpunkte_stehen_im_ergebnis():
    """„Kollidiert" schickt niemanden an die richtige Stelle, ein Ort schon."""
    from conftest import box
    from pruefstand import Body, overlap
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), (8, 0, 0))

    exakt = overlap(a, b)
    assert exakt.exact and exakt.collides
    assert len(exakt.contact_points) == 1
    assert exakt.contact_points[0][0] == pytest.approx(4.0, abs=1e-3), 'Mitte der 2-mm-Überdeckung'
    assert exakt.as_dict()['contact_points']

    ueber_netz = overlap(Body('A', 'A', mesh=a.mesh), Body('B', 'B', mesh=b.mesh))
    assert not ueber_netz.exact and ueber_netz.collides
    assert ueber_netz.contact_points, 'auch der Netzweg muss den Ort nennen'
    assert all(len(p) == 3 for p in ueber_netz.contact_points)


def test_ohne_kollision_gibt_es_keine_kontaktpunkte():
    from conftest import box
    from pruefstand import overlap
    r = overlap(box('A', (10, 10, 10)), box('B', (10, 10, 10), (50, 0, 0)))
    assert r.contact_points == []
