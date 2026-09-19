"""Laufzeitkontext: aktuelles Projekt und aktueller Test (vom pytest-Plugin gesetzt)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Project:
    root: Path
    spec: Path
    review: Path

    @classmethod
    def from_spec_dir(cls, spec_dir: Path, review: str | None = None) -> "Project":
        spec_dir = Path(spec_dir).resolve()
        root = spec_dir.parent
        rev = (spec_dir / review).resolve() if review else (root / 'var' / 'review')
        rev.mkdir(parents=True, exist_ok=True)
        return cls(root=root, spec=spec_dir, review=rev)


_state = {'project': None, 'test_id': None}


def set_project(p: Project | None) -> None:
    _state['project'] = p


def project() -> Project | None:
    return _state['project']


def set_test_id(tid: str | None) -> None:
    _state['test_id'] = tid


def test_id() -> str | None:
    return _state['test_id']


def review_dir() -> Path | None:
    p = _state['project']
    return p.review if p is not None else None
