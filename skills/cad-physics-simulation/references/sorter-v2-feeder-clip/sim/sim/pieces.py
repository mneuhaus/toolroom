"""LEGO piece library: LDraw part -> visual mesh, convex collision pieces, mass.

Reads .dat files from an LDraw library (SIM_LDRAW or --ldraw), follows subfile
references recursively, applies the transforms, converts LDU (0.4 mm, Y down)
to metres Z up, welds the triangle soup, and writes:

  assets/pieces/<part>/visual.stl        the part as one mesh
  assets/pieces/<part>/col/<k>.stl       convex pieces (CoACD) for contact
  assets/pieces/library.json             {part: {name, mass_kg, com, fullinertia, bounds, hulls, ...}}

The body inertia is the convex hull's at uniform density scaled to the mass
(com and the six fullinertia terms in the part frame), so contact never sees
a thin hull piece with a near-zero inertia of its own.

Mass is ABS density (1.05 g/cm3) times an estimated solid volume: LDraw parts
are open shells, so it is a fraction of the convex hull (a 2x4 brick lands at
about 2.4 g against 2.3 g real). A per-part mass table can replace this.

Usage: python -m sim.pieces [--parts 3001,3003,...] [--ldraw DIR] [--threshold 0.05]
The default set is a starter of common bricks, plates, slopes and tiles.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import coacd
import numpy as np
import trimesh

from sim.assets import asset_root

coacd.set_log_level("error")

LDU = 0.0004  # metres per LDraw unit
LD_TO_Z_UP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], dtype=float)
ABS_DENSITY = 1050.0  # kg/m3
SOLID_FRACTION = 0.45  # of the convex hull, for the open LDraw shells

STARTER = [
    "3001", "3002", "3003", "3004", "3005", "3009", "3010", "2357", "3622",   # bricks
    "3020", "3021", "3022", "3023", "3024", "3034", "3035", "3623", "3710", "3795",  # plates
    "3039", "3040", "3660", "3665", "3298", "3747",                            # slopes
    "3068", "3069", "3070", "2412", "3794",                                    # tiles, jumper
    "3062", "4073", "3941", "6141",                                            # round
    "3700", "3701", "3673", "2780", "32062", "3705", "4519",                   # technic
    "4070", "3005", "87087", "3245", "2877", "4162", "3666",                   # misc
]


class LDraw:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.dirs = [self.root / d for d in ("parts", "p", "parts/s", "p/48", "p/8")]
        self._index: dict[str, Path] | None = None
        self.colours = self._load_colours(self.root / "LDConfig.ldr")

    def _find(self, name: str) -> Path | None:
        name = name.replace("\\", "/").lower()
        if self._index is None:
            self._index = {}
            for d in self.dirs:
                if not d.is_dir():
                    continue
                for f in os.listdir(d):
                    fl = f.lower()
                    if not fl.endswith(".dat"):
                        continue
                    rel = d.relative_to(self.root).as_posix()
                    key = fl if rel in ("parts", "p") else f"{d.name}/{fl}"
                    self._index.setdefault(key, d / f)
                    self._index.setdefault(fl, d / f)
        return self._index.get(name) or self._index.get(os.path.basename(name))

    def title(self, part: str) -> str | None:
        for _ in range(5):
            path = self._find(part + ".dat")
            if not path:
                return None
            first = path.open(encoding="utf-8", errors="replace").readline().strip()
            t = first[2:].strip() if first.startswith("0") else first
            m = re.match(r"~Moved to (\S+)", t)
            if not m:
                return t
            part = m.group(1)
        return t

    @staticmethod
    def _load_colours(path: Path) -> dict[int, dict]:
        cols = {}
        rx = re.compile(r"!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9A-Fa-f]{6})")
        for line in path.open(encoding="utf-8", errors="replace"):
            m = rx.search(line)
            if m:
                name, code, val = m.groups()
                cols[int(code)] = {"name": name, "rgb": [int(val[i:i + 2], 16) / 255 for i in (0, 2, 4)]}
        return cols

    def _parse(self, path: Path, matrix: np.ndarray, tris: list, depth: int = 0) -> None:
        if depth > 12:
            return
        for line in path.open(encoding="utf-8", errors="replace"):
            p = line.split()
            if not p:
                continue
            t = p[0]
            if t == "1" and len(p) >= 15:
                x, y, z = (float(v) for v in p[2:5])
                a, b, c, d, e, f, g, h, i = (float(v) for v in p[5:14])
                sub = np.array([[a, b, c, x], [d, e, f, y], [g, h, i, z], [0, 0, 0, 1]])
                subpath = self._find(" ".join(p[14:]))
                if subpath:
                    self._parse(subpath, matrix @ sub, tris, depth + 1)
            elif t in ("3", "4") and len(p) >= (11 if t == "3" else 14):
                n = 3 if t == "3" else 4
                pts = [matrix @ np.array([float(p[2 + 3 * k]), float(p[3 + 3 * k]), float(p[4 + 3 * k]), 1.0]) for k in range(n)]
                pts = [q[:3] for q in pts]
                tris.append((pts[0], pts[1], pts[2]))
                if n == 4:
                    tris.append((pts[0], pts[2], pts[3]))

    def mesh(self, part: str) -> trimesh.Trimesh:
        path = self._find(part + ".dat")
        if not path:
            raise FileNotFoundError(part)
        tris: list = []
        self._parse(path, np.eye(4), tris)
        v = np.array(tris, dtype=float).reshape(-1, 3)
        v = (LD_TO_Z_UP[:3, :3] @ v.T).T * LDU
        f = np.arange(len(v)).reshape(-1, 3)
        m = trimesh.Trimesh(v, f, process=True)  # welds duplicate vertices
        m.merge_vertices(merge_tex=True, merge_norm=True)
        m.fix_normals()
        return m


def inertia_props(mesh: trimesh.Trimesh, mass: float) -> tuple[list[float], list[float]]:
    """Centre of mass and full inertia [ixx iyy izz ixy ixz iyz] about it, for the
    convex hull at uniform density scaled to `mass`."""
    hull = mesh.convex_hull
    hull.density = mass / hull.volume
    com = hull.center_mass
    I = hull.moment_inertia  # about the centre of mass, mesh frame
    return [float(x) for x in com], [float(I[0, 0]), float(I[1, 1]), float(I[2, 2]),
                                     float(I[0, 1]), float(I[0, 2]), float(I[1, 2])]


def decompose(mesh: trimesh.Trimesh, threshold: float, max_hulls: int) -> list[trimesh.Trimesh]:
    """A few convex pieces per part. LDraw parts carry every stud and the hollow
    underside, which a fine decomposition turns into dozens of hulls; contact
    cost scales with that, so the count is capped and the studs get absorbed."""
    m = coacd.Mesh(np.asarray(mesh.vertices, dtype=np.float64), np.asarray(mesh.faces, dtype=np.int64))
    parts = coacd.run_coacd(m, threshold=threshold, max_convex_hull=max_hulls, preprocess_mode="auto",
                            resolution=2000, seed=0)
    return [trimesh.Trimesh(v, f, process=False) for v, f in parts]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default=",".join(STARTER))
    ap.add_argument("--ldraw", default=os.environ.get("SIM_LDRAW", str(Path.home() / "Documents" / "ldraw")))
    ap.add_argument("--threshold", type=float, default=0.1, help="CoACD concavity threshold")
    ap.add_argument("--max-hulls", type=int, default=6, help="convex pieces per part, at most")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--props-only", action="store_true", help="recompute mass and inertia for parts already built")
    args = ap.parse_args()

    lib = LDraw(Path(args.ldraw))
    out = asset_root() / "pieces"
    out.mkdir(parents=True, exist_ok=True)
    libfile = out / "library.json"
    library = json.loads(libfile.read_text()) if libfile.exists() else {}
    for part in dict.fromkeys(p.strip() for p in args.parts.split(",") if p.strip()):
        d = out / part
        if args.props_only:
            if part not in library:
                continue
            m = trimesh.load(d / "visual.stl", force="mesh", process=False)
            mass = library[part]["mass_kg"]
            library[part]["com"], library[part]["fullinertia"] = inertia_props(m, mass)
            continue
        if part in library and (d / "visual.stl").exists() and not args.force:
            continue
        t0 = time.time()
        try:
            m = lib.mesh(part)
        except FileNotFoundError:
            print(f"{part}: not in the library")
            continue
        d.mkdir(parents=True, exist_ok=True)
        m.export(d / "visual.stl", file_type="stl")
        hull_vol = m.convex_hull.volume
        # LDraw parts are open shells, so the mesh volume is meaningless; a
        # brick is roughly 0.45 of its convex hull by weight (2x4 brick: 2.3 g).
        vol = abs(m.volume) if m.is_watertight else hull_vol * SOLID_FRACTION
        hulls = decompose(m, args.threshold, args.max_hulls)
        col = d / "col"
        col.mkdir(exist_ok=True)
        for f in col.glob("*.stl"):
            f.unlink()
        for k, h in enumerate(hulls):
            h.export(col / f"{k:03d}.stl", file_type="stl")
        mass = round(vol * ABS_DENSITY, 6)
        com, fullinertia = inertia_props(m, mass)
        library[part] = {
            "name": lib.title(part),
            "mass_kg": mass,
            "com": com,
            "fullinertia": fullinertia,
            "volume_m3": vol,
            "watertight": bool(m.is_watertight),
            "bounds": np.round(m.bounds, 6).tolist(),
            "faces": int(len(m.faces)),
            "hulls": len(hulls),
        }
        libfile.write_text(json.dumps(library, indent=1, sort_keys=True))
        print(f"{part} {library[part]['name']}: {len(m.faces)} faces, {library[part]['mass_kg'] * 1000:.2f} g, "
              f"{len(hulls)} hulls, watertight={m.is_watertight}, {time.time() - t0:.1f}s")
    libfile.write_text(json.dumps(library, indent=1, sort_keys=True))
    print(f"library: {len(library)} parts -> {libfile}")


if __name__ == "__main__":
    main()
