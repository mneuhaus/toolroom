"""Riskante Kernrechnungen laufen in einem eigenen Prozess.

Ein Boolean, an dem OCCT hart abstürzt, nimmt sonst den ganzen Testlauf mit. Ein
toter Lauf meldet keinen Messwert -- er meldet gar nichts, und das sieht von außen
aus wie „noch nicht gelaufen", nicht wie „hier ist etwas kaputt". Im Kindprozess
wird der Absturz zu einem Ergebnis: `KernelFehler`, und damit zu einem technischen
Fehler im Bericht.

Transport ist BREP, nicht pickle: build123ds Pickle-Rückweg scheitert an echten
STEP-Körpern (`BinTools_SurfaceSet::ReadGeometry: UnExpected BRep_PointRepresentation`),
schreibt die Bytes aber klaglos. Gemessen an einem echten Teil (87 Flächen):
schreiben 1,6 ms, lesen 0,8 ms, 74 KiB; ein Aufruf über die Leitung 4,3 ms, der
erste inklusive Prozessstart knapp 1 s.

Der Wächter ist bewusst zuschaltbar (`PRUEFSTAND_KERNWAECHTER=1`) und nicht überall
verdrahtet: er kostet je Rechnung rund 10 ms, und die meisten Booleans stürzen nicht
ab, sondern werfen -- die fängt die Absicherung in den Primitiven schon ab.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import signal
import tempfile

from .results import KernelFehler

ZEIT_S = 120.0
_ctx = mp.get_context('spawn')
_worker = None
_conn = None


def aktiv() -> bool:
    return os.environ.get('PRUEFSTAND_KERNWAECHTER', '') not in ('', '0')


# -- Im Kindprozess ------------------------------------------------------

_gelesen: dict = {}


def _lese(daten: bytes):
    """BREP-Bytes zu einem Körper -- gemerkt, weil das Lesen teuer ist.

    Ohne diesen Zwischenspeicher kostete ein Schnitt an einem echten Teil 476 ms,
    fast alles davon das erneute Einlesen beider Operanden.
    """
    schluessel = hash(daten)
    hit = _gelesen.get(schluessel)
    if hit is not None:
        return hit
    from build123d import Solid
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    pfad = tempfile.mktemp(suffix='.brep')
    try:
        with open(pfad, 'wb') as fh:
            fh.write(daten)
        shape = TopoDS_Shape()
        BRepTools.Read_s(shape, pfad, BRep_Builder())
        koerper = Solid(shape)
        _gelesen[schluessel] = koerper
        return koerper
    finally:
        if os.path.exists(pfad):
            os.unlink(pfad)


def schreibe(solid) -> bytes:
    """Einen Körper für die Leitung verpacken."""
    from OCP.BRepTools import BRepTools
    pfad = tempfile.mktemp(suffix='.brep')
    try:
        BRepTools.Write_s(solid.wrapped, pfad)
        with open(pfad, 'rb') as fh:
            return fh.read()
    finally:
        if os.path.exists(pfad):
            os.unlink(pfad)


def _schnitt_volumen(a: bytes, b: bytes) -> float:
    return float(_lese(a).intersect(_lese(b)).volume)


def _differenz_volumen(a: bytes, b: bytes) -> float:
    return float(_lese(a).cut(_lese(b)).volume)


def _absturz(*_):
    """Bringt den Rechenprozess hart um.

    Steht bewusst im Auslieferungsstand: das Abnahmekriterium verlangt, dass ein
    Kernelabsturz offline reproduzierbar als technischer Fehler erscheint. Ohne
    diesen Auftrag liesse sich genau der Fall nur mit Glück und einem kaputten
    Modell nachstellen.
    """
    import ctypes
    ctypes.string_at(0)


_AUFTRAEGE = {'schnitt': _schnitt_volumen, 'differenz': _differenz_volumen,
              'absturz': _absturz}


def _schleife(conn):
    while True:
        auftrag = conn.recv()
        if auftrag is None:
            break
        name, args = auftrag
        try:
            conn.send(('ok', _AUFTRAEGE[name](*args)))
        except Exception as e:  # eine geworfene Ausnahme ist kein Absturz
            conn.send(('fehler', f'{type(e).__name__}: {e}'))


# -- Im Elternprozess ----------------------------------------------------

def _start():
    global _worker, _conn
    hier, dort = _ctx.Pipe()
    _worker = _ctx.Process(target=_schleife, args=(dort,), daemon=True)
    _worker.start()
    dort.close()
    _conn = hier


def beende() -> None:
    """Den Rechenprozess beenden -- für Tests und am Ende eines Laufs."""
    global _worker, _conn
    if _worker is not None and _worker.is_alive():
        try:
            _conn.send(None)
            _worker.join(2.0)
        except Exception:
            pass
        if _worker.is_alive():
            _worker.terminate()
    _worker, _conn = None, None


def _grund(code) -> str:
    if code is None:
        return 'Zeitüberschreitung, der Kern rechnet noch'
    if code < 0:
        name = signal.Signals(-code).name
        return f'Kernel abgestürzt, Signal {name}'
    return f'Rechenprozess beendet, Rückgabewert {code}'


def rechne(name: str, *args, zeit_s: float = ZEIT_S):
    """Einen Auftrag im Rechenprozess ausführen.

    Erhebt `KernelFehler` bei Absturz, Zeitüberschreitung und geworfener Ausnahme --
    nie einen Zahlenwert, den niemand gerechnet hat.
    """
    if _worker is None or not _worker.is_alive():
        _start()
    _conn.send((name, args))
    # Nicht recv() ohne poll(): stirbt das Kind mitten in der Rechnung, bleibt recv()
    # hängen, statt EOF zu liefern. Gemessen -- der Lauf stand sonst still. In Scheiben
    # warten, damit ein Absturz sofort auffällt und nicht erst nach `zeit_s`.
    rest = zeit_s
    while not _conn.poll(min(0.05, rest)):
        rest -= 0.05
        if not _worker.is_alive():
            code = _worker.exitcode
            beende()
            raise KernelFehler(_grund(code))
        if rest <= 0:
            beende()
            raise KernelFehler(_grund(None))
    try:
        art, wert = _conn.recv()
    except EOFError:
        # Der Pipe-Schluss zählt als lesbar, der Absturz kommt also hier an und
        # nicht über den Lebendtest oben.
        _worker.join(1.0)
        code = _worker.exitcode
        beende()
        raise KernelFehler(_grund(code)) from None
    if art == 'fehler':
        raise KernelFehler(wert)
    return wert
