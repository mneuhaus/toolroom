"""pruefstand CLI."""
from __future__ import annotations

import argparse
import runpy
import subprocess
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='pruefstand')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run', help='pytest über den spec-Ordner eines Projekts')
    r.add_argument('projekt')
    r.add_argument('pytest_args', nargs=argparse.REMAINDER)
    m = sub.add_parser('machine', help='build_machine.py ausführen')
    m.add_argument('script')
    a = ap.parse_args(argv)
    if a.cmd == 'run':
        p = Path(a.projekt)
        target = p if p.name == 'spec' else p / 'spec'
        return subprocess.call([sys.executable, '-m', 'pytest', str(target), '-q', *a.pytest_args])
    runpy.run_path(a.script, run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
