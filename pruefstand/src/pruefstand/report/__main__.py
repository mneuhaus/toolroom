"""CLI: `uv run python -m pruefstand.report <bericht.json> -o <ausgabe.html>`."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import build_report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='pruefstand.report',
                                 description='HTML-Bericht mit 3D-Viewer aus pruefstand.json bauen')
    ap.add_argument('bericht', help='Pfad zu pruefstand.json')
    ap.add_argument('-o', '--out', default=None, help='Ziel-HTML (Vorgabe: neben dem JSON)')
    a = ap.parse_args(argv)
    out = build_report(a.bericht, a.out)
    kb = Path(out).stat().st_size / 1024
    print(f'{out}  ({kb:.0f} KiB)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
