"""CAD export (glTF) -> per-part mesh assets + manifest.

The master assembly is exported from the CAD as one glTF in metres, Z up. This
turns it into what the simulation loads:

  assets/machine/manifest.json
  assets/machine/meshes/<id>.stl        one binary STL per unique mesh

The export names every part after its CAD part and re-tessellates the mesh
for every instance (same faces and bounds, different bytes), so instances are
deduplicated by part name, face count and local bounds, and a repeated part
shares one file. The loader's per-primitive split is folded back into one
occurrence per part instance.

manifest.json:
  source, units ("m"), up ("z")
  meshes:      {id: {file, faces, bounds [[min],[max]] (local), gltf_colors [[r,g,b,a],...]}}
  occurrences: [{name, mesh, xform (4x4 row-major, world), path [assembly names, root first],
                 material (key from sim.materials or null)}]

Usage: python -m sim.extract path/to/export.gltf [--out assets/machine] [--skip-fasteners]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import trimesh

from sim.assets import asset_root
from sim.materials import FASTENER, classify

# trimesh suffixes duplicate node names with _<6 hex>, and the export carries
# _<n> on some repeated parts.
_SUFFIX = re.compile(r"(_\d+)?_[0-9a-f]{6}$")


FASTENER_MAX_M = 0.03  # nothing bigger than 30 mm is a fastener


def base_name(node: str) -> tuple[str, int]:
    return _SUFFIX.sub("", node), 0


def gltf_color(mesh: trimesh.Trimesh):
    mat = getattr(mesh.visual, "material", None)
    c = getattr(mat, "baseColorFactor", None)
    if c is None:
        return None
    c = np.asarray(c, dtype=float)
    if c.max() > 1.0:
        c = c / 255.0
    return [round(float(x), 4) for x in c[:4]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("gltf")
    ap.add_argument("--out", default=None, help="default: <assets>/machine")
    ap.add_argument("--skip-fasteners", action="store_true", help="drop screws, nuts, inserts")
    args = ap.parse_args()

    out = Path(args.out) if args.out else asset_root() / "machine"
    meshdir = out / "meshes"
    meshdir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    scene = trimesh.load(args.gltf, force="scene", process=False)
    graph = scene.graph
    print(f"loaded {args.gltf} in {time.time() - t0:.1f}s: {len(graph.nodes)} nodes")

    parent = {child: p for p, child, _ in graph.to_edgelist()}

    def path_of(node: str) -> list[str]:
        chain = []
        n = node
        while n in parent:
            n = parent[n]
            chain.append(n)
        return list(reversed(chain))

    # Fold per-primitive nodes back into occurrences: same parent, same base
    # name, same transform.
    groups: dict[tuple, list[str]] = defaultdict(list)
    for node in graph.nodes_geometry:
        T, _ = graph.get(node)
        key = (parent.get(node), base_name(node), tuple(np.round(T, 6).ravel()))
        groups[key].append(node)
    print(f"{len(groups)} occurrences from {len(graph.nodes_geometry)} primitive nodes")

    meshes: dict[str, dict] = {}
    occurrences: list[dict] = []
    instances: dict[str, int] = defaultdict(int)
    skipped = 0
    skipped_names: dict[str, int] = defaultdict(int)
    for (par, (name, _), _), nodes in groups.items():
        T, _ = graph.get(nodes[0])
        prims = [graph.transforms.node_data[n]["geometry"] for n in sorted(nodes)]
        parts = [scene.geometry[g] for g in prims]
        merged = trimesh.util.concatenate(parts) if len(parts) > 1 else parts[0].copy()
        # A fastener is a small part with a fastener word in its name. The size
        # gate matters: "Top plate ... screw holes" is a 600 mm plate.
        if args.skip_fasteners and FASTENER.search(name) and merged.extents.max() < FASTENER_MAX_M:
            skipped += 1
            skipped_names[name] += 1
            continue
        sig = f"{name}|{len(merged.faces)}|{np.round(merged.bounds, 5).tolist()}"
        mesh_id = hashlib.sha1(sig.encode()).hexdigest()[:10]
        instances[name] += 1
        instance = instances[name]
        if mesh_id not in meshes:
            merged.export(meshdir / f"{mesh_id}.stl", file_type="stl")
            colors = []
            for g in prims:
                c = gltf_color(scene.geometry[g])
                if c is not None and c not in colors:
                    colors.append(c)
            meshes[mesh_id] = {
                "file": f"meshes/{mesh_id}.stl",
                "faces": int(len(merged.faces)),
                "bounds": np.round(merged.bounds, 6).tolist(),
                "gltf_colors": colors,
                "example": name,
            }
        path = path_of(nodes[0])
        occurrences.append({
            "name": name,
            "instance": instance,
            "mesh": mesh_id,
            "xform": np.round(T, 9).ravel().tolist(),
            "path": path,
            "material": classify(name, path),
        })

    occurrences.sort(key=lambda o: (o["path"], o["name"], o["instance"]))
    manifest = {
        "source": str(Path(args.gltf).name),
        "units": "m",
        "up": "z",
        "meshes": meshes,
        "occurrences": occurrences,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    if skipped_names:
        print("skipped as fasteners: " + ", ".join(f"{n} x{c}" for n, c in sorted(skipped_names.items())))
    faces = sum(m["faces"] for m in meshes.values())
    print(f"wrote {len(meshes)} unique meshes ({faces} faces), {len(occurrences)} occurrences, "
          f"{skipped} fasteners skipped, in {time.time() - t0:.1f}s -> {out}")


if __name__ == "__main__":
    main()
