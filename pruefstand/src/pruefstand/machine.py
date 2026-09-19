"""Machine / State / Scene: Maschinenkontext aus machine.json."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from .body import Body, load_mesh, load_step
from .frame import Frame

SCHEMA = 'pruefstand.machine/1'


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


class State:
    """Werte aller Motions.

    Eine Motion ist entweder eine Verschiebung (`kind: translation`) oder eine Drehung
    (`kind: rotation`, mit `axis` und `origin` im Frame). Welche Körper eine Motion
    bewegt, sagt ihr `applies_to`; fehlt das, gilt sie -- wie bisher -- für alle Körper
    mit `moving: true`. Erst damit lassen sich zwei unabhängige Bewegungen in einer
    Maschine führen: der Hub schiebt die Wagen, der Schwenk dreht nur die Schale.
    """

    def __init__(self, machine: "Machine", values: dict):
        self.machine = machine
        self.values = dict(values)

    # -- eine Motion als 4x4 --------------------------------------------
    def _matrix(self, name: str, val: float) -> np.ndarray:
        m = self.machine.motions[name]
        art = m.get('kind', 'translation')
        frame = self.machine.frame(m.get('frame', 'local'))
        axis = np.asarray(m.get('axis', (0, 0, 1)), dtype=float).reshape(3)
        out = np.eye(4)
        if art == 'translation':
            out[:3, 3] = frame.direction_to_world(axis * float(val))
            return out
        if art == 'rotation':
            u = frame.direction_to_world(axis)
            n = float(np.linalg.norm(u))
            if n < 1e-12:
                raise ValueError(f'Motion {name!r}: Achse hat Länge 0')
            u = u / n
            p = frame.to_world(np.asarray(m.get('origin', (0, 0, 0)), dtype=float).reshape(1, 3))[0]
            t = np.radians(float(val))
            k = np.array([[0, -u[2], u[1]], [u[2], 0, -u[0]], [-u[1], u[0], 0]])
            r = np.eye(3) + np.sin(t) * k + (1 - np.cos(t)) * (k @ k)   # Rodrigues
            out[:3, :3] = r
            out[:3, 3] = p - r @ p
            return out
        raise NotImplementedError(f'Motion-Art {art!r} unbekannt (translation, rotation)')

    def _betrifft(self, name: str, body: Body) -> bool:
        ziel = self.machine.motions[name].get('applies_to')
        if ziel is None:
            return bool(body.moving)
        return body.key in set(ziel)

    def matrix_for(self, body: Body) -> np.ndarray:
        """Gesamttransform für einen Körper -- nur die Motions, die ihn betreffen."""
        out = np.eye(4)
        for name, val in self.values.items():
            if val == 0 or not self._betrifft(name, body):
                continue
            out = self._matrix(name, val) @ out
        return out

    def displacement(self) -> np.ndarray:
        """Reine Verschiebung aller Motions -- nur solange keine Drehung im Spiel ist."""
        d = np.zeros(3)
        for name, val in self.values.items():
            m = self.machine.motions[name]
            if m.get('kind', 'translation') != 'translation':
                if val == 0:
                    continue                 # eine Drehung um 0 verschiebt nichts
                raise NotImplementedError(
                    f'Motion {name!r} ist eine Drehung -- displacement() gibt es dafür nicht, '
                    'matrix_for(body) benutzen')
            axis = np.asarray(m.get('axis', (0, 0, 1)), dtype=float)
            frame = self.machine.frame(m.get('frame', 'local'))
            d = d + frame.direction_to_world(axis * float(val))
        return d

    def apply(self, body: Body) -> Body:
        # Vor den Abkürzungen merken: auch eine Pose, die nichts verschiebt (alle
        # Motions auf Vorgabe), ist die Pose, in der gemessen wurde.
        from . import results
        results.merke_pose(self.values)
        if getattr(body, 'displaced', False):
            return body
        mat = self.matrix_for(body)
        if np.allclose(mat, np.eye(4)):
            return body
        if np.allclose(mat[:3, :3], np.eye(3)):
            out = body.translated(mat[:3, 3])
        else:
            out = body.transformed(mat)
        out.displaced = True
        return out

    def as_dict(self):
        return dict(self.values)

    def __repr__(self):
        return f'State({self.values})'


class Scene:
    """Alle Körper der Maschine in einer Pose."""

    def __init__(self, machine: "Machine", state: State, bodies: list[Body]):
        self.machine = machine
        self.state = state
        self.bodies = list(bodies)

    @property
    def fixed(self) -> list[Body]:
        return [b for b in self.bodies if not b.moving]

    @property
    def moving(self) -> list[Body]:
        return [b for b in self.bodies if b.moving]

    def keys(self) -> list[str]:
        return [b.key for b in self.bodies]

    def without(self, *keys) -> "Scene":
        drop = set()
        for k in keys:
            drop.update(k if isinstance(k, (list, tuple, set)) else [k])
        return Scene(self.machine, self.state, [b for b in self.bodies if b.key not in drop])

    def only(self, *keys) -> "Scene":
        keep = []
        for k in keys:
            keep.extend(k if isinstance(k, (list, tuple, set)) else [k])
        keep = set(keep)
        return Scene(self.machine, self.state, [b for b in self.bodies if b.key in keep])

    def displace(self, body: Body) -> Body:
        return self.state.apply(body)

    def __iter__(self):
        return iter(self.bodies)

    def __len__(self):
        return len(self.bodies)

    def __repr__(self):
        return f'Scene({self.state.values}, {len(self.bodies)} Körper)'


class Machine:
    def __init__(self, data: dict, path: Path):
        self.data = data
        self.path = Path(path)
        self.dir = self.path.parent
        self.name = data.get('name', '')
        self.revision = data.get('revision', '')
        self.frames = {k: Frame.from_dict(v) for k, v in data.get('frames', {}).items()}
        self.motions = dict(data.get('motions', {}))
        self._specs = {b['key']: b for b in data.get('bodies', [])}
        self._cache: dict[str, Body] = {}
        self._scenes: dict[tuple, Scene] = {}

    # -- laden -----------------------------------------------------------
    @classmethod
    def load(cls, path) -> "Machine":
        path = Path(path).resolve()
        data = json.loads(path.read_text())
        if data.get('schema') != SCHEMA:
            raise ValueError(f'unerwartetes Schema {data.get("schema")!r}, erwartet {SCHEMA!r}')
        return cls(data, path)

    def frame(self, name='local') -> Frame:
        if name not in self.frames:
            if str(name).lower() == 'world':
                return Frame.identity()      # Weltsystem gilt immer, auch ungenannt
            raise KeyError(f'Frame {name!r} unbekannt: {list(self.frames)}')
        return self.frames[name]

    def keys(self) -> list[str]:
        return list(self._specs)

    def body(self, key) -> Body:
        if key in self._cache:
            return self._cache[key]
        spec = self._specs.get(key)
        if spec is None:
            raise KeyError(f'Körper {key!r} nicht in {self.path}')
        f = (self.dir / spec['file']).resolve()
        fmt = spec.get('format', 'stl').lower()
        if fmt == 'stl':
            b = load_mesh(f, key=key, moving=spec.get('moving', False))
        elif fmt == 'step':
            parts = load_step(f, moving=spec.get('moving', False))
            sel = spec.get('solid')
            if sel is None:
                b = parts.one(key=key, moving=spec.get('moving', False))
            elif isinstance(sel, int):
                b = parts.all()[sel]
                b.key = key
            else:
                b = parts.find(sel)
                b.key = key
        else:
            raise ValueError(f'unbekanntes Format {fmt!r}')
        b.name = spec.get('name', key)
        b.role = spec.get('role')
        b.moving = bool(spec.get('moving', False))
        self._cache[key] = b
        return b

    def bodies(self) -> list[Body]:
        return [self.body(k) for k in self._specs]

    # -- Posen -----------------------------------------------------------
    def state(self, **motions) -> State:
        values = {}
        for name, m in self.motions.items():
            val = motions.get(name, m.get('default', 0))
            lo, hi = m.get('range', [-np.inf, np.inf])
            if not (lo - 1e-9 <= val <= hi + 1e-9):
                raise ValueError(f'Motion {name}={val} außerhalb {lo}…{hi}')
            values[name] = float(val)
        unknown = set(motions) - set(self.motions)
        if unknown:
            raise ValueError(f'unbekannte Motions: {sorted(unknown)}')
        return State(self, values)

    def scene_at(self, state: State) -> Scene:
        key = tuple(sorted(state.values.items()))
        sc = self._scenes.get(key)
        if sc is None:
            sc = Scene(self, state, [state.apply(self.body(k)) for k in self._specs])
            self._scenes[key] = sc
        return Scene(self, sc.state, sc.bodies)

    def scene(self, **motions) -> Scene:
        return self.scene_at(self.state(**motions))

    # -- bauen -----------------------------------------------------------
    @classmethod
    def from_manifest(cls, manifest_json, out_dir, frames, motions, name, revision,
                      units='mm', note=None, file_pattern='../local/{key}.stl') -> "Machine":
        manifest_json = Path(manifest_json).resolve()
        out_dir = Path(out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = json.loads(manifest_json.read_text())
        bodies = []
        for r in rows:
            rel = file_pattern.format(key=r['key'])
            f = (out_dir / rel).resolve()
            if not f.exists():
                raise FileNotFoundError(f'{f} fehlt (Körper {r["key"]})')
            bodies.append({
                'key': r['key'],
                'name': r.get('name', r['key']),
                'role': r.get('role'),
                'moving': bool(r.get('moving', False)),
                'file': rel,
                'format': 'stl',
                'sha256': _sha256(f),
                'boundsMm': r.get('boundsMm'),
                'volumeMm3': r.get('volumeMm3'),
            })
        data = {
            'schema': SCHEMA,
            'name': name,
            'revision': revision,
            'units': units,
            'frames': {k: (v.as_dict() if isinstance(v, Frame) else v) for k, v in frames.items()},
            'motions': motions,
            'bodies': bodies,
            'source': {
                'kind': 'manifest',
                'path': os.path.relpath(manifest_json, out_dir),
                'built': _dt.datetime.now().isoformat(timespec='seconds'),
                'note': note or '',
            },
        }
        out = out_dir / 'machine.json'
        out.write_text(json.dumps(data, indent=2))
        return cls.load(out)

    def __repr__(self):
        return f'Machine({self.name!r} {self.revision}, {len(self._specs)} Körper)'
