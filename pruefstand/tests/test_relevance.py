"""Tests für `relevance()` und die Pflegedatei `spec/relevanz.yaml`."""
from __future__ import annotations

import numpy as np
import pytest
from build123d import Box, Location

from pruefstand import Body, Region
from pruefstand import results
from pruefstand.frame import Frame
from pruefstand.primitives import _relevance as _r
from pruefstand.primitives.relevance import RelevanceResult, relevance
from pruefstand.relevanz import (SCHEMA, Relevanz, TeilRelevanz, erklaert_from_dict,
                                 find_relevanz, load_relevanz, teil_from_dict)

# -- Prüflinge -----------------------------------------------------------


def platte(zipfel=None, key='P'):
    """Platte 100x20x5 auf zwei Auflagen, optional mit angesetztem Zipfel (L, B, H)."""
    s = Box(100, 20, 5)
    if zipfel is not None:
        L, B, H = zipfel
        s = s + Box(L, B, H).locate(Location((50 + L / 2 - 0.001, 0, 0)))
    return Body(key, key, solid=s)


def auflagen():
    return [Body('A', 'A', solid=Box(10, 20, 10).locate(Location((-45, 0, -7.5)))),
            Body('B', 'B', solid=Box(10, 20, 10).locate(Location((45, 0, -7.5))))]


# -- Voxelgitter ---------------------------------------------------------


def test_voxelize_trifft_das_volumen():
    g = _r.voxelize(Body('W', 'W', solid=Box(20, 10, 6)).mesh, 0.5)
    assert abs(g.occ.sum() * g.voxel_mm3 - 1200.0) / 1200.0 < 0.02


def test_voxelize_findet_die_hoehlung():
    hohl = Box(30, 30, 30) - Box(10, 10, 10)
    g = _r.voxelize(Body('H', 'H', solid=hohl).mesh, 1.0)
    mitte = g.occ[tuple((np.array(g.shape) // 2).tolist())]
    assert not mitte
    assert abs(g.occ.sum() * g.voxel_mm3 - 26000.0) / 26000.0 < 0.03


def test_grid_centers_und_region():
    g = _r.voxelize(Body('W', 'W', solid=Box(10, 10, 10)).mesh, 1.0)
    reg = Region.box(Frame.identity(), [-5, -5, 0], [5, 5, 5])
    m = g.contains_mask(reg) & g.occ
    assert 0 < m.sum() < g.occ.sum()


def test_aufloesung_muss_positiv_sein():
    with pytest.raises(ValueError, match='aufloesung_mm'):
        relevance(platte(), auflagen(), aufloesung_mm=0)


# -- Bohrungen -----------------------------------------------------------


def test_bores_findet_durchgangsloch_und_ignoriert_zapfen():
    from build123d import Cylinder

    s = Box(40, 40, 10) - Cylinder(radius=2, height=20)
    s = s + Cylinder(radius=3, height=20).locate(Location((15, 15, 0)))
    b = _r.bores(Body('X', 'X', solid=s).solid)
    assert [round(x['radius'], 2) for x in b] == [2.0]


# -- Grundfälle ----------------------------------------------------------


def test_gesunde_platte_ohne_befund():
    r = relevance(platte(), auflagen())
    assert isinstance(r, RelevanceResult)
    assert r.befunde == []
    assert r.fraglich_mm3 == 0.0
    assert r.anteil == 0.0
    assert r.level == 'ok'
    assert r.passed
    assert r.anker['kontakt'] == 2
    assert r.anker['kontakt_koerper'] == ['A', 'B']
    assert r.anker['quellen'] == 2


def test_zipfel_wird_gefunden_und_lokalisiert():
    r = relevance(platte((20, 20, 5)), auflagen())
    assert r.level == 'warnung'
    assert not r.passed
    assert len(r.befunde) == 1
    b = r.befunde[0]
    assert b['volumen_mm3'] > 1000.0
    assert b['schwerpunkt'][0] > 50.0          # sitzt im Zipfel, nicht auf der Platte
    lo, hi = b['bbox_mm']
    assert lo[0] > 45.0 and hi[0] <= 70.5
    assert b['max_abstand_mm'] > 10.0
    assert r.fraglich_mm3 + r.funktional_mm3 == pytest.approx(
        r.fraglich_mm3 / r.anteil, rel=1e-6)


def test_kleiner_zipfel_faellt_unter_min_volumen():
    gross = relevance(platte((8, 8, 5)), auflagen())
    assert gross.befunde                      # 320 mm3 wird gemeldet
    klein = relevance(platte((5, 5, 5)), auflagen())
    assert klein.befunde == []                # 125 mm3 ueberlebt die Oeffnung nicht
    assert klein.level == 'ok'


def test_min_volumen_filtert_nur_die_meldung():
    laut = relevance(platte((20, 20, 5)), auflagen(), min_volumen_mm3=1e9)
    assert laut.befunde == []
    assert laut.passed
    assert laut.fraglich_mm3 > 1000.0         # gemessen wird trotzdem


def test_lastpfad_haelt_die_rippe_zwischen_zwei_ankern_funktional():
    """Eine schmale Brücke zwischen zwei Auflagen, deren Mitte weit von beiden weg ist."""
    bruecke = Body('R', 'R', solid=Box(100, 8, 6))
    ctx = [Body('A', 'A', solid=Box(10, 8, 10).locate(Location((-45, 0, -8)))),
           Body('B', 'B', solid=Box(10, 8, 10).locate(Location((45, 0, -8))))]
    r = relevance(bruecke, ctx, r_anker=3.0)
    assert r.befunde == []
    assert r.fraglich_mm3 == 0.0


def test_ohne_anker_nichts_gemessen():
    r = relevance(platte(), [], aufloesung_mm=2.0)
    assert r.nichts_gemessen
    assert not r.passed                       # nichts gemessen heisst nicht bestanden
    assert 'Anker' in r.leer_grund
    assert r.befunde == []
    # Ein leeres Messergebnis faerbt den Test rot; hier ist die Leere der Pruefgegenstand.
    assert results.forget_empty()


def test_eine_einzige_ankerquelle_ist_zu_wenig():
    from build123d import Cylinder

    s = Box(60, 20, 6) - Cylinder(radius=1.6, height=20)
    r = relevance(Body('S', 'S', solid=s), [], aufloesung_mm=1.0)
    assert r.anker['bohrung'] == 1 and r.anker['kontakt'] == 0
    assert r.nichts_gemessen and not r.passed
    assert results.forget_empty()


def test_bohrungen_zaehlen_als_anker():
    from build123d import Cylinder

    s = Box(50, 20, 6)
    for x in (-20, 20):
        for y in (-6, 6):
            s -= Cylinder(radius=1.6, height=20).locate(Location((x, y, 0)))
    r = relevance(Body('S', 'S', solid=s), [], aufloesung_mm=1.0)
    assert not r.nichts_gemessen
    assert r.anker['bohrung'] == 4
    assert r.anker['kontakt'] == 0
    assert r.befunde == []                    # Lastpfade laufen ueber die vier Loecher


def test_erklaerter_bereich_entschaerft_den_befund():
    ctx = auflagen()
    laut = relevance(platte((20, 20, 5)), ctx)
    assert laut.befunde
    reg = Region.box(Frame.identity(), [48, -12, -4], [72, 12, 4])
    still = relevance(platte((20, 20, 5)), ctx, erklaert=[reg])
    assert still.befunde == []
    assert still.anker['erklaert'] == 1


def test_ignorierter_bereich_faellt_aus_der_messung():
    ctx = auflagen()
    teil = TeilRelevanz(
        key='P',
        erklaert=(erklaert_from_dict({'name': 'Beschriftung',
                                      'bereich': {'frame': 'world', 'von': [48, -12, -4],
                                                  'bis': [72, 12, 4]}}, 'test'),),
        ignorieren=('Beschriftung',))
    r = relevance(platte((20, 20, 5)), ctx, relevanz=teil)
    assert r.befunde == []
    assert teil.anker() == []
    assert [e.name for e in teil.ausgeschlossen()] == ['Beschriftung']


def test_relevanz_argument_wird_geprueft():
    with pytest.raises(TypeError, match='Relevanz oder TeilRelevanz'):
        relevance(platte(), auflagen(), relevanz='spec/relevanz.yaml')


def test_ergebnis_summary_und_dict():
    r = relevance(platte((20, 20, 5)), auflagen())
    d = r.as_dict()
    for k in ('funktional_mm3', 'fraglich_mm3', 'anteil', 'level', 'aufloesung_mm',
              'anker', 'befunde'):
        assert k in d
    assert isinstance(r.summary(), str) and r.summary()


# -- Pflegedatei ---------------------------------------------------------

GUT = f"""
schema: {SCHEMA}
teile:
  - key: T05
    erklaert:
      - name: Grifflippe
        bereich: {{frame: local, von: [-120, -10, -5], bis: [120, 0, 5]}}
        grund: Anfassen beim Einsetzen
      - name: Beschriftung
        bereich: {{frame: local, von: [-10, -10, 4], bis: [10, 10, 6]}}
    ignorieren: [Beschriftung]
"""


def schreib(tmp_path, text, name='relevanz.yaml'):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_loader_liest_die_gute_datei(tmp_path):
    rel = load_relevanz(schreib(tmp_path, GUT))
    assert isinstance(rel, Relevanz)
    assert rel.keys() == ['T05']
    t = rel.teil('T05')
    assert [e.name for e in t.anker()] == ['Grifflippe']
    assert [e.name for e in t.ausgeschlossen()] == ['Beschriftung']
    assert t.erklaert[0].grund == 'Anfassen beim Einsetzen'
    assert np.allclose(t.erklaert[0].von, [-120, -10, -5])
    assert rel.teil('gibtsnicht') is None
    assert len(rel) == 1


def test_erklaert_region_in_weltkoordinaten(tmp_path):
    t = load_relevanz(schreib(tmp_path, GUT)).teil('T05')
    reg = t.anker()[0].region(Frame.identity())
    assert bool(reg.contains(np.array([[0.0, -5.0, 0.0]]))[0])
    assert not bool(reg.contains(np.array([[0.0, 50.0, 0.0]]))[0])


@pytest.mark.parametrize('text, muster', [
    ('schema: falsch/9\nteile: [{key: A}]', 'Schema'),
    (f'schema: {SCHEMA}\n', '`teile` fehlt'),
    (f'schema: {SCHEMA}\nteile: []', '`teile` fehlt'),
    (f'schema: {SCHEMA}\nquatsch: 1\nteile: [{{key: A}}]', 'unbekannte Schlüssel'),
    (f'schema: {SCHEMA}\nteile: [{{name: A}}]', 'unbekannte Schlüssel'),
    (f'schema: {SCHEMA}\nteile: [{{key: A}}, {{key: A}}]', 'doppelter Teil-key'),
    (f'schema: {SCHEMA}\nteile: [{{key: A, ignorieren: [X]}}]', 'ignorieren'),
    (f'schema: {SCHEMA}\nteile: [{{key: A, erklaert: [{{bereich: {{von: [0,0,0], bis: [1,1,1]}}}}]}}]',
     '`name` fehlt'),
    (f'schema: {SCHEMA}\nteile: [{{key: A, erklaert: [{{name: N}}]}}]', '`bereich` fehlt'),
    (f'schema: {SCHEMA}\nteile: [{{key: A, erklaert: [{{name: N, bereich: {{von: [0,0,0]}}}}]}}]',
     '`bereich.bis` fehlt'),
    (f'schema: {SCHEMA}\nteile: [{{key: A, erklaert: [{{name: N, bereich: '
     f'{{von: [0,0,0], bis: [0,1,1]}}}}]}}]', 'leerer Quader'),
    (f'schema: {SCHEMA}\nteile: [{{key: A, erklaert: [{{name: N, bereich: '
     f'{{von: [0,0], bis: [1,1,1]}}}}]}}]', 'drei Zahlen'),
    (f'schema: {SCHEMA}\nteile: [{{key: A, erklaert: [{{name: N, bereich: '
     f'{{von: [0,0,0], bis: [1,1,1], quatsch: 1}}}}]}}]', 'unbekannte Schlüssel'),
    ('- 1\n- 2', 'Wurzel'),
])
def test_loader_weist_kaputte_dateien_ab(tmp_path, text, muster):
    with pytest.raises(ValueError, match=muster):
        load_relevanz(schreib(tmp_path, text))


def test_doppelte_namen_werden_abgewiesen():
    b = {'von': [0, 0, 0], 'bis': [1, 1, 1]}
    with pytest.raises(ValueError, match='doppelte Namen'):
        teil_from_dict({'key': 'A', 'erklaert': [{'name': 'N', 'bereich': b},
                                                 {'name': 'N', 'bereich': b}]})


def test_fehlende_datei_wirft():
    with pytest.raises(FileNotFoundError):
        load_relevanz('/gibt/es/nicht/relevanz.yaml')


def test_find_relevanz_ohne_datei(tmp_path):
    assert find_relevanz(tmp_path) is None


def test_find_relevanz_mit_datei(tmp_path):
    schreib(tmp_path, GUT)
    assert find_relevanz(tmp_path).keys() == ['T05']
