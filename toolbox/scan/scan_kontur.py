"""Profile outline from a flatbed scan with a steel ruler beside it (extruded profile sections scanned at 2400 dpi).
The ruler's mm ticks give the scale (px/mm along the ruler, its linearity), the profile's cut face lies
on the glass, so the scan is a true-scale orthographic view of the section. Writes the material outline (outer contour
and the chambers as holes, sub-pixel iso-line at the level halfway between background and material) as a DXF in mm
(y up), a check overlay, and a table of the contours.

Limits: the scale is only measured along the ruler; the scan's other axis is taken as equal until a scan with the ruler
turned 90 degrees confirms it. Material boundaries inside the section (plastic insert against aluminium) are not traced,
only material against air.

Usage: uv run --no-project --with pillow --with numpy --with scipy --with scikit-image --with ezdxf python -I
       tools/scan_kontur.py <scan.jpeg> <out-stem> [--ruler y0:y1] [--below y] [--level 105]
       ruler band: rows of the ruler's mm ticks (default: found from the brightest rows above the profile);
       below: first row under the ruler where the profile may start.
"""
import argparse
import json

import ezdxf
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from skimage.measure import approximate_polygon, find_contours

Image.MAX_IMAGE_PIXELS = None


def ruler_scale(g, band):
    """px/mm from the mm ticks in a band of rows: tick centroids, index by the median pitch, line fit."""
    prof = g[band[0]:band[1]].mean(axis=0)
    prof = np.convolve(prof, np.ones(5) / 5, mode="same")
    s = prof - np.convolve(prof, np.ones(81) / 81, mode="same")
    peaks = [x for x in range(50, len(s) - 50) if s[x] == s[x - 40:x + 41].max() and s[x] > 8]
    c = np.array([x - 12 + (np.clip(s[x - 12:x + 13], 0, None) * np.arange(25)).sum() / np.clip(s[x - 12:x + 13], 0, None).sum()
                  for x in peaks])
    idx = np.round((c - c[0]) / np.median(np.diff(c))).astype(int)
    for _ in range(3):                                       # drop ticks that are not on the mm grid (labels, dust)
        p, a = np.polyfit(idx, c, 1)
        r = c - (a + p * idx)
        keep = np.abs(r) < 3 * max(np.std(r), 0.5)
        idx, c = idx[keep], c[keep]
    p, a = np.polyfit(idx, c, 1)
    r = c - (a + p * idx)
    thirds = [np.polyfit(idx[m], c[m], 1)[0] for m in (idx < idx[-1] / 3, (idx >= idx[-1] / 3) & (idx < 2 * idx[-1] / 3),
                                                        idx >= 2 * idx[-1] / 3)]
    return {"px_per_mm": float(p), "dpi": float(p * 25.4), "ticks": int(len(c)), "span_mm": int(idx[-1] - idx[0]),
            "residual_rms_um": float(np.std(r) / p * 1000), "residual_max_um": float(np.abs(r).max() / p * 1000),
            "px_per_mm_thirds": [round(float(t), 3) for t in thirds]}


def area(poly):
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scan")
    ap.add_argument("out")
    ap.add_argument("--ruler", default="1820:1960")
    ap.add_argument("--below", type=int, default=2040)
    ap.add_argument("--level", type=float, default=105.0)
    ap.add_argument("--min-mm", type=float, default=2.0, help="drop contours shorter than this (dust)")
    args = ap.parse_args()
    g = np.asarray(Image.open(args.scan).convert("L"), dtype=np.float32)
    band = tuple(int(v) for v in args.ruler.split(":"))
    scale = ruler_scale(g, band)
    k = scale["px_per_mm"]
    sub = gaussian_filter(g[args.below:], 1.0)
    H, W = sub.shape
    contours = []
    for c in find_contours(sub, args.level):
        closed = bool(np.allclose(c[0], c[-1]))
        mm = np.c_[c[:, 1] / k, -(c[:, 0] + args.below) / k]              # x right, y up, origin at the scan's top left
        length = float(np.hypot(*np.diff(mm, axis=0).T).sum())
        if length < args.min_mm:
            continue
        on_edge = bool((c[:, 0] < 1).any() or (c[:, 0] > H - 2).any() or (c[:, 1] < 1).any() or (c[:, 1] > W - 2).any())
        contours.append({"mm": mm, "px": c, "closed": closed and not on_edge, "length": length,
                         "area": abs(area(mm)) if closed else 0.0})
    contours.sort(key=lambda c: -c["area"])
    x0 = min(c["mm"][:, 0].min() for c in contours)
    y0 = min(c["mm"][:, 1].min() for c in contours)
    doc = ezdxf.new("R2010", setup=False)
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    table = []
    outer = max(range(len(contours)), key=lambda i: contours[i]["length"])   # the section's outline is its longest contour
    for i, c in enumerate(contours):
        pts = approximate_polygon(c["mm"] - [x0, y0], tolerance=0.005)   # Douglas-Peucker, 5 um
        # outline-open: the outline runs off the scan; open: other contours cut by the scan edge (dust, a part of a part)
        layer = ("outline" if c["closed"] else "outline-open") if i == outer else ("hole" if c["closed"] else "open")
        msp.add_lwpolyline([tuple(p) for p in (pts[:-1] if c["closed"] else pts)], close=c["closed"],
                           dxfattribs={"layer": layer})
        lo, hi = c["mm"].min(0) - [x0, y0], c["mm"].max(0) - [x0, y0]
        table.append({"i": i, "layer": layer, "closed": c["closed"], "area_mm2": round(c["area"], 2), "length_mm": round(c["length"], 2),
                      "bbox_mm": [round(float(v), 3) for v in (*lo, *hi)], "points": len(pts)})
    doc.saveas(f"{args.out}.dxf")
    # overlay at a quarter of the scan
    q = 4
    img = Image.open(args.scan).convert("RGB").resize((g.shape[1] // q, g.shape[0] // q))
    d = ImageDraw.Draw(img)
    for c in contours:
        p = c["px"][:, ::-1] / q + [0, args.below / q]
        d.line([tuple(v) for v in p], fill=(255, 40, 40) if c["closed"] else (255, 200, 0), width=2)
    d.line([(0, band[0] / q), (img.width, band[0] / q)], fill=(0, 160, 255))
    d.line([(0, band[1] / q), (img.width, band[1] / q)], fill=(0, 160, 255))
    img.save(f"{args.out}-overlay.png")
    report = {"scan": args.scan, "size_px": list(g.shape[::-1]), "ruler": scale, "level": args.level,
              "origin_mm": [round(x0, 3), round(y0, 3)], "contours": table}
    with open(f"{args.out}.json", "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(scale))
    for t in table[:12]:
        print(t)
    print(f"{len(table)} contours -> {args.out}.dxf, {args.out}-overlay.png, {args.out}.json")


if __name__ == "__main__":
    main()
