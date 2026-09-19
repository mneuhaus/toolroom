"""Prüfbudget und `status: not_built_yet`.

Zwei Antworten auf dieselbe Frage: **was hat dieser grüne Lauf eigentlich angesehen?**

Das Budget hängt an jedem Testeintrag und sagt, welches Primitiv welche Körper in
welcher Pose gemessen hat (`geprueft`), was es ausgelassen hat (`uebersprungen`) und
unter welchen Annahmen der Messwert gilt (`angenommen`). `status: not_built_yet` ist
die Gegenrichtung: eine Anforderung, zu der es noch keine Geometrie gibt, wird
ausdrücklich **unentschieden** statt stillschweigend grün.
"""
import pytest
from build123d import Box

from pruefstand import Body, gap, interface_ok, load_screws, overlap
from pruefstand.assembly import MontageError, load_assembly
from pruefstand.interface import interface_from_dict, load_interfaces
from pruefstand.primitives.access import access
from pruefstand.primitives.screw_chain import screw_chain
from pruefstand.pytest_plugin import _budget_kopf
from pruefstand.results import NICHT_GEBAUT, budget, forget_open, pruefe_bau_status
from pruefstand import context


def hier() -> dict:
    """Das Budget des gerade laufenden Tests."""
    return budget(context.test_id())


# -- Budget -----------------------------------------------------------------

def test_messung_schreibt_koerper_pose_und_urteil_ins_budget():
    a = Body('A', 'A', solid=Box(10, 10, 10))
    b = Body('B', 'B', solid=Box(10, 10, 10).translate((20, 0, 0)))
    gap(a, [b])
    eintraege = [e for e in hier()['geprueft'] if e['primitiv'] == 'gap']
    assert eintraege, hier()
    assert set(eintraege[-1]['koerper']) == {'A', 'B'}
    assert eintraege[-1]['urteil_auf'] == 'mesh'
    assert any(e.get('urteil_auf') == 'mesh' for e in hier()['angenommen'])


def test_netzkoerper_steht_als_uebersprungen_im_budget(tmp_path):
    """Ein Körper ohne BRep wird nicht exakt gerechnet -- das muss im Bericht stehen."""
    from build123d import export_stl
    from pruefstand import load_mesh
    p = tmp_path / 'w.stl'
    export_stl(Box(10, 10, 10).solid(), str(p))
    netz = load_mesh(p, key='M')
    overlap(netz, Body('B', 'B', solid=Box(10, 10, 10).translate((30, 0, 0))))
    # Eine Sammelzeile je Test, nicht eine je Messung -- sonst stünde derselbe
    # Netzkörper hundertmal im Bericht.
    uebersprungen = [u for u in hier()['uebersprungen'] if u.get('was') == 'brep']
    assert len(uebersprungen) == 1 and uebersprungen[0]['keys'] == ['M'], hier()
    assert hier()['koerper'] == {'B': True, 'M': False}


def test_leeres_fenster_steht_im_budget():
    from pruefstand import Frame, Region
    from pruefstand.results import forget_empty
    a = Body('A', 'A', solid=Box(10, 10, 10))
    b = Body('B', 'B', solid=Box(10, 10, 10).translate((20, 0, 0)))
    weit = Region.box(Frame.identity(), (500, 500, 500), (510, 510, 510))
    gap(a, [b], within=weit)
    assert any(u.get('was') == 'fenster' for u in hier()['uebersprungen']), hier()
    assert forget_empty()


def test_budget_kopf_summiert_einen_lauf():
    kopf = _budget_kopf({
        'a::t1': {'budget': {'geprueft': [{'primitiv': 'gap', 'koerper': ['T01', 'H608']}],
                             'koerper': {'T01': True, 'H608': True, 'R18': False},
                             'uebersprungen': [{'was': 'brep', 'key': 'R18'}],
                             'angenommen': [{'urteil_auf': 'mesh'}]}},
        'a::t2': {'budget': {'geprueft': [{'primitiv': 'absatz', 'koerper': ['T01']}],
                             'koerper': {'T01': True},
                             'uebersprungen': [], 'angenommen': []}},
    })
    assert kopf['geprueft'] == 2 and kopf['angenommen'] == 1
    assert kopf['koerper'] == ['H608', 'R18', 'T01']
    assert kopf['ohne_brep'] == ['R18']
    assert kopf['uebersprungen_nach_art'] == {'brep': 1}


def test_budget_landet_im_json(pytester):
    """Der Bericht trägt je Test ein Budget und in der Wurzel die Summe des Laufs."""
    import json
    pytester.makefile('.yaml', pruefstand='review: review\n')
    pytester.makepyfile("""
        from build123d import Box
        from pruefstand import Body, gap

        def test_messen():
            a = Body('A', 'A', solid=Box(10, 10, 10))
            b = Body('B', 'B', solid=Box(10, 10, 10).translate((20, 0, 0)))
            assert gap(a, [b]).min_mm > 5
    """)
    r = pytester.runpytest('-q')
    assert r.ret == 0, r.outlines[-5:]
    daten = json.loads((pytester.path / 'review' / 'pruefstand.json').read_text())
    assert daten['budget']['geprueft'] >= 1
    assert 'A' in daten['budget']['koerper'] and 'B' in daten['budget']['koerper']
    # Der innere Lauf teilt sich den Prozess mit dem äußeren und sieht dessen
    # Testeinträge mit -- der eigene wird deshalb am Namen gesucht, nicht am Index.
    meiner = [t for t in daten['tests'] if t['nodeid'].endswith('test_messen')]
    assert meiner and meiner[0]['budget']['geprueft'][0]['primitiv'] == 'gap'


# -- status: not_built_yet --------------------------------------------------

def test_status_nimmt_nur_den_einen_wert():
    assert pruefe_bau_status(None, 'x') == ''
    assert pruefe_bau_status(NICHT_GEBAUT, 'x') == NICHT_GEBAUT
    with pytest.raises(ValueError, match='status'):
        pruefe_bau_status('geplant', 'x')


def test_schraube_mit_status(tmp_path):
    p = tmp_path / 'schrauben.yaml'
    p.write_text("""schema: pruefstand.schrauben/1
schrauben:
  - {id: s1, norm: M3x12, kopf: senkkopf, frame: world, punkt: [0,0,0], richtung: [1,0,0],
     status: not_built_yet}
""")
    s = load_screws(p)[0]
    assert s.nicht_gebaut
    # Beide Schraubenprüfungen fassen keine Geometrie an und urteilen nicht.
    for r in (screw_chain(s, []), access(s, [])):
        assert r.unentschieden and 'not_built_yet' in r.offen_grund
        assert not r.passed
    assert len(forget_open()) == 2


def test_schnittstelle_mit_status_wird_unentschieden():
    iface = interface_from_dict({'id': 'x', 'kind': 'pin', 'body': 'P', 'axis': [1, 0, 0],
                                 'origin': [0, 0, 0], 'radius': 4.0, 'status': NICHT_GEBAUT})
    assert iface.nicht_gebaut
    r = interface_ok(iface, [Body('P', 'P', solid=Box(10, 10, 10))])
    assert r.unentschieden and not r.passed
    assert 'not_built_yet' in r.offen_grund
    assert forget_open()


def test_schnittstellendatei_mit_status(tmp_path):
    p = tmp_path / 'schnittstellen.yaml'
    p.write_text("""schema: pruefstand.schnittstellen/1
schnittstellen:
  - {id: x, kind: pin, body: P, axis: [1,0,0], origin: [0,0,0], radius: 4,
     status: not_built_yet}
""")
    assert load_interfaces(p)[0].nicht_gebaut


def test_montageschritt_mit_status(tmp_path):
    p = tmp_path / 'montage.yaml'
    p.write_text("""schema: pruefstand.montage/1
schritte:
  - name: kommt noch
    teil: P99
    bewegung: {richtung: [0, 1, 0], weg: 10}
    status: not_built_yet
""")
    assert load_assembly(p)[0].nicht_gebaut


def test_falscher_status_wird_abgewiesen(tmp_path):
    p = tmp_path / 'montage.yaml'
    p.write_text("""schema: pruefstand.montage/1
schritte:
  - name: a
    teil: P1
    bewegung: {richtung: [0, 1, 0], weg: 10}
    status: irgendwas
""")
    with pytest.raises(MontageError, match='status'):
        load_assembly(p)
