"""Live-push loop for the OCP standalone viewer.

The standalone viewer (python -m ocp_vscode) relays pushes to connected
browser tabs but keeps no state — a reloaded tab shows the OCP logo until
the next push. This loop closes that gap:

  - rebuilds + pushes whenever a watched .py file changes
  - re-pushes the cached assembly every INTERVAL seconds, so a freshly
    (re)loaded tab is populated within a few seconds

Usage:  uv run watch.py  (viewer server must be running on port 3939)
"""

import runpy
import sys
import time
import traceback
from pathlib import Path

from cad_khana.viewer import push

SCRIPT = Path(__file__).parent / (sys.argv[1] if len(sys.argv) > 1 else "assembly.py")
INTERVAL = 5.0  # seconds between keep-alive pushes


def mtimes() -> tuple:
    # every .py in the project dir except this watcher
    return tuple(
        p.stat().st_mtime
        for p in sorted(SCRIPT.parent.glob("*.py"))
        if p.name != "watch.py"
    )


def build():
    print(f"[watch] building {SCRIPT.name} ...", flush=True)
    t0 = time.time()
    # purge project-local modules: runpy reruns the SCRIPT, but its
    # `import foo` of sibling files would come from sys.modules' cache
    # and silently serve stale geometry
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and Path(f).parent == SCRIPT.parent:  # project root only, NOT .venv
            del sys.modules[name]
    module = runpy.run_path(str(SCRIPT))  # __main__ guard keeps check() out
    assembly = module["assembly"]
    print(f"[watch] built in {time.time() - t0:.1f}s", flush=True)
    return assembly


def main():
    stamp = mtimes()
    assembly = build()
    while True:
        try:
            if mtimes() != stamp:
                stamp = mtimes()
                assembly = build()
            push(assembly)
        except Exception:
            traceback.print_exc()
            print("[watch] push/build failed, retrying ...", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
