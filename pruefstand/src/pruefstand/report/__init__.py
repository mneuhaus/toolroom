"""HTML-Bericht mit 3D-Viewer aus dem Bericht-JSON des Prüfstands.

    uv run python -m pruefstand.report var/review/pruefstand.json -o bericht.html

oder aus Python:

    from pruefstand.report import build_report
    build_report('var/review/pruefstand.json', 'var/review/pruefstand.html')
"""
from __future__ import annotations

from pathlib import Path


def build_report(report_json, out_html=None) -> Path:
    """Bericht-JSON zu einer eigenständigen HTML-Datei machen. Gibt den Pfad zurück."""
    from .html import build
    p = Path(report_json)
    if out_html is None:
        out_html = p.with_suffix('.html')
    return build(p, out_html)


__all__ = ['build_report']
