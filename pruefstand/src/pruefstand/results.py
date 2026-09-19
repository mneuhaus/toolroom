"""Messergebnisse der Primitive und ihr Weg in den Testbericht."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import context

LEER_MELDUNG = 'nichts gemessen: Region enthält keine Geometrie'
TECHNIK_MELDUNG = 'technischer Fehler: das Messverfahren ist gescheitert, der Messwert ist keiner'
OFFEN_MELDUNG = 'unentschieden: die Anforderung ist keiner Geometrie zugeordnet'

#: Erlaubter Wert von `status:` in den Pflegedateien. Er sagt: diese Anforderung ist
#: beschrieben, das Teil dazu ist noch nicht gebaut. Der zugehörige Test wird damit
#: **unentschieden** -- nicht grün (nichts geprüft) und nicht rot (nichts verletzt).
#: Ohne diesen Zustand müsste man die Zeile auskommentieren, und dann fehlt sie später.
NICHT_GEBAUT = 'not_built_yet'
NICHT_GEBAUT_MELDUNG = f'`status: {NICHT_GEBAUT}` in der Pflegedatei -- das Teil gibt es noch nicht'


def pruefe_bau_status(wert, wo: str) -> str:
    """`status:` aus einer Pflegedatei prüfen. Erlaubt ist nur `not_built_yet`."""
    if wert is None:
        return ''
    s = str(wert).strip()
    if s != NICHT_GEBAUT:
        raise ValueError(f'{wo}: status {wert!r} unbekannt, erlaubt ist nur {NICHT_GEBAUT!r} '
                         '(oder gar kein status)')
    return s


_records: dict[str, list[dict]] = {}
_leer: dict[str, list[str]] = {}
_technisch: dict[str, list[str]] = {}
_offen: dict[str, list[str]] = {}
_posen: dict[str, list[dict]] = {}
_budget: dict[str, dict] = {}
#: Körper, die seit der letzten Messung angefasst wurden. `as_bodies` füllt, jedes
#: `_publish` leert -- so weiß ein Ergebnis, an welchen Körpern es entstanden ist,
#: ohne dass jedes Primitiv das selbst mitschreiben müsste.
_koerper_offen: list[tuple] = []

BUDGET_ARTEN = ('geprueft', 'uebersprungen', 'angenommen')

#: So viele Körper stehen namentlich in einem Budgeteintrag, der Rest nur als Zahl.
#: Eine Sweep-Prüfung gegen die ganze Maschine fasst über hundert Körper an; sie alle
#: bei jeder einzelnen Messung auszuschreiben blähte den Bericht auf 3 MB, ohne einen
#: Leser klüger zu machen. Die vollständige Liste steht im Kopf des Laufs.
BUDGET_KOERPER_MAX = 12

#: Alle Körper eines Tests mit der Frage, ob sie ein BRep hatten. Vollständig -- die
#: Liste im einzelnen Messeintrag ist gekappt, diese hier nicht.
_budget_koerper: dict[str, dict] = {}


class KernelFehler(Exception):
    """Der Geometriekern hat die Rechnung verweigert.

    Wird nie in einen Messwert umgerechnet. Ein gescheiterter Boolean ist kein
    Volumen von null -- das wäre die Aussage „keine Überschneidung", und die hat
    niemand gemessen.
    """


def record(test_id, name, values: dict) -> None:
    if test_id is None:
        test_id = context.test_id()
    if test_id is None:
        return
    _records.setdefault(test_id, []).append({'primitive': name, **values})


def records(test_id=None):
    if test_id is None:
        return dict(_records)
    return list(_records.get(test_id, []))


def budget_eintrag(art: str, test_id=None, **werte) -> None:
    """Einen Posten ins Prüfbudget schreiben.

    Das Budget beantwortet die Frage, die eine Zahl allein nie beantwortet: *woran*
    ist sie entstanden. `geprueft` sagt, welches Primitiv welche Körper in welcher
    Pose gemessen hat; `uebersprungen`, was dabei ausgelassen wurde (Netz ohne BRep,
    leeres Fenster, Bbox-Vorfilter); `angenommen`, worauf das Urteil beruht
    (`urteil_auf`, Abtastdichten, Grenzwerte der Regel). Ein grüner Test, der die
    halbe Maschine übersprungen hat, sieht im Terminal aus wie jeder andere -- im
    Budget nicht.
    """
    if art not in BUDGET_ARTEN:
        raise ValueError(f'Budgetart {art!r} unbekannt, erlaubt {list(BUDGET_ARTEN)}')
    if test_id is None:
        test_id = context.test_id()
    if test_id is None:
        return
    eimer = _budget.setdefault(test_id, {a: [] for a in BUDGET_ARTEN})
    eimer[art].append(_j(dict(werte)))


def budget(test_id) -> dict:
    out = {a: list(v) for a, v in _budget.get(test_id, {a: [] for a in BUDGET_ARTEN}).items()}
    out['koerper'] = dict(sorted(_budget_koerper.get(test_id, {}).items()))
    ohne = [k for k, brep in out['koerper'].items() if not brep]
    if ohne:
        out['uebersprungen'].append({
            'was': 'brep', 'anzahl': len(ohne), 'keys': ohne,
            'grund': 'nur als Netz geladen -- exakt gerechnet wird daran nichts'})
    return out


def merke_koerper(key: str, hat_brep: bool) -> None:
    """Einen angefassten Körper vormerken -- wird beim nächsten `_publish` verbucht."""
    eintrag = (str(key), bool(hat_brep))
    if eintrag not in _koerper_offen:
        _koerper_offen.append(eintrag)


def zieh_koerper() -> list[tuple]:
    """Die vorgemerkten Körper abholen und die Merkliste leeren."""
    out = list(_koerper_offen)
    _koerper_offen.clear()
    return out


def merke_pose(values: dict, test_id=None) -> None:
    """Die Pose festhalten, in der gemessen wurde.

    Ein Messwert ohne Pose ist bei einer bewegten Maschine nur die halbe Aussage: 0,2 mm
    Fuge bei Schwenk −135° und 0,2 mm bei +45° sind zwei verschiedene Befunde. Gesammelt
    wird eine **Liste**, weil ein Test mehrere Posen durchfahren darf; ein einzelnes
    Feld müsste sich für eine entscheiden und damit lügen.
    """
    if test_id is None:
        test_id = context.test_id()
    if test_id is None:
        return
    p = dict(values)
    liste = _posen.setdefault(test_id, [])
    if p not in liste:
        liste.append(p)


def posen(test_id) -> list[dict]:
    return list(_posen.get(test_id, []))


def mark_empty(test_id, grund: str) -> None:
    """Eine Messung hatte nichts zu messen. Der Test darf nicht grün werden."""
    if test_id is None:
        test_id = context.test_id()
    if test_id is None:
        return
    _leer.setdefault(test_id, []).append(grund)


def empty_reasons(test_id) -> list[str]:
    return list(_leer.get(test_id, []))


def mark_technical(test_id, grund: str) -> None:
    """Das Messverfahren ist gescheitert. Der Test darf nicht grün werden."""
    if test_id is None:
        test_id = context.test_id()
    if test_id is None:
        return
    _technisch.setdefault(test_id, []).append(grund)


def technical_reasons(test_id) -> list[str]:
    return list(_technisch.get(test_id, []))


def mark_open(test_id, grund: str) -> None:
    """Die Zuordnung fehlt. Es gibt kein Urteil -- weder „bestanden" noch „verletzt"."""
    if test_id is None:
        test_id = context.test_id()
    if test_id is None:
        return
    _offen.setdefault(test_id, []).append(grund)


def open_reasons(test_id) -> list[str]:
    return list(_offen.get(test_id, []))


def forget_open(test_id=None) -> list[str]:
    """Offen-Markierungen vergessen -- für Tests des Prüfstands selbst."""
    if test_id is None:
        test_id = context.test_id()
    return _offen.pop(test_id, [])


def forget_technical(test_id=None) -> list[str]:
    """Technik-Markierungen vergessen -- für Tests des Prüfstands selbst."""
    if test_id is None:
        test_id = context.test_id()
    return _technisch.pop(test_id, [])


def forget_empty(test_id=None) -> list[str]:
    """Leer-Markierungen eines Tests vergessen und zurückgeben.

    Für Tests des Prüfstands selbst, die eine leere Messung absichtlich auslösen und
    trotzdem grün bleiben sollen.
    """
    if test_id is None:
        test_id = context.test_id()
    return _leer.pop(test_id, [])


def clear() -> None:
    _records.clear()
    _leer.clear()
    _technisch.clear()
    _offen.clear()
    _posen.clear()
    _budget.clear()
    _budget_koerper.clear()
    _koerper_offen.clear()


def _j(v):
    if isinstance(v, np.ndarray):
        return [round(float(x), 4) for x in np.ravel(v)]
    if isinstance(v, (np.floating, float)):
        return None if v != v else round(float(v), 5) if abs(v) < 1e12 else float(v)
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (list, tuple)):
        return [_j(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _j(x) for k, x in v.items()}
    if v is None or isinstance(v, (str, bool)):
        return v
    return str(v)


class Result:
    """Basis: bool() = bestanden, as_dict() für den Bericht."""

    primitive = 'result'
    _fields: tuple = ()
    #: nichts zu messen (leere Region). Kein `_fields`-Eintrag, damit die Repr-Zeilen
    #: im Bericht unverändert bleiben; im JSON hängt der Schlüssel hinten an.
    nichts_gemessen: bool = False
    leer_grund: str = ''
    #: Das Verfahren ist gescheitert (Kernel verweigert, Zuordnung fehlt). Anders als
    #: `nichts_gemessen`: dort gab es nichts zu messen, hier hat das Messen versagt.
    technischer_fehler: bool = False
    fehler_grund: str = ''
    #: Die Anforderung liess sich keiner Geometrie zuordnen. Das ist kein Fehlschlag:
    #: ein nicht gefundener Anker beweist keinen Verstoss, er beweist gar nichts.
    unentschieden: bool = False
    offen_grund: str = ''
    #: Worauf das Urteil in `passed` tatsächlich beruht -- 'mesh' oder 'brep'. Ein
    #: exakt gerechneter Nebenwert macht ein abgetastetes Urteil nicht exakt.
    urteil_auf: str = ''
    #: Hat das Messfenster Material angeschnitten? `None` heißt: es wurde nichts
    #: zugeschnitten, also gibt es dazu auch keine Aussage. Kein Urteil, nur Hinweis --
    #: aber der wichtigste: ein Fenster, dessen Wand im Material liegt, misst am Rand
    #: sich selbst (Zylinder r 4,5 über dem Bund Ø10,5 lieferte 4,41 statt 3,95).
    fenster_schneidet_material: bool | None = None
    #: Die Zahlen sind eine **Obergrenze**, kein Messwert: der Messung fehlt eine
    #: Angabe, mit der Treffer herausgefallen wären (bei `unverrundet` die Druckpose
    #: und der Kontext für Fugenkanten). Im Terminalbericht steht dann `≤` vor den
    #: Werten, im JSON der Schlüssel `obergrenze`. Kein Urteil -- aber der Unterschied
    #: zwischen „104 scharfe Kanten" und „höchstens 104" ist der zwischen einem Befund
    #: und einer Hausnummer.
    obergrenze: bool = False
    #: Welche Felder von `obergrenze` betroffen sind. Nur Zählungen und Summen sind
    #: zu groß; ein Radius oder eine Schwelle ist keine Obergrenze, nur weil der
    #: Messung eine Ausnahme fehlt -- „radius_mm=≤4,2" wäre schlicht falsch.
    _obergrenze_felder: tuple = ()

    @property
    def uebersprungen(self) -> list:
        """Was diese Messung ausgelassen hat -- je Eintrag `was` und `grund`.

        Bewusst eine Eigenschaft und kein Klassenattribut: eine Liste an der Klasse
        teilten sich alle Ergebnisse, und der erste übersprungene Körper stünde im
        Budget jeder späteren Messung.
        """
        if not hasattr(self, '_uebersprungen'):
            self._uebersprungen = []
        return self._uebersprungen

    @property
    def annahmen(self) -> list:
        """Unter welchen Annahmen der Messwert gilt (Grenzwerte, Raster, Dichten)."""
        if not hasattr(self, '_annahmen'):
            self._annahmen = []
        return self._annahmen

    def _budget_buchen(self):
        """Was diese Messung geprüft, ausgelassen und angenommen hat, ins Budget."""
        koerper = zieh_koerper()
        namen = [k for k, _ in koerper]
        eintrag = {'primitiv': self.primitive, 'koerper_n': len(namen),
                   'koerper': namen[:BUDGET_KOERPER_MAX],
                   'urteil_auf': self.urteil_auf or None}
        pose = posen(context.test_id())
        if pose:
            eintrag['pose'] = pose[-1]
        budget_eintrag('geprueft', **eintrag)
        # Körper ohne BRep werden hier nur vermerkt, nicht je Messung gemeldet: ein
        # Schwenktest fasst hundert Netzkörper an, und hundert gleichlautende Zeilen je
        # Test blähten den Bericht auf ein Megabyte. Die Sammelzeile setzt das Plugin
        # am Testende (`_brep_sammelzeile`).
        alle = _budget_koerper.setdefault(context.test_id() or '', {})
        for key, brep in koerper:
            alle[key] = bool(brep) and alle.get(key, True)
        for u in self.uebersprungen:
            budget_eintrag('uebersprungen', primitiv=self.primitive, **u)
        if self.nichts_gemessen:
            budget_eintrag('uebersprungen', primitiv=self.primitive, was='fenster',
                           grund=self.leer_grund or LEER_MELDUNG)
        if self.unentschieden:
            budget_eintrag('uebersprungen', primitiv=self.primitive, was='zuordnung',
                           grund=self.offen_grund or OFFEN_MELDUNG)
        for a in self.annahmen:
            budget_eintrag('angenommen', primitiv=self.primitive, **a)
        if self.urteil_auf:
            budget_eintrag('angenommen', primitiv=self.primitive, urteil_auf=self.urteil_auf)
        if self.fenster_schneidet_material:
            budget_eintrag('angenommen', primitiv=self.primitive,
                           fenster_schneidet_material=True,
                           grund='Fensterwand liegt im Material -- der Randwert kann das '
                                 'Fenster selbst sein')

    def _publish(self):
        self._budget_buchen()
        d = self.as_dict()
        if self.technischer_fehler:
            # Kein Verfahren, kein Urteil. Das überstimmt alles, was oben berechnet wurde.
            self.passed = False
            d['technischer_fehler'] = True
            d['fehler_grund'] = self.fehler_grund
            record(None, self.primitive, d)
            detail = f' ({self.fehler_grund})' if self.fehler_grund else ''
            mark_technical(None, f'{self.primitive}: {TECHNIK_MELDUNG}{detail}')
            return
        if self.urteil_auf:
            d['urteil_auf'] = self.urteil_auf
        if self.unentschieden:
            # Ohne Zuordnung gibt es nichts zu bestehen. Der Lauf muss das sichtbar
            # tragen, aber nicht als erkannten Geometriefehler ausweisen.
            self.passed = False
            d['unentschieden'] = True
            d['offen_grund'] = self.offen_grund
            record(None, self.primitive, d)
            detail = f' ({self.offen_grund})' if self.offen_grund else ''
            mark_open(None, f'{self.primitive}: {OFFEN_MELDUNG}{detail}')
            return
        if self.nichts_gemessen:
            d['nichts_gemessen'] = True
            record(None, self.primitive, d)
            detail = f' ({self.leer_grund})' if self.leer_grund else ''
            mark_empty(None, f'{self.primitive}: {LEER_MELDUNG}{detail}')
            return
        record(None, self.primitive, d)

    def as_dict(self) -> dict:
        d = {k: _j(getattr(self, k)) for k in self._fields}
        if self.fenster_schneidet_material is not None:
            d['fenster_schneidet_material'] = bool(self.fenster_schneidet_material)
        if self.obergrenze:
            d['obergrenze'] = True
            d['obergrenze_felder'] = list(self._obergrenze_felder)
        return d

    def summary(self) -> str:
        d = self.as_dict()
        parts = [f'{k}={d[k]}' for k in self._fields if d.get(k) is not None and not isinstance(d[k], (list, dict))]
        return f'{self.primitive}(' + ', '.join(parts) + ')'

    def __repr__(self):
        return self.summary()

    def __bool__(self):
        return bool(self.passed)


@dataclass(repr=False)
class GapResult(Result):
    min_mm: float = float('inf')
    point_a: object = None
    point_b: object = None
    pair: tuple = ()
    per_body: dict = field(default_factory=dict)
    penetrating: bool = False
    #: Worauf `penetrating` beruht: 'brep' (exakter Schnitt > 0) oder 'mesh'
    #: (Eindringtiefe über `gap.DURCHDRINGUNG_MM`). Leer, solange kein Paar den
    #: Abstand 0 hatte -- dann gibt es zur Durchdringung nichts zu sagen.
    penetration_auf: str = ''
    #: Größte gemessene Eindringtiefe des Netzwegs in mm. 0,0 im BRep-Weg: dort ist
    #: das Kriterium ein Volumen, und eine Tiefe zu erfinden wäre schlimmer als keine.
    durchdringung_mm: float = 0.0
    passed: bool = True
    primitive: str = 'gap'
    _fields: tuple = ('min_mm', 'pair', 'penetrating', 'penetration_auf',
                      'durchdringung_mm', 'point_a', 'point_b', 'per_body')


@dataclass(repr=False)
class OverlapResult(Result):
    volume_mm3: float | None = None
    collides: bool = False
    exact: bool = False
    contacts: int = 0
    max_penetration_mm: float = 0.0
    pairs: list = field(default_factory=list)
    touching: bool = False
    touch_pairs: list = field(default_factory=list)
    #: Wo es sich durchdringt, in Weltkoordinaten (mm). Im Netzweg die Kontaktorte aus
    #: dem Kollisionskern, im exakten Weg der Schwerpunkt des Schnittkörpers je Paar.
    #: „Kollidiert" schickt niemanden an die richtige Stelle, ein Ort schon.
    contact_points: list = field(default_factory=list)
    passed: bool = True
    primitive: str = 'overlap'
    _fields: tuple = ('volume_mm3', 'collides', 'exact', 'contacts', 'max_penetration_mm',
                      'touching', 'pairs', 'touch_pairs', 'contact_points')


@dataclass(repr=False)
class CoverageResult(Result):
    total: int = 0
    covered: int = 0
    open: int = 0
    open_points: object = None
    fraction: float = 0.0
    map_png: object = None
    passed: bool = True
    primitive: str = 'coverage'
    _fields: tuple = ('total', 'covered', 'open', 'fraction', 'map_png')


@dataclass(repr=False)
class ProtrusionResult(Result):
    volume_mm3: float | None = None
    hits: int = 0
    exact: bool = False
    passed: bool = True
    primitive: str = 'protrusion'
    _fields: tuple = ('volume_mm3', 'hits', 'exact')


@dataclass(repr=False)
class SameAsResult(Result):
    max_deviation_mm: float = 0.0
    #: Exaktes Differenzvolumen der **ganzen** Region -- erwartete Unterschiede sind
    #: darin enthalten. Nur `max_deviation_mm` nimmt sie heraus, und nur darauf beruht
    #: das Urteil. Steht eine Pilotbohrung in `erwartet`, taucht ihr Volumen hier auf.
    diff_mm3: float | None = None
    samples: int = 0
    exact: bool = False
    #: Abtastpunkte, die in einer erwarteten Region lagen und nicht gezählt wurden.
    erwartet_ausgenommen: int = 0
    passed: bool = True
    primitive: str = 'same_as'
    _fields: tuple = ('max_deviation_mm', 'diff_mm3', 'samples', 'exact',
                      'erwartet_ausgenommen')


@dataclass(repr=False)
class OhneUrteilResult(Result):
    """Ein Ergebnis, das ausdrücklich keines ist.

    Gebraucht für Anforderungen, deren Teil laut Pflegedatei (`status: not_built_yet`)
    noch gar nicht gebaut ist: prüfen lässt sich daran nichts, und eine grüne Zeile
    wäre eine Lüge über eine Geometrie, die niemand angesehen hat.
    """

    passed: bool = False
    primitive: str = 'unentschieden'
    _fields: tuple = ()


def ohne_urteil(primitive: str, grund: str) -> OhneUrteilResult:
    """Ein unentschiedenes Ergebnis erzeugen und in den Bericht schreiben."""
    r = OhneUrteilResult(primitive=str(primitive))
    r.unentschieden = True
    r.offen_grund = str(grund)
    r._publish()
    return r
