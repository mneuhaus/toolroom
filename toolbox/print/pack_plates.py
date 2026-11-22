"""Packs print parts onto Bambu A1 plates by their real outlines: each part's STL (print_prep.py, build direction up)
is projected onto the bed as a raster; parts go one by one, turned about Z in STEP_DEG steps, to the lowest free spot
(then leftmost) of the first plate with room, so small parts land inside open frames.
Each part claims its footprint plus REACH mm around its downward faces off the bed (tree supports grow that far
beyond the outline; Bambu refuses a plate whose support paths cross another part's paths). Claims keep GAP mm to each
other and footprints MARGIN mm to the bed edge (a claim may pass the edge: R59B spans 238 mm, its supports grow inward).
Several part orders are tried (by area, by span, shuffles of the big parts); the layout with the fewest plates, then
the most uneven fill, wins. Writes the turned STLs, one plate-3mf.mjs spec per plate ("nested": the outlines are
checked here, not the boxes) and a layout picture per plate (footprints black, support claims grey).
Usage: pack_plates.py stl_dir out_dir part [part ...]"""
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation
from scipy.signal import fftconvolve

BED = 256  # mm A1 bed
MARGIN = 3  # mm Free edge of the bed
GAP = 6  # mm Between the claims of two parts
REACH = 10  # mm Tree supports beyond the outline (support_check.py, rev 14 plates: up to 9.5)
OVERHANG_NZ = -0.7  # Downward faces steeper than 45 deg from vertical get supports (Bambu threshold 30 deg)
RES = 1.0  # mm Raster cell
STEP_DEG = 15  # deg Turns tried about Z
BIG = 150  # mm Parts spanning more go first, in shuffled orders
SHUFFLES, SEED = 40, 1
CELLS, EDGE, PAD = int(BED / RES), int(MARGIN / RES), int(math.ceil((GAP + REACH) / RES))


def read_stl(path):
    data = np.fromfile(path, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), offset=84)
    return data["v"].astype(float)


def write_stl(path, tris):
    tri = tris.astype(np.float32)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(tri), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as f:
        f.write(b"print part, packed".ljust(80, b" ") + struct.pack("<I", len(tri)))
        rec.tofile(f)


def turned(tris, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    out = tris.copy()
    out[..., 0], out[..., 1] = c * tris[..., 0] - s * tris[..., 1], s * tris[..., 0] + c * tris[..., 1]
    return out


def raster(tris, lo, shape):
    """Cells covered by the triangles' projection, row = y, column = x, cell (0, 0) at lo."""
    img = Image.new("1", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(img)
    for t in (tris[:, :, :2] - lo) / RES:
        draw.polygon([tuple(p) for p in t], fill=1, outline=1)
    return np.array(img, dtype=bool)


def overhanging(tris):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nz = n[:, 2] / np.maximum(np.linalg.norm(n, axis=1), 1e-12)
    return tris[(nz < OVERHANG_NZ) & (tris[:, :, 2].min(axis=1) > tris[:, :, 2].min() + 0.05)]


def disk(r):
    n = int(math.ceil(r / RES))
    y, x = np.mgrid[-n:n + 1, -n:n + 1]
    return x * x + y * y <= n * n


def shape(tris, deg):
    """Footprint, claim and halo (claim grown by GAP) of the part turned by deg, the last two padded by PAD cells;
    None if it does not fit the bed in this turn."""
    tris = turned(tris, deg)
    lo = tris[:, :, :2].reshape(-1, 2).min(axis=0)
    size = tris[:, :, :2].reshape(-1, 2).max(axis=0) - lo
    cells = tuple(int(math.ceil(v / RES)) + 1 for v in size[::-1])
    if max(cells) > CELLS - 2 * EDGE:
        return None
    mask = raster(tris, lo, cells)
    claim = np.pad(mask, PAD)
    down = overhanging(tris)
    if len(down):
        claim |= binary_dilation(np.pad(raster(down, lo, cells), PAD), structure=disk(REACH))
    halo = binary_dilation(claim, structure=disk(GAP))
    return {"deg": deg, "mask": mask, "claim": claim, "halo": halo.astype(float), "size": size}


def pack(order, shapes):
    plates = []
    for name in order:
        best = None
        for plate in plates + [None]:
            occ = plate["claims"] if plate else np.zeros((CELLS + 2 * PAD, CELLS + 2 * PAD), dtype=bool)
            for s in shapes[name]:
                h, w = s["mask"].shape
                hits = fftconvolve(occ.astype(float), s["halo"][::-1, ::-1], mode="valid")
                free = hits[EDGE:CELLS - EDGE - h + 1, EDGE:CELLS - EDGE - w + 1] < 0.5
                if not free.any():
                    continue
                rows, cols = np.nonzero(free)
                i = np.lexsort((cols, rows))[0]
                spot = (rows[i] + EDGE, cols[i] + EDGE)
                if best is None or spot < best[1]:
                    best = (s, spot)
            if best:
                if plate is None:
                    plate = {"claims": occ, "occ": np.zeros((CELLS, CELLS), dtype=bool), "parts": []}
                    plates.append(plate)
                break
        if not best:
            raise SystemExit(f"{name} fits no empty plate")
        s, (row, col) = best
        h, w = s["mask"].shape
        plate["occ"][row:row + h, col:col + w] |= s["mask"]
        plate["claims"][row:row + h + 2 * PAD, col:col + w + 2 * PAD] |= s["claim"]
        plate["parts"].append({"name": name, "deg": s["deg"], "at": [round(col * RES + s["size"][0] / 2, 3),
                                                                      round(row * RES + s["size"][1] / 2, 3)]})
    return plates


def main(stl_dir, out_dir, *parts):
    out = Path(out_dir)
    (out / "stl").mkdir(parents=True, exist_ok=True)
    meshes = {name: read_stl(Path(stl_dir) / f"{name}.stl") for name in parts}
    shapes = {name: [s for deg in range(0, 360, STEP_DEG) if (s := shape(tris, deg))] for name, tris in meshes.items()}
    area = {n: shapes[n][0]["mask"].sum() for n in parts}
    span = {n: max(shapes[n][0]["size"]) for n in parts}
    orders = {"area": sorted(parts, key=lambda n: -area[n]), "span": sorted(parts, key=lambda n: -span[n]),
              "span then area": sorted(parts, key=lambda n: (-round(span[n] / 50), -area[n]))}
    # Shuffles of the big parts (span over BIG mm) ahead of the small ones by area: the big ones decide the plate count
    big = [n for n in orders["area"] if span[n] > BIG]
    rng = np.random.default_rng(SEED)
    for k in range(SHUFFLES):
        orders[f"shuffle {k}"] = list(rng.permutation(big)) + [n for n in orders["area"] if n not in big]
    # Fewest plates, then the plates as unevenly full as possible (full plates plus one easy rest plate)
    score = lambda plates: (len(plates), -sum(p["occ"].mean() ** 2 for p in plates))
    results = {key: pack(order, shapes) for key, order in orders.items()}
    for key, plates in sorted(results.items(), key=lambda kv: score(kv[1]))[:5]:
        print(f"order by {key}: {len(plates)} plates, fill " + " ".join(f"{p['occ'].mean() * 100:.0f}" for p in plates))
    key = min(results, key=lambda k: score(results[k]))
    print(f"using order by {key}")
    for n, plate in enumerate(results[key], 1):
        tag = f"S2_A1-{n:02d}"
        specs = []
        for p in plate["parts"]:
            stl = out / "stl" / f"{p['name']}_z{p['deg']}.stl"
            write_stl(stl, turned(meshes[p["name"]], p["deg"]))
            # A lone part goes to the bed centre (the diagonal posts then keep 8 mm free at each corner)
            at = [BED / 2, BED / 2] if len(plate["parts"]) == 1 else p["at"]
            specs.append({"name": p["name"], "stl": str(stl.resolve()), "at": at})
        json.dump({"nested": True, "out": str((out / f"{tag}.3mf").resolve()), "bed": [BED, BED], "parts": specs},
                  open(out / f"{tag}.json", "w"), indent=1)
        picture = np.full((CELLS, CELLS), 255, dtype=np.uint8)
        picture[plate["claims"][PAD:-PAD, PAD:-PAD]] = 190
        picture[plate["occ"]] = 0
        Image.fromarray(picture[::-1]).save(out / f"{tag}_layout.png")
        print(f"{tag}: {', '.join(p['name'] for p in plate['parts'])}  ({plate['occ'].mean() * 100:.0f} % of the bed)")


if __name__ == "__main__":
    main(*sys.argv[1:])
