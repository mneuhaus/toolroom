"""Ein gescheitertes Messverfahren darf nie wie ein Messwert aussehen.

Der gefährlichste Zustand eines Prüfwerkzeugs ist nicht der falsche Messwert, sondern
der erfundene: ein Boolean, den der Kern verweigert hat, als „Volumen 0,0 mm³" -- das
liest sich als „keine Überschneidung", und das hat niemand gemessen.
"""
import pytest

from pruefstand import Frame, overlap, same_as
from pruefstand.region import Region
from pruefstand.results import KernelFehler, forget_open, forget_technical

from conftest import box


class _SturerKern:
    """Hüllt einen echten Solid und lässt nur die Booleans scheitern.

    Alles andere wird durchgereicht, damit das Netz und die Hüllquader stimmen --
    geprüft wird der Kernelausfall, nicht ein kaputtes Testobjekt.
    """

    def __init__(self, solid):
        self._s = solid

    def __getattr__(self, name):
        return getattr(self._s, name)

    def intersect(self, other):
        raise RuntimeError('BOPAlgo: kaputt')

    def cut(self, other):
        raise RuntimeError('BOPAlgo: kaputt')


def test_gescheiterter_schnitt_ist_kein_leeres_volumen():
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), at=(5, 0, 0))
    a.solid = _SturerKern(a.solid)
    r = overlap(a, b)
    assert r.technischer_fehler, 'gescheiterter Boolean muss als technischer Fehler gelten'
    assert not r.passed, 'ohne Verfahren gibt es kein Urteil'
    assert 'Schnitt gescheitert' in r.fehler_grund
    assert forget_technical(), 'der Lauf muss die Markierung sehen, die den Test rot macht'


def test_overlap_meldet_sonst_kein_technisches_problem():
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), at=(50, 0, 0))
    r = overlap(a, b)
    assert not r.technischer_fehler
    assert r.passed
    assert r.urteil_auf == 'brep'


def test_gescheiterte_differenz_meldet_nicht_unveraendert():
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10))
    a.solid = _SturerKern(a.solid)
    region = Region.box(Frame.identity(), (-20, -20, -20), (20, 20, 20))
    r = same_as(a, b, region)
    assert r.technischer_fehler
    assert not r.passed
    assert r.diff_mm3 is None, 'kein erfundenes Differenzvolumen aus einem gescheiterten Schnitt'
    assert forget_technical()


def test_same_as_urteilt_auf_mesh_auch_wenn_brep_rechnet():
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10))
    region = Region.box(Frame.identity(), (-20, -20, -20), (20, 20, 20))
    r = same_as(a, b, region, max_deviation_mm=0.01)
    assert r.exact, 'das Differenzvolumen kommt aus dem BRep'
    assert r.urteil_auf == 'mesh', 'das Urteil kommt aus der Abtastung -- das muss dranstehen'


def test_cut_wirft_statt_none_zu_liefern():
    from pruefstand.primitives.same_as import _cut
    with pytest.raises(KernelFehler):
        _cut(_SturerKern(box('X', (1, 1, 1)).solid), box('Y', (1, 1, 1)).solid)


def test_technischer_fehler_macht_den_lauf_rot(pytester_setup):
    """Ein Test, der den Fehler nicht selbst behandelt, muss rot werden -- nicht grün."""
    ergebnis = pytester_setup.runpytest('-q')
    ergebnis.assert_outcomes(failed=1)
    ergebnis.stdout.fnmatch_lines(['*technischer Fehler*'])


@pytest.fixture
def pytester_setup(pytester):
    pytester.makeconftest('''
import sys, pathlib
sys.path.insert(0, %r)
''' % str(__import__('pathlib').Path(__file__).parent))
    pytester.makepyfile("""
from build123d import Box, Location
from pruefstand import Body, overlap
from test_haerte import _SturerKern

def test_schlucken_verboten():
    a = Body('A', 'A', solid=_SturerKern(Box(10, 10, 10)))
    b = Body('B', 'B', solid=Box(10, 10, 10).locate(Location((5.0, 0.0, 0.0))))
    overlap(a, b)          # Ergebnis bewusst ignoriert -- der Lauf muss es trotzdem merken
""")
    return pytester


# -- Fehlende Zuordnung --------------------------------------------------

def test_fehlende_zuordnung_bleibt_unentschieden():
    """Ohne Gegenstück gibt es kein Urteil -- weder „unverändert" noch „verletzt"."""
    a = box('A', (10, 10, 10))
    region = Region.box(Frame.identity(), (-20, -20, -20), (20, 20, 20))
    r = same_as(a, None, region)
    assert r.unentschieden
    assert not r.passed, 'ohne Zuordnung darf nichts bestehen'
    assert not r.technischer_fehler, 'eine fehlende Zuordnung ist kein Werkzeugausfall'
    assert "kein Vorgänger" in r.offen_grund
    assert forget_open()


def test_unentschieden_ist_ein_eigener_ausgang(pytester):
    """Der Lauf endet nicht grün, weist den Fall aber nicht als Geometriefehler aus."""
    pytester.makepyfile("""
from build123d import Box
from pruefstand import Body, Frame, same_as
from pruefstand.region import Region

def test_ohne_vorgaenger():
    a = Body('A', 'A', solid=Box(10, 10, 10))
    same_as(a, None, Region.box(Frame.identity(), (-20, -20, -20), (20, 20, 20)))
""")
    ergebnis = pytester.runpytest('-q')
    assert ergebnis.ret != 0, 'ein Lauf ganz ohne Urteil darf nicht mit Erfolg enden'
    ergebnis.stdout.fnmatch_lines(['*unentschieden*'])


# -- Kernelabsturz -------------------------------------------------------

def test_kernelabsturz_wird_technischer_fehler():
    """Ein harter Absturz des Geometriekerns reißt den Lauf nicht mit."""
    from pruefstand import kernel
    with pytest.raises(KernelFehler) as e:
        kernel.rechne('absturz', b'', b'', zeit_s=30)
    assert 'SIGSEGV' in str(e.value)
    # Nach dem Absturz muss weitergerechnet werden können, sonst fällt jeder
    # Folgetest dem ersten kaputten Körper zum Opfer.
    from build123d import Box
    daten = kernel.schreibe(Box(10, 10, 10))
    assert kernel.rechne('schnitt', daten, daten) == pytest.approx(1000.0)
    kernel.beende()


def test_bewachter_schnitt_liefert_denselben_wert(monkeypatch):
    """Der Wächter darf den Messwert nicht verändern, nur absichern."""
    a = box('A', (10, 10, 10))
    b = box('B', (10, 10, 10), at=(5, 0, 0))
    ohne = overlap(a, b).volume_mm3
    monkeypatch.setenv('PRUEFSTAND_KERNWAECHTER', '1')
    mit = overlap(a, b).volume_mm3
    from pruefstand import kernel
    kernel.beende()
    assert mit == pytest.approx(ohne)
