"""Convex decomposition for the parts pieces touch.

MuJoCo collides a mesh as its convex hull, so the concave parts a piece rides
on (stator rings, output guides, the bulk cap) are split into convex pieces
with CoACD. Output: assets/machine/collision/<mesh id>/<k>.stl, picked up by
sim.scene when present.

Usage: python -m sim.collide [--parts "Rotor - Faceted,Stator,..."] [--threshold 0.04]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import coacd

coacd.set_log_level("error")
import numpy as np
import trimesh

from sim.assets import asset_root

DEFAULT_PARTS = ["Rotor - Faceted", "Stator", "Output Guide", "rotor cap", "Bulk Cap B"]


def decompose(mesh: trimesh.Trimesh, threshold: float) -> list[trimesh.Trimesh]:
    m = coacd.Mesh(np.asarray(mesh.vertices, dtype=np.float64), np.asarray(mesh.faces, dtype=np.int64))
    parts = coacd.run_coacd(m, threshold=threshold, preprocess_mode="auto", resolution=2000, seed=0)
    return [trimesh.Trimesh(v, f, process=False) for v, f in parts]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default=",".join(DEFAULT_PARTS))
    ap.add_argument("--threshold", type=float, default=0.04, help="CoACD concavity threshold (lower = more pieces)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    machine = asset_root() / "machine"
    manifest = json.loads((machine / "manifest.json").read_text())
    wanted = [p.strip() for p in args.parts.split(",") if p.strip()]
    mesh_ids = sorted({o["mesh"] for o in manifest["occurrences"] if o["name"] in wanted})
    for mesh_id in mesh_ids:
        out = machine / "collision" / mesh_id
        if out.exists() and not args.force:
            print(f"{mesh_id} ({manifest['meshes'][mesh_id]['example']}): exists, skip")
            continue
        src = trimesh.load(machine / manifest["meshes"][mesh_id]["file"], force="mesh", process=False)
        t0 = time.time()
        parts = decompose(src, args.threshold)
        out.mkdir(parents=True, exist_ok=True)
        for f in out.glob("*.stl"):
            f.unlink()
        for k, p in enumerate(parts):
            p.export(out / f"{k:03d}.stl", file_type="stl")
        print(f"{mesh_id} ({manifest['meshes'][mesh_id]['example']}): {len(src.faces)} faces -> "
              f"{len(parts)} convex pieces in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
