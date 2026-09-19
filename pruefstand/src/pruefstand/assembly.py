"""Montage-Storyboard: `spec/montage.yaml` laden und in prüfbare Schritte übersetzen.

    schema: pruefstand.montage/1
    ersetzt: [R55, R15]                 # optional: Körper, die dieser Umbau ausbaut
    schritte:
      - name: Zugbügel einsetzen
        teil: P03
        bewegung: {frame: local, richtung: [0, -1, 0], weg: 40}
        gegen: fest                     # fest | alles | Liste von Keys
        bereits_montiert: [T05, T41L, T41R]
        nominale_kontakte: [[P03, R10]] # optional: konstruktive Dauerkontakte am Sitz
        beruehrung_erlaubt: true        # optional: gleitende Passflächen sind keine Kollision
        motionen: {hub: 100}            # optional: Pose der Maschine für diesen Schritt
        notiz: ...                      # optional
        status: not_built_yet           # optional: Schritt beschrieben, Teil fehlt noch

Der Sinn der Datei ist, dass jeder Schritt gegen **genau den Bestand von diesem Augenblick**
geprüft wird, nicht gegen die fertige Maschine. Deshalb erzwingt der Lader zwei Regeln:

* Was ein **späterer** Schritt einbaut, ist im aktuellen Schritt nicht da. Das wird aus der
  Reihenfolge abgeleitet, nicht vom Autor abgeschrieben -- man kann es also nicht vergessen.
* Was ein **früherer** Schritt eingebaut hat, muss im aktuellen Schritt in `bereits_montiert`
  stehen. Fehlt es, ist das ein Fehler in der Datei, kein stillschweigend milderer Test.

Fehlerhafte Dateien werden laut und früh abgewiesen (unbekannte Schlüssel eingeschlossen --
ein Tippfehler darf keine Prüfung stillschweigend ausschalten).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .results import NICHT_GEBAUT, pruefe_bau_status

SCHEMA = 'pruefstand.montage/1'

_TOP = {'schema', 'ersetzt', 'schritte'}
_STEP = {'name', 'teil', 'bewegung', 'gegen', 'bereits_montiert', 'nominale_kontakte',
         'beruehrung_erlaubt', 'motionen', 'notiz', 'status'}
_MOVE = {'frame', 'richtung', 'weg', 'motion', 'bis'}


class MontageError(ValueError):
    """Die YAML-Datei ist kaputt oder in sich widersprüchlich."""


def _err(where, msg):
    raise MontageError(f'{where}: {msg}')


def _keys(where, d, allowed):
    if not isinstance(d, dict):
        _err(where, f'Abbildung erwartet, bekommen {type(d).__name__}')
    unknown = sorted(set(d) - allowed)
    if unknown:
        _err(where, f'unbekannte Schlüssel {unknown} (erlaubt: {sorted(allowed)})')


def _keylist(where, v):
    if v is None:
        return []
    if isinstance(v, str) or not isinstance(v, (list, tuple)):
        _err(where, f'Liste von Keys erwartet, bekommen {v!r}')
    out = []
    for k in v:
        if not isinstance(k, str) or not k.strip():
            _err(where, f'Key muss ein nicht-leerer Text sein, bekommen {k!r}')
        out.append(k.strip())
    if len(set(out)) != len(out):
        _err(where, f'doppelte Einträge in {out}')
    return out


@dataclass
class Step:
    """Ein Montageschritt. Längen mm, Richtungen im Frame `frame` der Maschine."""

    index: int
    name: str
    teil: str
    richtung: np.ndarray | None = None
    weg: float | None = None
    frame: str = 'local'
    motion: str | None = None
    bis: float | None = None
    gegen: object = 'fest'
    bereits_montiert: list = field(default_factory=list)
    nominale_kontakte: list = field(default_factory=list)
    beruehrung_erlaubt: bool = False
    motionen: dict = field(default_factory=dict)
    notiz: str = ''
    #: '' oder 'not_built_yet': der Schritt steht, das Teil dazu fehlt noch.
    status: str = ''
    ersetzt: list = field(default_factory=list)
    spaeter: list = field(default_factory=list)      # Teile, die erst nach diesem Schritt kommen
    quelle: Path | None = None

    @property
    def nicht_gebaut(self) -> bool:
        """Der Schritt ist beschrieben, das Teil dazu noch nicht gebaut."""
        return self.status == NICHT_GEBAUT

    # -- Kontext ---------------------------------------------------------
    def nicht_vorhanden(self) -> set:
        """Keys, die in diesem Augenblick definitiv nicht in der Maschine stecken."""
        return set(self.ersetzt) | set(self.spaeter) | {self.teil}

    def against_keys(self, machine) -> list[str]:
        """Die Körper der Maschine, gegen die dieser Schritt zu prüfen ist."""
        alle = list(machine.keys())
        if self.gegen == 'alles':
            base = alle
        elif self.gegen == 'fest':
            base = [k for k in alle if not machine.body(k).moving]
        else:
            unbekannt = [k for k in self.gegen if k not in alle]
            if unbekannt:
                _err(self.where, f'gegen nennt unbekannte Körper {unbekannt}')
            base = list(self.gegen)
        weg = self.nicht_vorhanden()
        keys = [k for k in base if k not in weg]
        for k in self.bereits_montiert:
            if k in alle and k not in keys and k not in weg:
                keys.append(k)
        return keys

    def neue_teile(self, machine) -> list[str]:
        """Einträge aus `bereits_montiert`, die die Maschine nicht kennt.

        Das sind die Teile des Umbaus selbst. Sie muss der Aufrufer beisteuern -- `against_keys`
        kann sie nicht liefern, und stillschweigend verschlucken darf man sie erst recht nicht.
        """
        alle = set(machine.keys())
        return [k for k in self.bereits_montiert if k not in alle]

    def richtung_welt(self, machine) -> np.ndarray:
        if self.motion is not None:
            m = machine.motions.get(self.motion)
            if m is None:
                _err(self.where, f'Motion {self.motion!r} unbekannt: {sorted(machine.motions)}')
            v = np.asarray(m.get('axis', (0, 0, 1)), dtype=float)
            f = machine.frame(m.get('frame', 'local'))
        else:
            v = self.richtung
            f = machine.frame(self.frame)
        w = f.direction_to_world(v)
        return w / float(np.linalg.norm(w))

    def weg_mm(self, machine) -> float:
        if self.weg is not None:
            return float(self.weg)
        m = machine.motions[self.motion]
        return abs(float(self.bis) - float(m.get('default', 0)))

    @property
    def where(self) -> str:
        return f'{self.quelle}: schritte[{self.index}] ({self.name!r})'

    def __repr__(self):
        wie = (f'motion={self.motion} bis={self.bis}' if self.motion
               else f'{np.round(self.richtung, 3).tolist()} x {self.weg} mm')
        return f'Step({self.index}, {self.name!r}, teil={self.teil}, {wie})'


def _step(i, raw, path, ersetzt) -> Step:
    where = f'{path}: schritte[{i}]'
    _keys(where, raw, _STEP)
    for req in ('name', 'teil', 'bewegung'):
        if raw.get(req) in (None, ''):
            _err(where, f'{req} fehlt')
    name = str(raw['name'])
    teil = str(raw['teil']).strip()
    if not teil:
        _err(where, 'teil ist leer')

    mv = raw['bewegung']
    _keys(f'{where}.bewegung', mv, _MOVE)
    st = Step(index=i, name=name, teil=teil, quelle=path, ersetzt=list(ersetzt))
    st.frame = str(mv.get('frame', 'local'))
    if 'motion' in mv:
        if 'richtung' in mv:
            _err(f'{where}.bewegung', 'motion und richtung schließen sich aus')
        st.motion = str(mv['motion'])
        if 'bis' not in mv and 'weg' not in mv:
            _err(f'{where}.bewegung', 'motion braucht bis oder weg')
        st.bis = None if mv.get('bis') is None else float(mv['bis'])
        st.weg = None if mv.get('weg') is None else float(mv['weg'])
    else:
        r = mv.get('richtung')
        if not isinstance(r, (list, tuple)) or len(r) != 3:
            _err(f'{where}.bewegung', f'richtung braucht drei Zahlen, bekommen {r!r}')
        try:
            v = np.asarray([float(x) for x in r], dtype=float)
        except (TypeError, ValueError):
            _err(f'{where}.bewegung', f'richtung ist nicht numerisch: {r!r}')
        if not np.any(v):
            _err(f'{where}.bewegung', 'richtung ist der Nullvektor')
        st.richtung = v
        if mv.get('weg') is None:
            _err(f'{where}.bewegung', 'weg fehlt')
        st.weg = float(mv['weg'])
    if st.weg is not None and st.weg <= 0:
        _err(f'{where}.bewegung', f'weg muss > 0 sein, ist {st.weg}')

    gegen = raw.get('gegen', 'fest')
    if isinstance(gegen, str):
        if gegen not in ('fest', 'alles'):
            _err(where, f"gegen={gegen!r} -- erlaubt sind 'fest', 'alles' oder eine Liste von Keys")
        st.gegen = gegen
    else:
        st.gegen = _keylist(f'{where}.gegen', gegen)
        if not st.gegen:
            _err(where, 'gegen ist eine leere Liste -- dann gibt es nichts zu prüfen')

    st.bereits_montiert = _keylist(f'{where}.bereits_montiert', raw.get('bereits_montiert'))
    st.notiz = str(raw.get('notiz', '') or '')
    try:
        st.status = pruefe_bau_status(raw.get('status'), where)
    except ValueError as exc:
        _err(where, str(exc).split(': ', 1)[-1])
    bt = raw.get('beruehrung_erlaubt', False)
    if not isinstance(bt, bool):
        _err(where, f'beruehrung_erlaubt muss true/false sein, ist {bt!r}')
    st.beruehrung_erlaubt = bt

    mot = raw.get('motionen') or {}
    if not isinstance(mot, dict):
        _err(where, f'motionen muss eine Abbildung sein, ist {mot!r}')
    st.motionen = {str(k): float(v) for k, v in mot.items()}

    nk = raw.get('nominale_kontakte') or []
    if not isinstance(nk, (list, tuple)):
        _err(where, f'nominale_kontakte muss eine Liste von Paaren sein, ist {nk!r}')
    pairs = []
    for p in nk:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            _err(where, f'nominale_kontakte: Paar [a, b] erwartet, bekommen {p!r}')
        pairs.append((str(p[0]), str(p[1])))
    st.nominale_kontakte = pairs
    return st


def load_assembly(path) -> list[Step]:
    """`montage.yaml` laden, prüfen und als Liste von Schritten zurückgeben."""
    import yaml

    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f'Montage-Storyboard fehlt: {path}')
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise MontageError(f'{path}: kein gültiges YAML: {exc}') from exc
    if not isinstance(data, dict):
        _err(path, f'Abbildung auf oberster Ebene erwartet, bekommen {type(data).__name__}')
    _keys(str(path), data, _TOP)
    if data.get('schema') != SCHEMA:
        _err(path, f'unerwartetes Schema {data.get("schema")!r}, erwartet {SCHEMA!r}')
    raw = data.get('schritte')
    if not isinstance(raw, list) or not raw:
        _err(path, 'schritte fehlt oder ist leer')
    ersetzt = _keylist(f'{path}.ersetzt', data.get('ersetzt'))

    steps = [_step(i, r, path, ersetzt) for i, r in enumerate(raw)]

    teile = [s.teil for s in steps]
    for i, t in enumerate(teile):
        if t in teile[:i]:
            _err(steps[i].where, f'Teil {t!r} wird zweimal montiert (Schritt {teile.index(t)} und {i})')
    for i, s in enumerate(steps):
        s.spaeter = teile[i + 1:]
        fehlt = [t for t in teile[:i] if t not in s.bereits_montiert]
        if fehlt:
            _err(s.where, f'bereits_montiert vergisst {fehlt} aus früheren Schritten -- '
                          f'dann prüft der Schritt gegen weniger als wirklich dasteht')
        if s.teil in s.bereits_montiert:
            _err(s.where, f'{s.teil!r} steht in seinem eigenen bereits_montiert')
        zu_frueh = [k for k in s.bereits_montiert if k in s.spaeter]
        if zu_frueh:
            _err(s.where, f'bereits_montiert nennt {zu_frueh}, das erst später eingebaut wird')
        doppelt = [k for k in s.bereits_montiert if k in s.ersetzt]
        if doppelt:
            _err(s.where, f'bereits_montiert nennt {doppelt}, das unter ersetzt ausgebaut wird')
    return steps
