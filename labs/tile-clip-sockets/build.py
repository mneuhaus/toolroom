"""Build scaled OpenLOCK and Dragonbite pocket coupons and clips, export them and
run the geometric verification.

    uv run python labs/tile-clip-sockets/build.py --scale 1.0 [--variant through|blind]
        [--supports] [--chamfer] [--enforce] [--v43-bar]
    uv run python labs/tile-clip-sockets/build.py --all        # 0.5 0.75 1.0 1.5 2.0

Scaling rule: every profile dimension is multiplied by S; the process floors in
spec.Process are not. After scaling, the clip (clearance owner) is shrunk where
a clearance falls below its floor, the OpenLOCK barb / Dragonbite bite is grown
where the interference falls below one line width, and roof, floor and rim of
the base are compared with their floors. Only --enforce changes the base height.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys, time
from pathlib import Path

from build123d import (Box, Cylinder, Plane, Polygon, Pos, Rot, Compound, Part,
                       export_step, export_stl, extrude, section)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spec  # noqa: E402
import verify  # noqa: E402

SCALES = [0.5, 0.75, 1.0, 1.5, 2.0]
TILE = 25.4   # coupon edge at scale 1 (two pitches); the coupon scales with the profile, otherwise a 2x pocket does not fit
BUF = 1.0     # cut buffer outside the contact face (not scaled; pure boolean aid)
EPS = 0.01    # overlap between fused negatives (avoids coincident faces)


# ---------------------------------------------------------------- helpers
def prism(points, z0, z1):
    """Closed XY polygon extruded from z0 to z1."""
    return Pos(0, 0, z0) * extrude(Polygon(*points, align=None), amount=z1 - z0)


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from two opposite corners; accepts either corner order per axis."""
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def symmetric_outline(quadrant):
    """Quadrant (x >= 0, y >= 0) polyline from (bw, 0) to (0, tip) -> closed
    outline with mirror symmetry in x and y."""
    right = [(x, -y) for x, y in reversed(quadrant)] + quadrant[1:]
    left = [(-x, y) for x, y in reversed(right)][1:-1]
    return right + left


def slot_polygon(half, tip_y, extra=0.5):
    """Right half polyline (x >= 0, y ascending) of a slot -> closed polygon open past tip_y."""
    xt = half[-1][0]
    pts = list(half) + [(xt, tip_y + extra), (-xt, tip_y + extra)] + [(-x, y) for x, y in reversed(half)]
    return pts


def lead_in_wedge(w, c, z0, z1):
    """45 degree lead-in on the mouth corners at the contact face, as extra negative."""
    return prism([(-BUF, -w / 2 - c), (0, -w / 2 - c), (c, -w / 2), (c, w / 2), (0, w / 2 + c), (-BUF, w / 2 + c)], z0, z1)


def place(shape, edge, size=TILE, height=0.0):
    """Move a pocket-frame shape (x = depth, y = along the edge) onto an edge of a
    size x size tile centred on that edge. Edges: 'x0', 'x1', 'y0', 'y1'."""
    h = size / 2
    if edge == "x0":
        return Pos(0, h, height) * shape
    if edge == "x1":
        return Pos(size, h, height) * Rot(0, 0, 180) * shape
    if edge == "y0":
        return Pos(h, 0, height) * Rot(0, 0, 90) * shape
    return Pos(h, size, height) * Rot(0, 0, -90) * shape


def as_part(shape):
    """Booleans that leave several solids return a ShapeList; keep them as one Compound."""
    if isinstance(shape, (list, tuple)):
        return Compound(list(shape))
    return shape


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- scaling and floors
def adjust(adjustments, flags, quantity, scaled_value, floor, ok, applied=None, action="flag"):
    """Record one floor comparison. ok: scaled value satisfies the floor."""
    rec = {"quantity": quantity, "scaled_value": round(scaled_value, 4), "floor": round(floor, 4),
           "applied_value": round(scaled_value if applied is None else applied, 4),
           "action": "none" if ok else action}
    if not ok:
        adjustments.append(rec)
        if action != "flag":          # pure reports are flagged by verify.py from the measured geometry
            flags.append(f"{quantity}:{action}")
    return rec


def derive_openlock(S, P: spec.Process, opts) -> dict:
    d = spec.scaled(spec.OpenLock(), S)
    d["tile"] = TILE * S
    if opts.get("v43_bar"):
        d["clip_bar_w"] = d["clip_bar_w_v43"]
    adj, flags = [], []
    d["pocket_h"] = d["pocket_z1"] - d["pocket_z0"]
    # clip is the clearance owner
    clr_z = d["pocket_h"] - d["clip_t"]
    if clr_z < P.clearance_z:
        d["clip_t"] = d["pocket_h"] - P.clearance_z
    adjust(adj, flags, "clearance_z (pocket height - clip thickness)", clr_z, P.clearance_z, clr_z >= P.clearance_z,
           d["pocket_h"] - d["clip_t"], "shrink clip thickness")
    clr_xy = d["mouth_w"] - d["clip_bar_w"]
    if clr_xy < P.clearance_xy:
        d["clip_bar_w"] = d["mouth_w"] - P.clearance_xy
    adjust(adj, flags, "clearance_xy (mouth - bar width)", clr_xy, P.clearance_xy, clr_xy >= P.clearance_xy,
           d["mouth_w"] - d["clip_bar_w"], "shrink clip bar width")
    interf = d["barb_w"] - d["neck_w"]
    if interf < P.interference_min:
        d["barb_w"] = d["neck_w"] + P.interference_min
    adjust(adj, flags, "barb interference (barb - neck)", interf, P.interference_min, interf >= P.interference_min,
           d["barb_w"] - d["neck_w"], "grow barb")
    adjust(adj, flags, "clip thickness", d["clip_t"], P.clip_thickness_min, d["clip_t"] >= P.clip_thickness_min)
    if opts.get("supports") and d["support_w"] < P.support_bar:
        adjust(adj, flags, "support bar width", d["support_w"], P.support_bar, False, P.support_bar, "widen support bar")
        d["support_w"] = P.support_bar
    # base band
    roof = d["base_height"] - d["pocket_z1"]
    d["base_required"] = max(d["base_height"], d["pocket_z1"] + P.roof_min)
    if roof < P.roof_min and opts.get("enforce"):
        d["base_height"] = d["base_required"]
        adjust(adj, flags, "roof", roof, P.roof_min, False, d["base_height"] - d["pocket_z1"], "raise base height")
    else:
        adjust(adj, flags, "roof", roof, P.roof_min, roof >= P.roof_min)
    adjust(adj, flags, "floor", d["pocket_z0"], P.floor_min, d["pocket_z0"] >= P.floor_min)
    rim = (d["rim_w"] - d["mouth_w"]) / 2
    adjust(adj, flags, "rim side (per side beside the mouth)", rim, P.rim_min, rim >= P.rim_min)
    adjust(adj, flags, "rim depth (guaranteed band behind the face)", d["rim_d"], P.rim_min, d["rim_d"] >= P.rim_min)
    d["prong_neck_clearance"] = d["neck_w"] - d["prong_w"]   # line to line by design (OL7.1)
    d["barb_chamber_clearance"] = d["chamber_w"] - d["barb_w"]
    d["axial_clearance"] = d["chamber_x1"] - d["half_len"] if "half_len" in d else d["chamber_x1"] - d["clip_len"] / 2
    d["adjustments"], d["flags"] = adj, flags
    return d


def derive_dragonbite(S, P: spec.Process, opts) -> dict:
    d = spec.scaled(spec.Dragonbite(), S)
    d["tile"] = TILE * S
    adj, flags = [], []
    d["throat_h"] = d["throat_z1"] - d["throat_z0"]
    clr_z = d["throat_h"] - d["clip_t"]
    if clr_z < P.clearance_z:
        d["clip_t"] = d["throat_h"] - P.clearance_z
    adjust(adj, flags, "clearance_z (throat height - clip thickness)", clr_z, P.clearance_z, clr_z >= P.clearance_z,
           d["throat_h"] - d["clip_t"], "shrink clip thickness")
    clr_xy = d["throat_w"] - d["clip_bar_w"]
    if clr_xy < P.clearance_xy:
        d["clip_bar_w"] = d["throat_w"] - P.clearance_xy
    adjust(adj, flags, "clearance_xy (throat - bar width)", clr_xy, P.clearance_xy, clr_xy >= P.clearance_xy,
           d["throat_w"] - d["clip_bar_w"], "shrink clip bar width")
    interf = d["head_d"] - d["gap_bite"]
    if interf < P.interference_min:
        d["gap_bite"] = d["head_d"] - P.interference_min
    adjust(adj, flags, "bite interference (head - bite gap)", interf, P.interference_min, interf >= P.interference_min,
           d["head_d"] - d["gap_bite"], "close bite")
    adjust(adj, flags, "clip thickness", d["clip_t"], P.clip_thickness_min, d["clip_t"] >= P.clip_thickness_min)
    cup = d["gap_cup"] - d["head_d"]
    adjust(adj, flags, "cup clearance (cup gap - head)", cup, P.clearance_xy, cup >= P.clearance_xy)
    axial = d["cavity_x1"] - d["half_len"]
    adjust(adj, flags, "axial clearance (back wall - clip tip)", axial, P.clearance_xy, axial >= P.clearance_xy)
    if opts.get("supports") and d["rib_w"] < P.support_bar:
        adjust(adj, flags, "bridging rib width", d["rib_w"], P.support_bar, False, P.support_bar, "widen rib")
        d["rib_w"] = P.support_bar
    roof = d["base_height"] - d["throat_z1"]
    d["base_required"] = max(d["base_height"], d["throat_z1"] + P.roof_min)
    if roof < P.roof_min and opts.get("enforce"):
        d["base_height"] = d["base_required"]
        adjust(adj, flags, "roof", roof, P.roof_min, False, d["base_height"] - d["throat_z1"], "raise base height")
    else:
        adjust(adj, flags, "roof", roof, P.roof_min, roof >= P.roof_min)
    adjust(adj, flags, "floor (blind variant / pad)", d["floor_t"], P.floor_min, d["floor_t"] >= P.floor_min)
    rim = (d["rim_w"] - d["throat_w"]) / 2
    adjust(adj, flags, "rim side (per side beside the throat)", rim, P.rim_min, rim >= P.rim_min)
    adjust(adj, flags, "rim depth (guaranteed band behind the face)", d["rim_d"], P.rim_min, d["rim_d"] >= P.rim_min)
    d["cup_head_clearance"], d["axial_clearance"] = cup, axial
    d["clip_len"] = 2 * d["half_len"]
    d["adjustments"], d["flags"] = adj, flags
    return d


# ---------------------------------------------------------------- OpenLOCK geometry
def ol_floor_negative(d, variant, chamfer):
    z0, z1 = d["pocket_z0"], d["pocket_z1"]
    mw, md, tw, tx, nw, nx = d["mouth_w"], d["mouth_d"], d["taper_w0"], d["taper_x1"], d["neck_w"], d["neck_x1"]
    plan = [(-BUF, -mw / 2), (md, -mw / 2), (md, -tw / 2), (tx, -nw / 2), (nx + EPS, -nw / 2),
            (nx + EPS, nw / 2), (tx, nw / 2), (md, tw / 2), (md, mw / 2), (-BUF, mw / 2)]
    neg = prism(plan, z0, z1)
    if variant == "through":
        cz0, cz1 = -BUF, d["base_height"] + BUF
    else:
        cz0, cz1 = z0, z1
    neg = neg + box(nx, d["chamber_x1"], -d["chamber_w"] / 2, d["chamber_w"] / 2, cz0, cz1)
    if chamfer:
        neg = neg + lead_in_wedge(mw, chamfer, z0, z1)
    return neg


def ol_rim(d):
    return box(0, d["rim_d"], -d["rim_w"] / 2, d["rim_w"] / 2, d["rim_z0"], d["rim_z0"] + d["rim_h"])


def ol_supports(d, x1=None):
    x1 = d["support_x1"] if x1 is None else x1
    bars = [box(0, x1, sgn * d["support_y0"], sgn * d["support_y1"], d["support_z0"], d["support_z1"]) for sgn in (1, -1)]
    return bars[0] + bars[1]


def ol_wall_negative(d, chamfer):
    z0, z1, T = d["pocket_z0"], d["pocket_z1"], d["wall_t"]
    mw, md, tw, tx, nw = d["mouth_w"], d["wall_mouth_d"], d["taper_w0"], d["wall_taper_x1"], d["neck_w"]
    lower = [(-BUF, -mw / 2), (md, -mw / 2), (md, -tw / 2), (tx, -nw / 2), (T - tx, -nw / 2),
             (T - md, -tw / 2), (T - md, -mw / 2), (T + BUF, -mw / 2)]
    plan = lower + [(x, -y) for x, y in reversed(lower)]
    neg = prism(plan, z0, z1)
    if chamfer:
        neg = neg + lead_in_wedge(mw, chamfer, z0, z1) + (Pos(T, 0, 0) * Rot(0, 0, 180) * lead_in_wedge(mw, chamfer, z0, z1))
    return neg


def ol_sidelock_negative(d, chamfer):
    """Profile in x-z (x = depth from the end face), pocket thickness along y, centred at z = 0."""
    mh, md, tx, nh, nx, ch, cx, t = (d["side_mouth_h"], d["side_mouth_d"], d["side_taper_x1"], d["side_neck_h"],
                                     d["side_neck_x1"], d["side_chamber_h"], d["side_chamber_x1"], d["side_t"])
    tw = d["taper_w0"]  # same profile as the lying pocket: 12 -> 10 taper
    lower = [(-BUF, -mh / 2), (md, -mh / 2), (md, -tw / 2), (tx, -nh / 2), (nx, -nh / 2), (nx, -ch / 2), (cx, -ch / 2)]
    profile = lower + [(x, -y) for x, y in reversed(lower)]
    neg = prism(profile, -t / 2, t / 2)           # profile in XY, thickness in Z
    if chamfer:
        neg = neg + lead_in_wedge(mh, chamfer, -t / 2, t / 2)
    return Rot(90, 0, 0) * neg                    # XY profile -> XZ profile, thickness along Y


def ol_clip(d):
    outline = symmetric_outline(spec_outline_openlock(d))
    body = prism(outline, -d["clip_t"] / 2, d["clip_t"] / 2)
    eye = spec_eye_openlock(d)
    slot = prism(slot_polygon(eye, d["tip_y"]), -d["clip_t"], d["clip_t"])
    return body - slot - slot.mirror(Plane.XZ)


def spec_outline_openlock(d):
    bw = d["clip_bar_w"] / 2
    pts = [(bw, 0.0), (bw, d["bar_len"] / 2), (d["prong_w"] / 2, d["bar_len"] / 2), (d["prong_w"] / 2, d["prong_y1"]),
           (d["barb_w"] / 2, d["barb_y0"]), (d["barb_w"] / 2, d["barb_y1"])]
    pts += [(w / 2, y) for w, y in d["taper_stations"]]
    pts += [(d["tip_w"] / 2, d["tip_y"]), (0.0, d["tip_y"])]
    return pts


def spec_eye_openlock(d):
    return [(d["eye_open"] / 2, d["eye_open_y"]), (d["eye_max"] / 2, d["eye_max_y"]),
            (d["eye_y9"] / 2, 9.0 * d["tip_y"] / 9.75), (d["eye_tip"] / 2, d["tip_y"])]


def build_openlock(d, variant, supports, chamfer):
    base, T_ = d["base_height"], d["tile"]
    tile = box(0, T_, 0, T_, 0, base)
    neg = ol_floor_negative(d, variant, chamfer)
    rim = ol_rim(d)
    edges = ["x0", "x1", "y0", "y1"]
    for e in edges:
        tile = tile + place(rim, e, T_)
    negs = {e: place(neg, e, T_) for e in edges}
    for e in edges:
        tile = as_part(tile - negs[e])
    if supports:
        for e in edges:
            tile = as_part(tile + place(ol_supports(d), e, T_))
    single = as_part((box(0, T_, 0, T_, 0, base) + place(rim, "x0", T_)) - negs["x0"])
    # wall coupon: x = thickness, y = length, z = height
    T, L, H = d["wall_t"], T_, T_
    wall = box(0, T, 0, L, 0, H)
    wall = wall + box(0, T, L / 2 - d["rim_w"] / 2, L / 2 + d["rim_w"] / 2, d["rim_z0"], d["rim_z0"] + d["rim_h"])
    srim = box(0, d["side_rim_d"], -d["side_rim_t"] / 2, d["side_rim_t"] / 2, -d["side_rim_h"] / 2, d["side_rim_h"] / 2)
    wall = wall + (Pos(T / 2, 0, H / 2) * Rot(0, 0, 90) * srim) + (Pos(T / 2, L, H / 2) * Rot(0, 0, -90) * srim)
    wneg = Pos(0, L / 2, 0) * ol_wall_negative(d, chamfer)
    sneg = ol_sidelock_negative(d, chamfer)
    sneg0 = Pos(T / 2, 0, H / 2) * Rot(0, 0, 90) * sneg
    sneg1 = Pos(T / 2, L, H / 2) * Rot(0, 0, -90) * sneg
    wall = as_part(wall - wneg - sneg0 - sneg1)
    if supports:
        bars = ol_supports(d)
        wall = as_part(wall + (Pos(0, L / 2, 0) * bars) + (Pos(T, L / 2, 0) * Rot(0, 0, 180) * bars))
    clip = ol_clip(d)
    return {"floor_coupon": tile, "floor_negative": negs["x0"], "wall_coupon": wall, "wall_negative": wneg,
            "sidelock_negative": sneg0, "clip": clip, "rim": place(rim, "x0", T_), "measure_coupon": single,
            "supports": place(ol_supports(d), "x0", T_) if supports else None}


# ---------------------------------------------------------------- Dragonbite geometry
def db_negative(d, variant, chamfer):
    z0, z1 = d["throat_z0"], d["throat_z1"]
    throat = box(-BUF, d["lip_d"] + EPS, -d["throat_w"] / 2, d["throat_w"] / 2, z0, z1)
    cz0 = z0 if variant == "blind" else -BUF
    cavity = box(d["lip_d"], d["cavity_x1"], -d["cavity_w"] / 2, d["cavity_w"] / 2, cz0, z1)
    neg = throat + cavity
    head = Pos(d["head_cx"], 0, (cz0 + z1) / 2) * Cylinder(d["head_d"] / 2, z1 - cz0 + 2 * EPS)
    neck = box(d["head_cx"], d["cavity_x1"] + EPS, -d["post_neck_w"] / 2, d["post_neck_w"] / 2, cz0 - EPS, z1 + EPS)
    neg = neg - head - neck
    if variant != "blind":
        pad = box(d["lip_d"] - EPS, d["cavity_x1"] + EPS, -d["pad_w"] / 2, d["pad_w"] / 2, cz0 - EPS, z0)
        disc = Pos(d["head_cx"], 0, (cz0 - EPS + z0) / 2) * Cylinder(d["pad_disc_d"] / 2, z0 - cz0 + EPS)
        neg = neg - pad - disc
    if chamfer:
        neg = neg + lead_in_wedge(d["throat_w"], chamfer, z0, z1)
    return neg


def db_rim(d):
    return box(0, d["rim_d"], -d["rim_w"] / 2, d["rim_w"] / 2, d["rim_z0"], d["rim_z0"] + d["rim_h"])


def db_ribs(d):
    ribs = None
    for y in d["rib_y"]:
        b = box(0, d["lip_d"], y - d["rib_w"] / 2, y + d["rib_w"] / 2, d["throat_z0"] - EPS, d["throat_z1"] + EPS)
        ribs = b if ribs is None else ribs + b
    return ribs


def spec_outline_dragonbite(d):
    bw = d["clip_bar_w"] / 2
    S = d["half_len"] / 10.73
    return [(bw, 0.0), (bw, d["bar_len"] / 2), (d["jaw_neck_w"] / 2, d["jaw_neck_y0"]), (d["jaw_neck_w"] / 2, d["jaw_neck_y1"]),
            (6.2 * S, d["gap_cup_y"]), (d["jaw_max_w"] / 2, d["jaw_max_y0"]), (d["jaw_max_w"] / 2, d["jaw_max_y1"]),
            (6.0 * S, d["gap_bite_y"]), (d["jaw_tip_w"] / 2, d["half_len"]), (0.0, d["half_len"])]


def spec_gap_dragonbite(d):
    S = d["half_len"] / 10.73
    r, cy = d["gap_cup"] / 2, d["gap_cup_y"]
    pts = [(0.55 * S, d["bar_len"] / 2), (d["gap_root"] / 2, d["jaw_neck_y1"]), (1.2 * S, 4.5 * S)]
    for y in (6.0, 6.5, 7.0, 7.5, 7.95, 8.5, 9.0, 9.4):
        y *= S
        pts.append((math.sqrt(max(r * r - (y - cy) ** 2, 0.0)), y))
    pts += [(d["gap_bite"] / 2, d["gap_bite_y"]), (d["gap_tip"] / 2, d["half_len"])]
    return pts


def db_clip(d):
    body = prism(symmetric_outline(spec_outline_dragonbite(d)), -d["clip_t"] / 2, d["clip_t"] / 2)
    slot = prism(slot_polygon(spec_gap_dragonbite(d), d["half_len"]), -d["clip_t"], d["clip_t"])
    return body - slot - slot.mirror(Plane.XZ)


def build_dragonbite(d, variant, supports, chamfer):
    T_ = d["tile"]
    tile = box(0, T_, 0, T_, 0, d["base_height"])
    neg, rim = db_negative(d, variant, chamfer), db_rim(d)
    edges = ["x0", "x1", "y0", "y1"]
    for e in edges:
        tile = tile + place(rim, e, T_)
    negs = {e: place(neg, e, T_) for e in edges}
    for e in edges:
        tile = as_part(tile - negs[e])
    if supports:
        for e in edges:
            tile = as_part(tile + place(db_ribs(d), e, T_))
    single = as_part((box(0, T_, 0, T_, 0, d["base_height"]) + place(rim, "x0", T_)) - negs["x0"])
    return {"floor_coupon": tile, "floor_negative": negs["x0"], "clip": db_clip(d), "rim": place(rim, "x0", T_), "measure_coupon": single,
            "supports": place(db_ribs(d), "x0", T_) if supports else None}


# ---------------------------------------------------------------- export, SVG, summary
def export_case(shapes, out: Path, prefix: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, shape in shapes.items():
        if shape is None or key in ("rim", "supports", "measure_coupon"):
            continue
        name = f"{prefix}-{key.replace('_', '-')}"
        p = out / f"{name}.step"
        export_step(shape, p)
        files[p.name] = sha(p)
        if not key.endswith("negative"):
            q = out / f"{name}.stl"
            export_stl(shape, q, tolerance=0.05, angular_tolerance=0.5)
            files[q.name] = sha(q)
    return files


def run_case(system, S, P, opts):
    t0 = time.time()
    variant = opts["variant"]
    if system == "openlock":
        d = derive_openlock(S, P, opts)
        shapes = build_openlock(d, variant, opts["supports"], opts["chamfer"])
    else:
        d = derive_dragonbite(S, P, opts)
        shapes = build_dragonbite(d, variant, opts["supports"], opts["chamfer"])
    out = HERE / "exports" / f"s{S:g}"
    files = export_case(shapes, out, f"{system}-{variant}")
    d["variant"] = variant
    result = verify.verify_case(system, S, d, shapes, P)
    result.update({"system": system, "scale": S, "variant": variant, "options": {k: opts[k] for k in ("supports", "chamfer", "enforce", "v43_bar")},
                   "dimensions": {k: v for k, v in d.items() if k not in ("adjustments", "flags", "sources", "variant")},
                   "adjustments": d["adjustments"], "flags": sorted(set(d["flags"] + result.pop("flags", []))),
                   "exports": {f"labs/tile-clip-sockets/exports/s{S:g}/{k}": v for k, v in files.items()},
                   "build_seconds": round(time.time() - t0, 1)})
    print(f"{system:10s} S={S:<4g} {'PASS' if result['insertion']['passed'] else 'FAIL'} "
          f"protrusion={result['insertion']['protrusion_outside_barb_mm3']:.4g} barb={result['insertion']['barb_seated_interference_mm3']:.4g} "
          f"transit={result['insertion']['transit_interference_mm3']:.4g} "
          f"flags={result['flags']}", flush=True)
    return result, shapes, d


def fmt(v, nd=2):
    return "open" if v is None else f"{v:.{nd}f}"


def write_table(cases, path: Path, opts):
    L = ["# Scaling table", "",
         f"Generated by `build.py --all` (variant `{opts['variant']}`, supports {opts['supports']}, chamfer {opts['chamfer']}, "
         f"enforce {opts['enforce']}). Clearances are totals (pocket minus clip); adjustments show the value actually built. "
         "Volumes in mm³. Full numbers in `summary.json`.", ""]
    for system, title in (("openlock", "OpenLOCK"), ("dragonbite", "Dragonbite")):
        rows = [c for c in cases if c["system"] == system]
        L += [f"## {title}", "",
              "| Scale | Base | Band z | Roof | Floor | Rim side/depth | Mouth/throat | " + ("Neck" if system == "openlock" else "Post head") + " | Chamber/cavity | Clip t | Bar w | Clr z | Clr xy | " +
              ("Barb − neck" if system == "openlock" else "Head − bite") + " | Protrusion | Barb ∩ seated | Transit ∩ | Flags |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in rows:
            d, m, i = c["dimensions"], c["measurements"], c["insertion"]
            pocket = m["pocket"]
            band = (f"{d['pocket_z0']:.2f}–{d['pocket_z1']:.2f}" if system == "openlock" else f"{d['throat_z0']:.2f}–{d['throat_z1']:.2f}")
            interf = (d["barb_w"] - d["neck_w"]) if system == "openlock" else (d["head_d"] - d["gap_bite"])
            clr_z = (d["pocket_h"] if system == "openlock" else d["throat_h"]) - d["clip_t"]
            clr_xy = (d["mouth_w"] if system == "openlock" else d["throat_w"]) - d["clip_bar_w"]
            base = f"{d['base_height']:.2f}" + (f" (needs {d['base_required']:.2f})" if d["base_required"] > d["base_height"] + 1e-9 else "")
            L.append(f"| {c['scale']:g} | {base} | {band} | {fmt(pocket['roof'])} | {fmt(pocket['floor'])} | {fmt(pocket['rim_side'])}/{d['rim_d']:.2f} | "
                     f"{fmt(pocket['mouth_w'])} | {fmt(pocket['neck_w'])} | {fmt(pocket['chamber_w'])} | {m['clip']['thickness']:.2f} | "
                     f"{m['clip']['bar_w']:.2f} | {clr_z:.2f} | {clr_xy:.2f} | {interf:.2f} | {i['protrusion_outside_barb_mm3']:.3g} | "
                     f"{i['barb_seated_interference_mm3']:.3g} | {i['transit_interference_mm3']:.3g} | {', '.join(c['flags']) or '–'} |")
        L.append("")
    walls = [c for c in cases if c["system"] == "openlock"]
    L += ["## OpenLOCK wall coupon (through-pocket and vertical side-lock)", "",
          "| Scale | Wall mouth depth | Through-pocket protrusion | Through-pocket ∩ wall | Side-lock protrusion | Side-lock barb ∩ | Side-lock depth |",
          "|---|---|---|---|---|---|---|"]
    for c in walls:
        w = c["wall"]
        L.append(f"| {c['scale']:g} | {c['dimensions']['wall_mouth_d']:.2f} | {w['through_protrusion_mm3']:.3g} | {w['through_interference_mm3']:.3g} | "
                 f"{w['sidelock_protrusion_outside_barb_mm3']:.3g} | {w['sidelock_barb_interference_mm3']:.3g} | {w['sidelock_depth']:.2f} |")
    L += ["", "Flags: `quantity:action`; `flag` means reported only, other actions were applied to the clip (never to the pocket). "
          "The wall through-pocket clash is a property of the reference geometry (1.0 mm mouth inside a 12.7 mm wall, "
          "findings §7.2), not of scaling.", ""]
    path.write_text("\n".join(L))


# ---------------------------------------------------------------- SVG
def face_polys(sketch, axes):
    """Faces of a section -> list of (outer, [inners]) polylines in 2D using the given axis indices."""
    polys = []
    for f in sketch.faces():
        def wire_pts(w):
            pts = []
            for e in w.edges():
                n = 2 if e.geom_type.name == "LINE" else 16
                for p in e.positions([i / n for i in range(n)]):
                    t = tuple(p); pts.append((t[axes[0]], t[axes[1]]))
            return pts
        polys.append((wire_pts(f.outer_wire()), [wire_pts(w) for w in f.inner_wires()]))
    return polys


def svg_path(polys, tf):
    parts = []
    for outer, inners in polys:
        for ring in [outer] + inners:
            pts = [tf(x, y) for x, y in ring]
            parts.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z")
    return " ".join(parts)


def write_svg(sections, path: Path):
    """sections: dict system -> {plan_tiles, plan_clip, vert_tiles, vert_clip, labels}. Scale-1 geometry."""
    K = 7.0  # px per mm
    W, H = 640, 560
    rows = [("openlock", "OpenLOCK (through variant)", 40), ("dragonbite", "Dragonbite (open-bottom variant)", 300)]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif" font-size="11">',
           '<title>Tile clip joints: plan and vertical sections at scale 1</title>',
           '<style>.t{fill:#5a5a5a}.tile{fill:#8a8a8a;fill-opacity:0.22;stroke:#222;stroke-width:1;fill-rule:evenodd}'
           '.clip{fill:#3b6ea5;fill-opacity:0.55;stroke:#17324f;stroke-width:1;fill-rule:evenodd}'
           '.joint{stroke:#222;stroke-width:0.8;stroke-dasharray:4 3}.lbl{fill:#222}.lead{stroke:#222;stroke-width:0.7;fill:none}'
           '.ttl{fill:#222;font-weight:bold;font-size:13px}.cap{fill:#444;font-size:10px}</style>']
    for system, title, y0 in rows:
        s = sections[system]
        # plan: x (depth) to the right, y (along the edge) up; origin at the joint plane / pocket centre
        ox, oy = 130, y0 + 125
        tf = lambda x, y, ox=ox, oy=oy: (ox + K * x, oy - K * y)
        out.append(f'<text class="ttl" x="20" y="{y0 + 4}">{title}</text>')
        out.append(f'<text class="cap" x="20" y="{y0 + 18}">Plan section at mid pocket height, two tiles joined, clip seated</text>')
        out.append(f'<path class="tile" d="{svg_path(s["plan_tiles"], tf)}"/>')
        out.append(f'<path class="clip" d="{svg_path(s["plan_clip"], tf)}"/>')
        jx = tf(0, 0)[0]
        out.append(f'<line class="joint" x1="{jx:.1f}" y1="{oy - K * 12:.1f}" x2="{jx:.1f}" y2="{oy + K * 12:.1f}"/>')
        for text, (lx, ly), (px, py) in s["labels_plan"]:
            tx, ty = tf(lx, ly); qx, qy = tf(px, py)
            out.append(f'<line class="lead" x1="{tx:.1f}" y1="{ty:.1f}" x2="{qx:.1f}" y2="{qy:.1f}"/>')
            anchor = "end" if lx < px else "start"
            out.append(f'<text class="lbl" x="{tx:.1f}" y="{ty + 4:.1f}" text-anchor="{anchor}">{text}</text>')
        # vertical section: x to the right, z up
        vx, vy = 400, y0 + 140
        tv = lambda x, z, vx=vx, vy=vy: (vx + K * x, vy - K * z)
        out.append(f'<text class="cap" x="{vx - K * 13:.0f}" y="{y0 + 18}">Vertical section {s["vert_caption"]}</text>')
        out.append(f'<path class="tile" d="{svg_path(s["vert_tiles"], tv)}"/>')
        out.append(f'<path class="clip" d="{svg_path(s["vert_clip"], tv)}"/>')
        jx = tv(0, 0)[0]
        out.append(f'<line class="joint" x1="{jx:.1f}" y1="{vy - K * 9:.1f}" x2="{jx:.1f}" y2="{vy + K * 2:.1f}"/>')
        for text, (lx, ly), (px, py) in s["labels_vert"]:
            tx, ty = tv(lx, ly); qx, qy = tv(px, py)
            out.append(f'<line class="lead" x1="{tx:.1f}" y1="{ty:.1f}" x2="{qx:.1f}" y2="{qy:.1f}"/>')
            anchor = "end" if lx < px else "start"
            out.append(f'<text class="lbl" x="{tx:.1f}" y="{ty + 4:.1f}" text-anchor="{anchor}">{text}</text>')
    out.append(f'<text class="cap" x="20" y="{H - 12}">Dimensions at scale 1 in mm; blue = clip, grey = tile material, dashed = joint plane. '
               'Generated by labs/tile-clip-sockets/build.py from the built solids.</text>')
    out.append("</svg>")
    path.write_text("\n".join(out))


def make_sections(system, shapes, d):
    """Section polygons of the scale-1 build for the SVG (joint frame: x = depth into tile 1)."""
    tile, clip = shapes["measure_coupon"], shapes["clip"]   # one pocket: the neighbouring pockets would cut into the window
    zmid = (d["pocket_z0"] + d["pocket_z1"]) / 2 if system == "openlock" else (d["throat_z0"] + d["throat_z1"]) / 2
    base = d["base_height"]
    pair = tile + tile.mirror(Plane.YZ)
    seated = verify.seated_pose(clip, zmid, d["tile"])
    win = box(-13, 13, d["tile"] / 2 - 11, d["tile"] / 2 + 11, -1, base + 1)
    plan_tiles = section(pair & win, section_by=Plane.XY, height=zmid)
    plan_clip = section(seated, section_by=Plane.XY, height=zmid)
    ycut = d["tile"] / 2 + 3.5
    vplane = Plane(origin=(0, ycut, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    vert_tiles = section(pair & win, section_by=vplane)
    vert_clip = section(seated, section_by=vplane)
    yc = d["tile"] / 2
    shift = lambda polys: [([(x, y - yc) for x, y in o], [[(x, y - yc) for x, y in i] for i in ins]) for o, ins in polys]
    s = {"plan_tiles": shift(face_polys(plan_tiles, (0, 1))), "plan_clip": shift(face_polys(plan_clip, (0, 1))),
         "vert_tiles": face_polys(vert_tiles, (0, 2)), "vert_clip": face_polys(vert_clip, (0, 2)),
         "vert_caption": "3.5 mm beside the pocket centre, through the " + ("prong" if system == "openlock" else "jaw")}
    if system == "openlock":
        s["labels_plan"] = [("mouth", (0.2, 13.6), (1.0, 7.0)), ("neck", (5.0, 12.2), (5.5, 5.0)), ("chamber", (9.8, 13.6), (8.4, 6.4)),
                            ("barb", (-6.8, -13.6), (-6.1, -5.2)), ("prong", (-1.5, -12.2), (-3.7, -5.0)), ("taper", (4.6, -13.6), (3.5, -5.8)),
                            ("bar", (-11.5, -8.5), (-1.0, -6.5)), ("eye slot", (-11.5, 3.5), (-4.5, 1.6))]
        s["labels_vert"] = [(f"floor {d['pocket_z0']:.1f}", (-11.5, -1.5), (-8, 0.7)),
                            (f"roof {d['base_height'] - d['pocket_z1']:.1f}", (4.0, 8.2), (3.5, 5.8)),
                            (f"clip {d['clip_t']:.2f} in {d['pocket_h']:.1f}", (11.5, 8.5), (2.0, 5.3)),
                            ("chamber " + ("through" if d["variant"] == "through" else "blind"), (11.5, -1.5), (8.5, 0.0))]
    else:
        s["labels_plan"] = [("throat", (0.2, 13.6), (1.5, 6.8)), ("lip", (3.0, 12.2), (3.15, 7.5)), ("cavity", (8.4, 13.6), (9.0, 8.0)),
                            ("jaws", (-7.0, -13.6), (-7.0, -6.2)), ("bar", (-1.5, -12.2), (-0.8, -6.5)), ("post", (5.4, -13.6), (8.1, -2.8)),
                            ("bite", (-11.5, 4.0), (-9.85, 2.3)), ("cup", (-11.5, 8.0), (-7.95, 2.95))]
        s["labels_vert"] = [(("pad" if d["variant"] == "through" else "floor") + f" {d['throat_z0']:.1f}", (-11.5, -1.5), (-8, 0.7)),
                            (f"ceiling {d['base_height'] - d['throat_z1']:.1f}", (4.0, 8.2), (3.5, 5.4)),
                            (f"clip {d['clip_t']:.2f} in {d['throat_h']:.2f}", (11.5, 8.5), (2.0, 4.4)),
                            ("open underside" if d["variant"] == "through" else "blind floor", (11.5, -1.5), (5.5, 0.0))]
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--all", action="store_true", help=f"run scales {SCALES} and write results/")
    ap.add_argument("--variant", choices=["through", "blind"], default="through",
                    help="OpenLOCK: chamber through the base or blind; Dragonbite: open underside (through) or blind 1.4 floor")
    ap.add_argument("--supports", action="store_true", help="model the built-in support bars / bridging ribs")
    ap.add_argument("--chamfer", action="store_true", help="add the proposed 0.4 mm lead-in at the mouth corners")
    ap.add_argument("--enforce", action="store_true", help="raise the base height so the roof meets its floor")
    ap.add_argument("--v43-bar", action="store_true", help="OpenLOCK clip bar 14.0 (v4.3) instead of 13.2 (v5.4)")
    ap.add_argument("--no-svg", action="store_true")
    a = ap.parse_args()
    opts = {"variant": a.variant, "supports": a.supports, "chamfer": a.chamfer, "enforce": a.enforce, "v43_bar": a.v43_bar}
    P = spec.Process()
    scales = SCALES if a.all else [a.scale]
    cases, sections = [], {}
    for S in scales:
        for system in ("openlock", "dragonbite"):
            result, shapes, d = run_case(system, S, P, opts)
            cases.append(result)
            if S == 1.0 and not a.no_svg:
                sections[system] = make_sections(system, shapes, d)
    if sections and len(sections) == 2:
        svg = HERE.parents[1] / "site" / "assets" / "tile-clips-sections.svg"
        write_svg(sections, svg)
        print("svg", svg, svg.stat().st_size, "bytes")
    res = HERE / "results"
    res.mkdir(exist_ok=True)
    summary = {"lab": "tile-clip-sockets", "build123d": __import__("build123d").__version__, "options": opts,
               "process": {**{k: v for k, v in spec.as_dict(P).items()}, "roof_min": P.roof_min, "floor_min": P.floor_min,
                           "rim_min": P.rim_min, "clip_thickness_min": P.clip_thickness_min},
               "volume_tolerance_mm3": verify.TOL, "script_sha256": {"build.py": sha(HERE / "build.py"), "spec.py": sha(HERE / "spec.py"),
                                                                     "verify.py": sha(HERE / "verify.py")},
               "physical_print": "not performed", "physical_fit": "not measured", "strength": "not tested", "cases": cases}
    if a.all:
        (res / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        write_table(cases, res / "scaling-table.md", opts)
    else:
        (res / f"summary-s{a.scale:g}.json").write_text(json.dumps(summary, indent=2) + "\n")
    failed = [c for c in cases if not c["insertion"]["passed"]]
    print("status:", "passed" if not failed else f"{len(failed)} case(s) failed the insertion check")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
