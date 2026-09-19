"""Körper für den Viewer beschaffen, reduzieren und einbetten.

Der Bericht nennt nur Körperschlüssel. Die Geometrie dazu steht an zwei Stellen:

* Maschinenkörper: `machine.json` (über `spec/pruefstand.yaml` gefunden) verweist
  auf STL-Dateien.
* Prüfteil-Körper aus STEP: der Prüfstand exportiert jeden angefassten Solid als
  `<review>/<sicherer_schlüssel>.stl` (siehe `body.Body.mesh`). Genau diese
  Dateien werden hier wiederverwendet.

Alles wird als indizierte Dreiecksgeometrie (float32-Positionen, uint32-Indizes,
base64) eingebettet. Damit die Seite klein bleibt, werden Kontextkörper stark
durch Vertex-Clustering reduziert.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .model import safe_key

#: Dreiecksbudget für die ganze Seite
BUDGET_BETEILIGT = 40_000
BUDGET_KONTEXT = 14_000
#: Obergrenze je Kontextkörper
KONTEXT_MAX_FACES = 450
#: Kontextkörper bis zu diesem Abstand (mm) um die beteiligten Körper herum
KONTEXT_RADIUS_MM = 220.0


@dataclass
class Koerper:
    key: str
    name: str
    rolle: str = ''
    beteiligt: bool = False
    moving: bool = False
    quelle: str = ''
    datei: str = ''
    mesh: object = None
    bounds: list | None = None
    faces_original: int = 0
    faces: int = 0


@dataclass
class Szene:
    koerper: list[Koerper] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    maschine_name: str = ''
    maschine_revision: str = ''
    maschine_pfad: str = ''

    def by_key(self, key) -> Koerper | None:
        for k in self.koerper:
            if k.key == key:
                return k
        return None


# -- Quellen finden -----------------------------------------------------------

def machine_pfad(projekt: Path) -> Path | None:
    """`spec/pruefstand.yaml` lesen und den machine.json-Pfad auflösen."""
    cfg = Path(projekt) / 'spec' / 'pruefstand.yaml'
    if not cfg.exists():
        return None
    try:
        import yaml
        data = yaml.safe_load(cfg.read_text()) or {}
    except Exception:
        return None
    m = data.get('machine')
    return (cfg.parent / m).resolve() if m else None


def _lade_machine(pfad: Path | None) -> dict:
    if pfad is None or not Path(pfad).exists():
        return {}
    try:
        return json.loads(Path(pfad).read_text())
    except Exception:
        return {}


# -- Mesh-Werkzeuge -----------------------------------------------------------

def _cluster(verts: np.ndarray, faces: np.ndarray, res: int):
    """Vertex-Clustering auf einem res³-Gitter: grob, robust, ohne Zusatzpaket."""
    lo = verts.min(axis=0)
    span = np.maximum(verts.max(axis=0) - lo, 1e-9)
    cell = np.clip(((verts - lo) / span * res).astype(np.int64), 0, res - 1)
    key = (cell[:, 0] * res + cell[:, 1]) * res + cell[:, 2]
    uniq, inv = np.unique(key, return_inverse=True)
    cnt = np.bincount(inv, minlength=len(uniq)).astype(float)
    nv = np.stack([np.bincount(inv, weights=verts[:, i], minlength=len(uniq)) / cnt
                   for i in range(3)], axis=1)
    nf = inv[faces]
    ok = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
    nf = nf[ok]
    if len(nf):
        _, idx = np.unique(np.sort(nf, axis=1), axis=0, return_index=True)
        nf = nf[np.sort(idx)]
    return nv, nf


def reduziere(verts: np.ndarray, faces: np.ndarray, ziel: int):
    """Auf ungefähr `ziel` Dreiecke eindampfen. Gibt (verts, faces) zurück."""
    if len(faces) <= ziel:
        return verts, faces
    best = None
    for res in (6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 192, 256):
        nv, nf = _cluster(verts, faces, res)
        if len(nf) == 0:
            continue
        best = (nv, nf)
        if len(nf) >= ziel:
            break
    return best if best is not None else (verts, faces)


def _b64(arr: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(arr).tobytes()).decode('ascii')


def payload(k: Koerper) -> dict:
    """Kompakt einbetten: Positionen als int16 je Körper-Hüllquader, Indizes so schmal wie möglich.

    Der Quantisierungsfehler ist Spanne/65535 – bei 200 mm Körpergröße also 3 µm,
    weit unter allem, was man in der Ansicht sehen kann.
    """
    v = np.asarray(k.mesh[0], dtype=float)
    f = np.asarray(k.mesh[1], dtype=np.int64)
    lo = v.min(axis=0)
    span = np.maximum(v.max(axis=0) - lo, 1e-9)
    q = np.rint((v - lo) / span * 65534.0 - 32767.0).astype(np.int16)
    idx16 = len(v) <= 65535
    return {
        'key': k.key, 'name': k.name, 'rolle': k.rolle or '',
        'beteiligt': bool(k.beteiligt), 'moving': bool(k.moving),
        'quelle': k.quelle, 'datei': k.datei,
        'faces': int(len(f)), 'faces_original': int(k.faces_original),
        'qlo': [float(x) for x in lo], 'qspan': [float(x) for x in span],
        'idx16': bool(idx16),
        'pos': _b64(q),
        'idx': _b64(f.astype(np.uint16 if idx16 else np.uint32)),
    }


def _lade_stl(pfad: Path):
    import trimesh
    m = trimesh.load_mesh(str(pfad), process=False)
    if isinstance(m, trimesh.Scene):
        m = m.to_mesh()
    return np.asarray(m.vertices, dtype=float), np.asarray(m.faces, dtype=np.int64)


# -- Szene bauen --------------------------------------------------------------

def baue_szene(bericht_pfad: Path, projekt: Path, gesuchte_keys: list[str],
               budget_beteiligt=BUDGET_BETEILIGT, budget_kontext=BUDGET_KONTEXT) -> Szene:
    review = Path(bericht_pfad).resolve().parent
    mp = machine_pfad(projekt)
    mdata = _lade_machine(mp)
    specs = {b['key']: b for b in mdata.get('bodies', [])}
    szene = Szene(maschine_name=mdata.get('name', ''), maschine_revision=mdata.get('revision', ''),
                  maschine_pfad=str(mp) if mp else '')
    mdir = Path(mp).parent if mp else projekt

    beteiligt: list[Koerper] = []
    for key in gesuchte_keys:
        spec = specs.get(key)
        datei = None
        quelle = ''
        if spec is not None:
            datei = (mdir / spec['file']).resolve()
            quelle = 'maschine'
        else:
            kand = review / f'{safe_key(key)}.stl'
            if kand.exists():
                datei = kand
                quelle = 'prüfteil'
        if datei is None or not Path(datei).exists():
            szene.warnungen.append(f'Körper {key!r}: keine Geometrie gefunden '
                                   f'(weder in machine.json noch als {safe_key(key)}.stl im Review-Ordner)')
            continue
        k = Koerper(key=key, name=(spec or {}).get('name', key), rolle=(spec or {}).get('role') or '',
                    beteiligt=True, moving=bool((spec or {}).get('moving', False)),
                    quelle=quelle, datei=str(datei))
        beteiligt.append(k)

    # Geometrie der beteiligten Körper laden
    anteil = max(1, budget_beteiligt // max(1, len(beteiligt)))
    for k in beteiligt:
        try:
            v, f = _lade_stl(Path(k.datei))
        except Exception as e:                                   # pragma: no cover
            szene.warnungen.append(f'Körper {k.key!r}: {e}')
            continue
        k.faces_original = len(f)
        v, f = reduziere(v, f, anteil)
        k.mesh = (v, f)
        k.faces = len(f)
        k.bounds = [v.min(axis=0).tolist(), v.max(axis=0).tolist()]
        szene.koerper.append(k)

    if not szene.koerper:
        return szene

    # Kontext: Maschinenkörper in der Nähe, stark reduziert
    lo = np.min([k.bounds[0] for k in szene.koerper], axis=0)
    hi = np.max([k.bounds[1] for k in szene.koerper], axis=0)
    mitte = (lo + hi) / 2.0
    kandidaten = []
    for key, spec in specs.items():
        if szene.by_key(key) is not None or not spec.get('boundsMm'):
            continue
        b = np.asarray(spec['boundsMm'], dtype=float)
        d = float(np.linalg.norm(np.maximum(np.maximum(b[0] - hi, lo - b[1]), 0.0)))
        if d <= KONTEXT_RADIUS_MM:
            kandidaten.append((d, float(np.linalg.norm((b[0] + b[1]) / 2 - mitte)), key, spec))
    kandidaten.sort(key=lambda t: (t[0], t[1]))
    rest = budget_kontext
    for _d, _c, key, spec in kandidaten:
        if rest <= 0:
            break
        datei = (mdir / spec['file']).resolve()
        if not datei.exists():
            continue
        try:
            v, f = _lade_stl(datei)
        except Exception:                                        # pragma: no cover
            continue
        n0 = len(f)
        v, f = reduziere(v, f, min(rest, KONTEXT_MAX_FACES))
        if len(f) == 0:
            continue
        rest -= len(f)
        szene.koerper.append(Koerper(key=key, name=spec.get('name', key), rolle=spec.get('role') or '',
                                     beteiligt=False, moving=bool(spec.get('moving', False)),
                                     quelle='maschine', datei=str(datei), mesh=(v, f),
                                     bounds=[v.min(axis=0).tolist(), v.max(axis=0).tolist()],
                                     faces_original=n0, faces=len(f)))
    return szene


def huell_schnitt(a: Koerper | None, b: Koerper | None):
    """Schnitt der beiden Hüllquader – Behelfsmarke für Durchdringungen."""
    if a is None or b is None or a.bounds is None or b.bounds is None:
        return None
    lo = np.maximum(np.asarray(a.bounds[0]), np.asarray(b.bounds[0]))
    hi = np.minimum(np.asarray(a.bounds[1]), np.asarray(b.bounds[1]))
    if np.any(hi <= lo):
        mitte = (np.asarray(a.bounds[0]) + np.asarray(a.bounds[1]) +
                 np.asarray(b.bounds[0]) + np.asarray(b.bounds[1])) / 4.0
        return {'min': (mitte - 2.0).tolist(), 'max': (mitte + 2.0).tolist(), 'genau': False}
    return {'min': lo.tolist(), 'max': hi.tolist(), 'genau': True}
