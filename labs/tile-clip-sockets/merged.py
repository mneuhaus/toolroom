"""Merged socket / hybrid clip lab extension.

A Toolroom design (this lab's own brief, not a reconstruction from OL/DL
findings): an OpenLOCK-envelope pocket topped with a thin plate carried on a
central post, and a clip that keeps the OpenLOCK outline but reshapes the eye
slot into DragonLock-style compliant jaws around that post. Scale 1 only.

    uv run python labs/tile-clip-sockets/merged.py

reuses spec.py (OpenLock envelope + the new spec.Merged dataclass), build.py
(prism/box/place/... helpers, the OpenLock pocket and clip builders) and
verify.py (vol/void_width/solid_extent/... probes). It writes:

    results/merged.json         -- every check in the brief, section C
    results/merged-table.md     -- the same, as a Markdown table
    print/*.stl, print/manifest.json, print/README.md (and print/plate.3mf if
    trimesh can write one in this environment)
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

from build123d import (Align, Box, Cylinder, Plane, Pos, Rot, Text, export_stl, extrude)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import spec  # noqa: E402
import build  # noqa: E402
import verify  # noqa: E402

M = spec.Merged()
OLSPEC = spec.OpenLock()
OL = spec.as_dict(OLSPEC)
MD = spec.as_dict(M)
TOL = verify.TOL


# ------------------------------------------------------------------ dims
def dims(post: bool = True, chamfer: bool = True) -> dict:
    """Merged socket dimensions: OpenLock's pocket/clip envelope copied straight
    from spec.OpenLock (never re-typed as separate spec.Merged numbers, so there
    is nothing for the two to drift out of sync with) plus spec.Merged's own
    post/plate/jaw numbers."""
    d = {k: OL[k] for k in (
        "mouth_w", "mouth_d", "taper_w0", "taper_x1", "neck_w", "neck_x1", "chamber_w", "chamber_x1",
        "pocket_z0", "pocket_z1", "rim_w", "rim_d", "rim_z0", "rim_h", "wall_t", "wall_mouth_d", "wall_taper_x1",
        "side_t", "side_mouth_h", "side_mouth_d", "side_taper_x1", "side_neck_h", "side_neck_x1",
        "side_chamber_h", "side_chamber_x1", "side_rim_d", "side_rim_t", "side_rim_h",
        "clip_bar_w", "clip_bar_w_v43", "clip_t", "clip_t_v54", "clip_len", "bar_len", "prong_w", "prong_y0", "prong_y1",
        "barb_w", "barb_y0", "barb_y1", "taper_stations", "tip_y", "tip_w",
        "eye_open", "eye_open_y", "eye_max", "eye_max_y", "eye_y9", "eye_tip",
    )}
    d.update({k: MD[k] for k in (
        "tile", "pitch", "base_height", "top_plate", "post_dia", "post_x", "lead_in_chamfer", "cube_edge",
        "jaw_root_w", "jaw_root_y", "jaw_compliance_w", "jaw_compliance_y", "jaw_bite_y", "jaw_cup_dia",
        "jaw_cup_y", "jaw_tip_w", "jaw_tip_y", "thicknesses", "grip_standard", "grip_tight",
        "label_engrave_depth", "label_letter_height", "label_cube_letter_height",
    )})
    d["total_height"] = d["base_height"] + d["top_plate"]
    d["post"] = post
    d["chamfer"] = chamfer
    d["variant"] = "merged"
    d["pocket_h"] = d["pocket_z1"] - d["pocket_z0"]
    d["half_len"] = d["clip_len"] / 2
    return d


CLIP_MATRIX = [(t, grip, *getattr(M, f"grip_{grip}")) for t in M.thicknesses for grip in ("standard", "tight")]
GRIP_LETTER = {"standard": "S", "tight": "T"}


def clip_label(t: float, grip: str) -> str:
    return f"{round(t * 10):02d}{GRIP_LETTER[grip]}"


def cw(d, chamfer: bool) -> float:
    """build.py's ol_floor_negative/ol_wall_negative/ol_sidelock_negative take
    `chamfer` as the wedge WIDTH, not a flag (`if chamfer:` then used directly as
    the numeric argument to lead_in_wedge) -- build.py's own CLI passes the
    argparse bool straight through, which works only by accident because
    `True == 1` gives a 1.0 mm wedge, not the 0.4 mm documented in spec.Process /
    spec.Merged. That mismatch is pre-existing in build.py and out of scope here
    (changing it would move the already-passing scaling results); merged.py
    converts its own bool at the call site instead, so every merged/cube/wall
    negative gets the intended spec.Merged.lead_in_chamfer width."""
    return d["lead_in_chamfer"] if chamfer else 0.0


# ------------------------------------------------------------------ merged socket geometry
def merged_negative(d, chamfer):
    """Same profile as build.ol_floor_negative, but the chamber always stops at
    base_height (the top plate roofs it) instead of following the through/blind
    variant switch -- this is what makes the control coupon printable too."""
    z0, z1 = d["pocket_z0"], d["pocket_z1"]
    mw, md, tw, tx, nw, nx = d["mouth_w"], d["mouth_d"], d["taper_w0"], d["taper_x1"], d["neck_w"], d["neck_x1"]
    plan = [(-build.BUF, -mw / 2), (md, -mw / 2), (md, -tw / 2), (tx, -nw / 2), (nx + build.EPS, -nw / 2),
            (nx + build.EPS, nw / 2), (tx, nw / 2), (md, tw / 2), (md, mw / 2), (-build.BUF, mw / 2)]
    neg = build.prism(plan, z0, z1)
    neg = neg + build.box(nx, d["chamber_x1"], -d["chamber_w"] / 2, d["chamber_w"] / 2, -build.BUF, d["base_height"])
    if chamfer:
        neg = neg + build.lead_in_wedge(mw, d["lead_in_chamfer"], z0, z1)
    return neg


def merged_post(d, height=None):
    r = d["post_dia"] / 2
    h = d["total_height"] if height is None else height
    return Pos(d["post_x"], 0, h / 2) * Cylinder(r, h)


def build_merged_coupon(d, post, chamfer):
    """One coupon (all four edges) plus a single-pocket copy for probing, mirroring
    build.build_openlock's floor_coupon / measure_coupon split."""
    T_, total = d["tile"], d["total_height"]
    tile = build.box(0, T_, 0, T_, 0, total)
    neg = merged_negative(d, chamfer)
    rim = build.ol_rim(d)
    edges = ["x0", "x1", "y0", "y1"]
    for e in edges:
        tile = tile + build.place(rim, e, T_)
    negs = {e: build.place(neg, e, T_) for e in edges}
    for e in edges:
        tile = build.as_part(tile - negs[e])
    posts = {e: build.place(merged_post(d), e, T_) for e in edges} if post else None
    if post:
        for e in edges:
            tile = build.as_part(tile + posts[e])
    single = build.as_part((build.box(0, T_, 0, T_, 0, total) + build.place(rim, "x0", T_)) - negs["x0"])
    if post:
        single = build.as_part(single + posts["x0"])
    return {"floor_coupon": tile, "floor_negative": negs["x0"], "measure_coupon": single,
            "rim": build.place(rim, "x0", T_), "post": posts["x0"] if post else None}


# ------------------------------------------------------------------ merged wall geometry
def build_merged_wall(d, post, chamfer):
    """OpenLock wall coupon (base through-pocket + two vertical side-lock pockets),
    with a short Ø2.0 post across the side-lock pockets only (the base pocket's
    neck is shared between the two mouths, there is no room for a full post there)."""
    T, L, H = d["wall_t"], d["tile"], d["tile"]
    wall = build.box(0, T, 0, L, 0, H)
    wall = wall + build.box(0, T, L / 2 - d["rim_w"] / 2, L / 2 + d["rim_w"] / 2, d["rim_z0"], d["rim_z0"] + d["rim_h"])
    srim = build.box(0, d["side_rim_d"], -d["side_rim_t"] / 2, d["side_rim_t"] / 2, -d["side_rim_h"] / 2, d["side_rim_h"] / 2)
    wall = wall + (Pos(T / 2, 0, H / 2) * Rot(0, 0, 90) * srim) + (Pos(T / 2, L, H / 2) * Rot(0, 0, -90) * srim)
    wneg = Pos(0, L / 2, 0) * build.ol_wall_negative(d, cw(d, chamfer))
    sneg = build.ol_sidelock_negative(d, cw(d, chamfer))
    sneg0 = Pos(T / 2, 0, H / 2) * Rot(0, 0, 90) * sneg
    sneg1 = Pos(T / 2, L, H / 2) * Rot(0, 0, -90) * sneg
    wall = build.as_part(wall - wneg - sneg0 - sneg1)
    post0 = post1 = None
    if post:
        r = d["post_dia"] / 2
        post_local = Rot(90, 0, 0) * (Pos(d["post_x"], 0, 0) * Cylinder(r, d["side_t"]))
        post0 = Pos(T / 2, 0, H / 2) * Rot(0, 0, 90) * post_local
        post1 = Pos(T / 2, L, H / 2) * Rot(0, 0, -90) * post_local
        wall = build.as_part(wall + post0 + post1)
    return {"wall_coupon": wall, "wall_negative": wneg, "sidelock_negative": sneg0,
            "sidelock_post": post0, "sidelock_post_far": post1}


# ------------------------------------------------------------------ six-face cube
CUBE_FACES = [
    # name, kind ("lying"|"standing"|"topbot"), placement transform, label, label origin (u, v) in face-local axes
    ("x0", "lying", lambda s: Pos(-s / 2, 0, 0), "LYING L"),
    ("x1", "lying", lambda s: Pos(s / 2, 0, 0) * Rot(0, 0, 180), "LYING R"),
    ("y0", "standing", lambda s: Pos(0, -s / 2, 0) * Rot(0, 0, 90), "STANDING F"),
    ("y1", "standing", lambda s: Pos(0, s / 2, 0) * Rot(0, 0, -90), "STANDING B"),
    ("z1", "topbot", lambda s: Pos(0, 0, s / 2) * Rot(0, 90, 0), "TOP"),
    ("z0", "topbot", lambda s: Pos(0, 0, -s / 2) * Rot(0, -90, 0), "BOTTOM"),
]
# in-plane (u, v, normal) world axes per face, used for label placement only
CUBE_FACE_AXES = {
    "x0": ((0, 1, 0), (0, 0, 1), (-1, 0, 0)), "x1": ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    "y0": ((1, 0, 0), (0, 0, 1), (0, -1, 0)), "y1": ((1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "z1": ((1, 0, 0), (0, 1, 0), (0, 0, 1)), "z0": ((1, 0, 0), (0, 1, 0), (0, 0, -1)),
}


def _cube_pocket_local(d, kind, chamfer):
    """Pocket negative and post in the canonical local frame later moved onto a
    cube face: 'lying'/'topbot' = the OpenLock BLIND pocket profile (chamber
    confined to pocket_z0..z1, X depth, Y width, Z thin axis) -- a solid cube has
    no top plate to roof an open chamber, so unlike the tile coupon this pocket
    must stay blind, or the post floats inside an oversized cavity and the
    boolean union leaves it as a disconnected island (seen while debugging: the
    tile coupon's merged_negative cuts the chamber down to z=-1, well outside the
    post's z0..z1 span, once there is no top plate above to re-close it).
    'standing' = build.ol_sidelock_negative's frame (X depth, Y thin axis, Z
    width, as at a wall end), already blind by construction (a through-slot in Y,
    which the post spans exactly, flush with the slot walls)."""
    if kind in ("lying", "topbot"):
        neg = build.ol_floor_negative(d, "blind", cw(d, chamfer))
        zc = (d["pocket_z0"] + d["pocket_z1"]) / 2
        post = Pos(d["post_x"], 0, zc) * Cylinder(d["post_dia"] / 2, d["pocket_z1"] - d["pocket_z0"])
    else:
        neg = build.ol_sidelock_negative(d, cw(d, chamfer))
        post = Rot(90, 0, 0) * (Pos(d["post_x"], 0, 0) * Cylinder(d["post_dia"] / 2, d["side_t"]))
    return neg, post


def build_merged_cube(d, chamfer=True):
    """A 50.8 mm cube (2 x tile pitch) with one merged pocket per face, thin axis
    rotated per face (see spec.Merged.sources['cube']), no open bottom (the cube
    is solid, the pocket stays blind against the surrounding mass) and no rim
    positive (deviation: the tile/wall rim register is skipped here to keep the
    six-pocket boolean tractable; see the report)."""
    s = d["cube_edge"]
    cube = Box(s, s, s)
    negs, posts, labels = {}, {}, {}
    for name, kind, xf, label in CUBE_FACES:
        neg_local, post_local = _cube_pocket_local(d, kind, chamfer)
        t = xf(s)
        negs[name] = t * neg_local
        posts[name] = t * post_local
        labels[name] = label
    for name in negs:
        cube = build.as_part(cube - negs[name])
    for name in posts:
        cube = build.as_part(cube + posts[name])
    # engraved face labels, corner region clear of the pocket mouth on every face
    depth, height = d["label_engrave_depth"], d["label_cube_letter_height"]
    u0 = 0.32 * s  # corner offset along each in-plane axis: clear of the pocket mouth (<= ~7 mm) with margin to the edge
    for name, (u_dir, v_dir, n_dir) in CUBE_FACE_AXES.items():
        origin = tuple(u_dir[i] * u0 + v_dir[i] * u0 + n_dir[i] * (s / 2) for i in range(3))
        plane = Plane(origin=origin, x_dir=u_dir, z_dir=n_dir)
        txt = Text(labels[name], font_size=height, align=(Align.CENTER, Align.CENTER))
        cut = plane * extrude(txt, amount=-depth)
        cube = build.as_part(cube - cut)
    return {"cube": cube, "negatives": negs, "posts": posts, "labels": labels}


# ------------------------------------------------------------------ hybrid clip
def hybrid_outline(d, i):
    """Same outline as build.spec_outline_openlock, with the barb width driven by
    the barb interference i (barb_w = neck_w + 2i) instead of the fixed OL6 value."""
    barb_w = d["neck_w"] + 2 * i
    pts = [(d["clip_bar_w"] / 2, 0.0), (d["clip_bar_w"] / 2, d["bar_len"] / 2),
           (d["prong_w"] / 2, d["bar_len"] / 2), (d["prong_w"] / 2, d["prong_y1"]),
           (barb_w / 2, d["barb_y0"]), (barb_w / 2, d["barb_y1"])]
    pts += [(w / 2, y) for w, y in d["taper_stations"]]
    pts += [(d["tip_w"] / 2, d["tip_y"]), (0.0, d["tip_y"])]
    return pts, barb_w


def hybrid_jaw_half(d, b):
    """Jaw slot (right half, half-width at y): root -> compliance widening ->
    bite (narrowed by the post interference b per side) -> cup (post + 0.2
    clearance, at the post's own station y = post_x) -> tip lead-in. Straight
    segments between stations, the same polyline convention build.py already
    uses for the plain OpenLock eye slot and the Dragonbite gap."""
    bite_w = d["post_dia"] - 2 * b
    return [(d["jaw_root_w"] / 2, d["jaw_root_y"]), (d["jaw_compliance_w"] / 2, d["jaw_compliance_y"]),
            (bite_w / 2, d["jaw_bite_y"]), (d["jaw_cup_dia"] / 2, d["jaw_cup_y"]),
            (d["jaw_tip_w"] / 2, d["jaw_tip_y"])], bite_w


def label_cut(text, t, depth, height):
    """Engraving cut on the +Z (top) face of a t-thick part centred at z = 0."""
    txt = Text(text, font_size=height, align=(Align.CENTER, Align.CENTER))
    return Pos(0, 0, t / 2) * extrude(txt, amount=-depth)


def hybrid_clip(d, t, i, b, label):
    outline, barb_w = hybrid_outline(d, i)
    body = build.prism(build.symmetric_outline(outline), -t / 2, t / 2)
    jaw, bite_w = hybrid_jaw_half(d, b)
    slot = build.prism(build.slot_polygon(jaw, d["jaw_tip_y"]), -t, t)
    clip = body - slot - slot.mirror(Plane.XZ)
    try:
        clip = clip - label_cut(label, t, d["label_engrave_depth"], d["label_letter_height"])
        label_method = "text"
    except Exception:
        clip = notch_label(clip, t, label)
        label_method = "notches"
    return clip, barb_w, bite_w, label_method


def notch_label(clip, t, label):
    """Fallback if Build123d Text is unavailable: notches on the tip edges
    (documented in the print README). Not exercised in this environment."""
    n = int(label[:2]) // 10 - 3 if label[:2].isdigit() else 0
    tight = label.endswith("T")
    y = 9.6
    for k in range(max(n, 1)):
        clip = clip - (Pos(6.5, y - 0.7 * k, 0) * Box(0.6, 0.6, t + 0.2))
    if tight:
        clip = clip - (Pos(-6.5, y, 0) * Box(0.6, 0.6, t + 0.2))
    return clip


def reference_clip(d, label="REF"):
    """The reference OpenLOCK clip used throughout section C's cross-checks: v5.4
    thickness (3.5 mm, task table), v5.4 bar width (13.2, spec.OpenLock default),
    plain eye slot -- i.e. `build.ol_clip` in all but the added label."""
    t = d["clip_t_v54"]
    body = build.prism(build.symmetric_outline(build.spec_outline_openlock(d)), -t / 2, t / 2)
    eye = build.spec_eye_openlock(d)
    slot = build.prism(build.slot_polygon(eye, d["tip_y"]), -t, t)
    clip = body - slot - slot.mirror(Plane.XZ)
    clip = clip - label_cut(label, t, d["label_engrave_depth"], d["label_letter_height"])
    return clip, t


def v43_clip(d):
    """The 'official measured OpenLOCK v4.3 clip outline' (spec.OpenLock, OL6
    column v4.3): 14.0 mm bar, plain eye slot, at the dataclass's general clip_t
    (3.6 mm) -- same construction build.py's own `--v43-bar` flag uses (only the
    bar width changes, per derive_openlock)."""
    dd = dict(d)
    dd["clip_bar_w"] = d["clip_bar_w_v43"]
    t = d["clip_t"]
    body = build.prism(build.symmetric_outline(build.spec_outline_openlock(dd)), -t / 2, t / 2)
    eye = build.spec_eye_openlock(dd)
    slot = build.prism(build.slot_polygon(eye, dd["tip_y"]), -t, t)
    return (body - slot - slot.mirror(Plane.XZ)), t


# ------------------------------------------------------------------ verification (spec section C)
def interp(pts, y):
    """Piecewise-linear half-width of a (half-width, y) polyline at y; flat
    beyond the ends (same convention as the eye/gap polylines in spec.py)."""
    if y <= pts[0][1]:
        return pts[0][0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y0 <= y <= y1:
            return x0 if y1 == y0 else x0 + (y - y0) / (y1 - y0) * (x1 - x0)
    return pts[-1][0]


def reference_socket(P=None):
    """Scale-1 reference OpenLOCK through-pocket coupon (build.py's own
    through/no-supports/no-chamfer default), used as the 'official tiles' the
    hybrid clips are cross-checked against in C.1."""
    P = P or spec.Process()
    opts = {"variant": "through", "supports": False, "chamfer": False, "enforce": False, "v43_bar": False}
    d = build.derive_openlock(1.0, P, opts)
    shapes = build.build_openlock(d, "through", False, False)
    return d, shapes


def insertion_check(clip, t, barb_w, d, neg, single):
    """The same protrusion / seated-interference / transit-interference triad as
    verify.verify_case's part (a), parametrised so it can run a clip whose barb
    width or thickness differs from `d`'s own (a hybrid clip probed against the
    stock OpenLock pocket, or the stock clip probed against the merged pocket)."""
    zmid = (d["pocket_z0"] + d["pocket_z1"]) / 2
    tile = d["tile"]
    seated = verify.seated_pose(clip, zmid, tile)
    joint_neg = neg + neg.mirror(Plane.YZ)
    pair = single + single.mirror(Plane.YZ)
    region = verify.barb_region(d, True, tile / 2, zmid)
    prot = seated - joint_neg
    protrusion, prot_barb = verify.vol(prot), verify.vol(prot & region)
    inter = seated & pair
    seated_interf, barb_interf = verify.vol(inter), verify.vol(inter & region)
    shift = (d["barb_y0"] + d["barb_y1"]) / 2 - (d["taper_x1"] + d["neck_x1"]) / 2
    half_len = d["clip_len"] / 2
    ramp = max(0.0, d["neck_x1"] - d["prong_y1"])
    interf_total = barb_w - d["neck_w"]
    barb_expected = 2 * 2 * 0.5 * ramp * (interf_total / 2) * (ramp / (d["barb_y0"] - d["prong_y1"])) * t
    transit = verify.vol((Pos(-shift, 0, 0) * seated) & single)
    transit_upper = interf_total * half_len * t
    outside = protrusion - prot_barb
    barb_ok = abs(barb_interf - barb_expected) <= 0.1 * barb_expected + TOL if barb_expected > 0 else barb_interf <= TOL
    return {"protrusion_mm3": protrusion, "protrusion_outside_barb_mm3": outside, "barb_region_protrusion_mm3": prot_barb,
            "seated_interference_mm3": seated_interf, "barb_seated_interference_mm3": barb_interf,
            "barb_seated_expected_mm3": barb_expected, "barb_ok": bool(barb_ok),
            "transit_interference_mm3": transit, "transit_expected_range_mm3": [TOL, transit_upper],
            "outside_ok": bool(outside < TOL), "transit_ok": bool(TOL < transit < transit_upper)}


def bite_check(seated_clip, post_solid):
    return verify.vol(seated_clip & post_solid) if post_solid is not None else 0.0


def check_c1(P, hybrid_records):
    """C.1: each hybrid clip seated in the reference OpenLOCK through-socket."""
    d, shapes = reference_socket(P)
    out = {}
    for label, rec in hybrid_records.items():
        clip, t, i, b, barb_w, bite_w = rec
        m = insertion_check(clip, t, barb_w, d, shapes["floor_negative"], shapes["measure_coupon"])
        m["barb_interference_i_per_side"] = i
        out[label] = m
    return out, d


def check_c2(d_merged, coupon_post):
    """C.2: the official measured v4.3 clip outline seated in the merged socket
    with post -- minimum clearance between the post and the eye slot (analytic,
    from the OL6 eye-slot polyline at y = post_x, cross-checked by the boolean
    post/clip intersection) and the protrusion volume."""
    clip, t = v43_clip(d_merged)
    eye_pts = build.spec_eye_openlock(d_merged)
    half_width_at_post = interp(eye_pts, d_merged["post_x"])
    clearance = half_width_at_post - d_merged["post_dia"] / 2
    m = insertion_check(clip, t, d_merged["barb_w"], d_merged, coupon_post["floor_negative"], coupon_post["measure_coupon"])
    zmid = (d_merged["pocket_z0"] + d_merged["pocket_z1"]) / 2
    seated = verify.seated_pose(clip, zmid, d_merged["tile"])
    post_interf = bite_check(seated, coupon_post["post"])
    return {"eye_half_width_at_post_x_mm": half_width_at_post, "post_radius_mm": d_merged["post_dia"] / 2,
            "clearance_mm": clearance, "collides": bool(clearance < 0 or post_interf > TOL),
            "post_clip_intersection_mm3": post_interf, "protrusion_outside_barb_mm3": m["protrusion_outside_barb_mm3"],
            "barb_seated_interference_mm3": m["barb_seated_interference_mm3"], "insertion": m}


def check_c3(d_merged, coupon_post, hybrid_records):
    """C.3: each hybrid clip seated in the merged socket (with post) -- protrusion
    excluding barb (tile) and bite (post) interference, both reported separately,
    plus the transit-interference probe."""
    out = {}
    zmid = (d_merged["pocket_z0"] + d_merged["pocket_z1"]) / 2
    for label, rec in hybrid_records.items():
        clip, t, i, b, barb_w, bite_w = rec
        m = insertion_check(clip, t, barb_w, d_merged, coupon_post["floor_negative"], coupon_post["measure_coupon"])
        seated = verify.seated_pose(clip, zmid, d_merged["tile"])
        m["bite_interference_mm3"] = bite_check(seated, coupon_post["post"])
        m["bite_interference_b_per_side"] = b
        out[label] = m
    return out


def check_c4(d_merged, coupon_post, hybrid_records, ref_record):
    """C.4: section measurements at mid pocket height, roof over the mouth/neck
    band vs. over the chamber (post) band, post diameter/position, and clip
    station widths for every clip in the matrix plus the reference clip."""
    single = coupon_post["measure_coupon"]
    zmid = (d_merged["pocket_z0"] + d_merged["pocket_z1"]) / 2
    yc, total = d_merged["tile"] / 2, d_merged["total_height"]
    st = {"mouth_w": d_merged["mouth_d"] / 2, "taper_mid_w": (d_merged["mouth_d"] + d_merged["taper_x1"]) / 2,
          "neck_w": (d_merged["taper_x1"] + d_merged["neck_x1"]) / 2}
    pocket = {k: verify.void_width(single, (x, yc, zmid), 1) for k, x in st.items()}
    pocket["chamber_w_nominal"] = verify.void_width(single, (6.5, yc, zmid), 1)
    # probing the chamber centreline exactly at the post gives 0 (solid there, by
    # design); report the open channel beside the post instead, at its midpoint
    side_off = d_merged["post_dia"] / 2 + (d_merged["chamber_w"] / 2 - d_merged["post_dia"] / 2) / 2
    pocket["chamber_centreline_at_post"] = verify.void_width(single, (d_merged["post_x"], yc, zmid), 1)
    pocket["chamber_side_channel"] = verify.void_width(single, (d_merged["post_x"], yc + side_off, zmid), 1)
    expect = {"mouth_w": d_merged["mouth_w"], "taper_mid_w": (d_merged["taper_w0"] + d_merged["neck_w"]) / 2,
              "neck_w": d_merged["neck_w"], "chamber_w_nominal": d_merged["chamber_w"],
              "chamber_centreline_at_post": 0.0, "chamber_side_channel": d_merged["chamber_w"] / 2 - d_merged["post_dia"] / 2}
    _, roof_mouth = verify.floor_roof(single, st["neck_w"], yc, total)
    floor_mouth, _ = verify.floor_roof(single, st["neck_w"], yc, total)
    _, roof_chamber = verify.floor_roof(single, d_merged["post_x"] + 2.0, yc, total)
    post_dia_measured = verify.solid_extent(single, (d_merged["post_x"], yc, total / 2), 1, containing=True)
    pocket_report = {"expected": expect, "measured": pocket,
                      "roof_over_mouth_neck_mm": roof_mouth, "roof_over_mouth_neck_expected_mm": total - d_merged["pocket_z1"],
                      "roof_over_chamber_mm": roof_chamber, "roof_over_chamber_expected_mm": total - d_merged["base_height"],
                      "floor_mm": floor_mouth, "floor_expected_mm": d_merged["pocket_z0"],
                      "post_dia_expected_mm": d_merged["post_dia"], "post_dia_measured_mm": post_dia_measured,
                      "post_x_expected_mm": d_merged["post_x"]}
    stations = {}
    for label, (clip, t, i, b, barb_w, bite_w) in hybrid_records.items():
        stations[label] = {
            "thickness_expected_mm": t, "thickness_measured_mm": float(clip.bounding_box().max.Z - clip.bounding_box().min.Z),
            "bar_w_mm": verify.solid_extent(clip, (0, 0, 0), 0, containing=False),
            "prong_w_mm": verify.solid_extent(clip, (0, (d_merged["prong_y0"] + d_merged["prong_y1"]) / 2, 0), 0, containing=False),
            "barb_w_measured_mm": verify.solid_extent(clip, (0, (d_merged["barb_y0"] + d_merged["barb_y1"]) / 2, 0), 0, containing=False),
            "barb_w_expected_mm": barb_w,
            "bite_w_measured_mm": verify.void_width(clip, (0, d_merged["jaw_bite_y"], 0), 0, 10),
            "bite_w_expected_mm": bite_w,
            "cup_dia_measured_mm": verify.void_width(clip, (0, d_merged["jaw_cup_y"], 0), 0, 10),
            "cup_dia_expected_mm": d_merged["jaw_cup_dia"],
            "tip_w_mm": verify.solid_extent(clip, (0, d_merged["jaw_tip_y"] - 0.1, 0), 0, containing=False),
        }
    ref_clip, ref_t = ref_record
    stations["REF"] = {
        "thickness_expected_mm": ref_t, "thickness_measured_mm": float(ref_clip.bounding_box().max.Z - ref_clip.bounding_box().min.Z),
        "bar_w_mm": verify.solid_extent(ref_clip, (0, 0, 0), 0, containing=False),
        "prong_w_mm": verify.solid_extent(ref_clip, (0, (d_merged["prong_y0"] + d_merged["prong_y1"]) / 2, 0), 0, containing=False),
        "barb_w_measured_mm": verify.solid_extent(ref_clip, (0, (d_merged["barb_y0"] + d_merged["barb_y1"]) / 2, 0), 0, containing=False),
        "eye_max_measured_mm": verify.void_width(ref_clip, (0, d_merged["eye_max_y"], 0), 0, 30),
        "eye_max_expected_mm": d_merged["eye_max"],
    }
    return pocket_report, stations


# ------------------------------------------------------------------ wall + cube spot-checks
def check_wall_post(d):
    """Wall addendum: does the official v4.3 outline clear the Ø2.0 post now
    standing in the side-lock pocket? Same clip geometry as C.2 (the standing
    pose only reorients it), so the analytic eye-slot/post clearance is
    identical; this re-derives it from the wall's own build for an independent
    boolean cross-check (protrusion against the wall solid, interference with
    the post specifically)."""
    wall = build_merged_wall(d, post=True, chamfer=True)
    clip, t = v43_clip(d)
    T, H = d["wall_t"], d["tile"]
    standing = Pos(T / 2, 0, H / 2) * Rot(0, 90, 0) * clip
    collision = verify.vol(standing & wall["wall_coupon"])
    post_interf = verify.vol(standing & wall["sidelock_post"])
    eye_pts = build.spec_eye_openlock(d)
    clearance = interp(eye_pts, d["post_x"]) - d["post_dia"] / 2
    return {"clearance_mm": clearance, "collides": bool(clearance < 0 or post_interf > TOL),
            "post_clip_intersection_mm3": post_interf, "wall_collision_mm3": collision,
            "note": "same clip geometry and post station as C.2 (y = post_x when seated); only the surrounding pocket differs"}


CUBE_SEAT_KIND = {"x0": "lying", "x1": "lying", "y0": "standing", "y1": "standing", "z1": "topbot", "z0": "topbot"}


def cube_seat_transform(d, name):
    s = d["cube_edge"]
    zmid = (d["pocket_z0"] + d["pocket_z1"]) / 2
    return {
        "x0": Pos(-s / 2, 0, zmid) * Rot(0, 0, -90), "x1": Pos(s / 2, 0, zmid) * Rot(0, 0, 90),
        "y0": Pos(0, -s / 2, 0) * Rot(0, 90, 0), "y1": Pos(0, s / 2, 0) * Rot(0, 90, 180),
        "z1": Pos(zmid, 0, s / 2) * Rot(0, 90, -90), "z0": Pos(-zmid, 0, -s / 2) * Rot(0, 90, 90),
    }[name]


def check_cube_spots(d, cube_shapes, faces=("z1", "z0", "x0", "y0")):
    """Cube addendum: 'the same insertion checks ... at least' for a
    representative face of each pocket orientation (top, bottom, a side-lying
    and a side-standing pocket), each with the hybrid 37S clip and the official
    v4.3 outline. Collision is measured directly against the built cube solid
    (seated & cube), which handles the double-tipped clip model correctly: the
    half that does not enter this blind pocket dangles in free air past the
    face and correctly contributes zero (it is outside the cube, not inside
    material), unlike a check against the local pocket envelope alone."""
    d37 = dims()
    hybrid37, barb_w, bite_w, _ = hybrid_clip(d37, 3.7, *M.grip_standard, "37S")
    v43, t43 = v43_clip(d)
    out = {}
    for name in faces:
        xf = cube_seat_transform(d, name)
        row = {}
        for label, cl in (("37S", hybrid37), ("v43", v43)):
            seated = xf * cl
            row[label] = {"collision_mm3": verify.vol(seated & cube_shapes["cube"]),
                          "post_interference_mm3": verify.vol(seated & cube_shapes["posts"][name])}
        out[name] = row
    return out


# ------------------------------------------------------------------ printability report (addendum item 5)
def printability_report(d):
    """Downward-facing pocket features and their unsupported (bridging) spans per
    exported coupon and print pose. Analytic, from the pocket dimensions -- no
    mesh/overhang analysis, as scoped by the brief."""
    R = []

    def row(coupon, pose, feature, span_mm, note):
        R.append({"coupon": coupon, "pose": pose, "feature": feature, "span_mm": round(span_mm, 2), "note": note})

    row("coupon-merged", "tile flat (top up)", "mouth bridge", d["mouth_w"],
        f"14 x {d['mouth_d']} mm bridge over the mouth cut, at the floor (z {d['pocket_z0']})")
    row("coupon-merged-post", "tile flat (top up)", "chamber roof", (d["chamber_w"] - d["post_dia"]) / 2,
        f"top plate ({d['top_plate']} mm) over the open chamber; the post at x={d['post_x']} splits the {d['chamber_w']} mm "
        "span into two ~5.4 mm half-bridges instead of one 12.8 mm span")
    row("coupon-merged-nopost", "tile flat (top up)", "chamber roof", d["chamber_w"],
        f"same {d['top_plate']} mm top plate, no post: one unsupported {d['chamber_w']} mm bridge")
    row("coupon-openlock-ref", "tile flat (top up)", "chamber roof", d["chamber_w"],
        f"control: same top-plate mechanism as coupon-merged-nopost, {d['chamber_w']} mm bridge")
    row("wall-merged / wall-openlock-ref", "standing (on its base)", "base pocket roof", d["mouth_w"],
        "the base through-pocket's mouth/taper/neck ceiling is a 14 mm bridge near the top of the standing wall")
    row("wall-merged / wall-openlock-ref", "standing (on its base)", "side-lock chamber", d["side_t"],
        f"the vertical side-lock pocket is a through-slot in thickness; each layer bridges only {d['side_t']} mm")
    row("wall-merged / wall-openlock-ref", "lying (on one 25.4 x 25.4 face)", "side-lock chamber", d["side_chamber_h"],
        f"rotated 90 deg, the side-lock chamber's {d['side_chamber_h']} mm height becomes the bridge span; "
        "wall-merged's post sits mid-span and acts as a support, wall-openlock-ref has none")
    row("wall-merged / wall-openlock-ref", "lying (on one 25.4 x 25.4 face)", "base through-pocket", 0.0,
        "prints as a plan profile (the pocket's depth axis is now vertical, its floor/ceiling faces are vertical too): no bridge")
    row("cube-merged-50.8", "one face down (bottom pocket up against the bed)", "bottom-face mouth + chamber roof",
        d["chamber_w"], "the bottom-face pocket opens downward into the bed contact face: its mouth and chamber ceilings print as bridges/overhangs over the void the nozzle cannot reach cleanly on layer 1")
    row("cube-merged-50.8", "one face down", "top-face chamber ledge", (d["chamber_w"] - d["neck_w"]) / 2,
        f"the top-face pocket's neck-to-chamber step overhangs {(d['chamber_w']-d['neck_w'])/2:.2f} mm on each side under the neck (neck {d['neck_w']} widening to chamber {d['chamber_w']})")
    row("cube-merged-50.8", "one face down", "side pockets (4x)", max(d["side_t"], d["mouth_d"]),
        "the four vertical side faces reproduce the wall-standing/-lying bridge cases above, one per face")
    return R


# ------------------------------------------------------------------ print package
PRINT_DIR = HERE / "print"


def norm(shape):
    """Shift a shape so its bounding box minimum is at the origin (Z min = 0,
    the print-pose requirement; X/Y are normalised too for a tidy plate layout)."""
    bb = shape.bounding_box()
    return Pos(-bb.min.X, -bb.min.Y, -bb.min.Z) * shape


def export_print_stl(shape, name, manifest, params):
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    path = PRINT_DIR / f"{name}.stl"
    export_stl(norm(shape), path, tolerance=0.01, angular_tolerance=0.1)
    manifest.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "bytes": path.stat().st_size, "parameters": params})
    return path


def build_print_package(d_post, d_nopost, d_ref, coupon_post, coupon_nopost, coupon_ref,
                         wall_merged, wall_ref, cube_shapes, hybrid_records, ref_clip_rec):
    manifest = []
    # tile coupons
    export_print_stl(coupon_post["floor_coupon"], "coupon-merged-post", manifest,
                      {"post": True, "chamfer": True, "base_height": d_post["base_height"], "top_plate": d_post["top_plate"]})
    export_print_stl(coupon_nopost["floor_coupon"], "coupon-merged-nopost", manifest,
                      {"post": False, "chamfer": True, "base_height": d_nopost["base_height"], "top_plate": d_nopost["top_plate"]})
    export_print_stl(coupon_ref["floor_coupon"], "coupon-openlock-ref", manifest,
                      {"post": False, "chamfer": False, "base_height": d_ref["base_height"], "top_plate": d_ref["top_plate"]})
    # wall coupons, two poses each
    export_print_stl(wall_merged["wall_coupon"], "wall-merged-standing", manifest,
                      {"post": True, "chamfer": True, "pose": "standing on its base"})
    export_print_stl(Rot(0, -90, 0) * wall_merged["wall_coupon"], "wall-merged-lying", manifest,
                      {"post": True, "chamfer": True, "pose": "lying on one 25.4 x 25.4 face"})
    export_print_stl(wall_ref["wall_coupon"], "wall-openlock-ref-standing", manifest,
                      {"post": False, "chamfer": False, "pose": "standing on its base"})
    export_print_stl(Rot(0, -90, 0) * wall_ref["wall_coupon"], "wall-openlock-ref-lying", manifest,
                      {"post": False, "chamfer": False, "pose": "lying on one 25.4 x 25.4 face"})
    # cube
    export_print_stl(cube_shapes["cube"], "cube-merged-50.8", manifest,
                      {"edge": d_post["cube_edge"], "pose": "bottom face (-Z) down", "labels": cube_shapes["labels"]})
    # clips
    for label, (clip, t, i, b, barb_w, bite_w) in hybrid_records.items():
        export_print_stl(clip, f"clip-{label}", manifest,
                          {"thickness": t, "barb_interference_i_per_side": i, "bite_interference_b_per_side": b,
                           "barb_w": barb_w, "bite_w": bite_w, "label_method": "text"})
        if label == "37S":
            export_print_stl(Rot(0, 90, 0) * clip, "clip-37S-onedge", manifest,
                              {"thickness": t, "barb_interference_i_per_side": i, "bite_interference_b_per_side": b,
                               "pose": "standing on its long edge"})
    ref_clip, ref_t = ref_clip_rec
    export_print_stl(ref_clip, "clip-REF", manifest,
                      {"thickness": ref_t, "barb_w": d_post["barb_w"], "note": "plain eye slot, v5.4 bar/thickness"})
    return manifest


def build_plate_3mf(manifest):
    """Lay every printed part out on a 256 x 256 mm plate with 8 mm gaps and try
    trimesh's Scene 3MF export. Returns (ok, message)."""
    try:
        import trimesh
    except Exception as e:  # noqa: BLE001
        return False, f"trimesh unavailable: {e}"
    scene = trimesh.Scene()
    x, y, row_h, plate, gap = 0.0, 0.0, 0.0, 256.0, 8.0
    for entry in manifest:
        p = PRINT_DIR / entry["file"]
        try:
            mesh = trimesh.load(p, force="mesh")
        except Exception as e:  # noqa: BLE001
            return False, f"could not load {p.name}: {e}"
        ext = mesh.extents
        if x + ext[0] > plate:
            x = 0.0
            y += row_h + gap
            row_h = 0.0
        mesh.apply_translation([x - mesh.bounds[0][0], y - mesh.bounds[0][1], -mesh.bounds[0][2]])
        scene.add_geometry(mesh, node_name=entry["file"], geom_name=entry["file"])
        x += ext[0] + gap
        row_h = max(row_h, ext[1])
        if y + row_h > plate:
            return False, "parts do not fit on a single 256 x 256 mm plate at this layout"
    try:
        data = scene.export(file_type="3mf")
    except Exception as e:  # noqa: BLE001
        return False, f"trimesh cannot write 3MF here: {e}"
    (PRINT_DIR / "plate.3mf").write_bytes(data)
    return True, f"wrote plate.3mf ({len(data)} bytes, {len(manifest)} parts)"


# ------------------------------------------------------------------ results writer
def write_results_table(path: Path, c1, c2, c3, pocket_report, stations, wall_post, cube_spots):
    L = ["# Merged socket / hybrid clip results", "",
         "Generated by `merged.py`, scale 1 only. Volumes in mm3; distances in mm. "
         "Full numbers in `merged.json`.", "",
         "## C.1 -- hybrid clips seated in the reference OpenLOCK through-socket", "",
         "| Clip | protrusion outside barb | barb interference (measured/expected) | transit interference | pass |",
         "|---|---|---|---|---|"]
    for label, v in c1.items():
        ok = v["outside_ok"] and v["barb_ok"] and v["transit_ok"]
        L.append(f"| {label} | {v['protrusion_outside_barb_mm3']:.4g} | {v['barb_seated_interference_mm3']:.3g} / "
                 f"{v['barb_seated_expected_mm3']:.3g} | {v['transit_interference_mm3']:.3g} | {'PASS' if ok else 'FAIL'} |")
    L += ["", "## C.2 -- official v4.3 outline seated in the merged socket (with post)", "",
          f"- post-to-eye-slot clearance: **{c2['clearance_mm']:.3f} mm** (eye half-width {c2['eye_half_width_at_post_x_mm']:.3f} "
          f"at y = post_x, post radius {c2['post_radius_mm']:.2f})",
          f"- collides: **{c2['collides']}**; post/clip boolean intersection: {c2['post_clip_intersection_mm3']:.4g} mm3",
          f"- protrusion outside barb: {c2['protrusion_outside_barb_mm3']:.4g} mm3; barb interference: {c2['barb_seated_interference_mm3']:.3g} mm3",
          "", "## C.3 -- hybrid clips seated in the merged socket (with post)", "",
          "| Clip | protrusion outside barb | barb interference | bite interference (post) | transit interference | pass |",
          "|---|---|---|---|---|---|"]
    for label, v in c3.items():
        ok = v["outside_ok"] and v["barb_ok"] and v["transit_ok"]
        L.append(f"| {label} | {v['protrusion_outside_barb_mm3']:.4g} | {v['barb_seated_interference_mm3']:.3g} | "
                 f"{v['bite_interference_mm3']:.3g} | {v['transit_interference_mm3']:.3g} | {'PASS' if ok else 'FAIL'} |")
    L += ["", "## C.4 -- section measurements (mid pocket height)", "",
          "| Quantity | Measured | Expected |", "|---|---|---|"]
    for k, e in pocket_report["expected"].items():
        L.append(f"| {k} | {pocket_report['measured'][k]:.3f} | {e:.3f} |")
    L += [f"| roof over mouth/neck | {pocket_report['roof_over_mouth_neck_mm']:.3f} | {pocket_report['roof_over_mouth_neck_expected_mm']:.3f} |",
          f"| roof over chamber (post band) | {pocket_report['roof_over_chamber_mm']:.3f} | {pocket_report['roof_over_chamber_expected_mm']:.3f} |",
          f"| floor | {pocket_report['floor_mm']:.3f} | {pocket_report['floor_expected_mm']:.3f} |",
          f"| post diameter | {pocket_report['post_dia_measured_mm']:.3f} | {pocket_report['post_dia_expected_mm']:.3f} |",
          f"| post x (from face) | -- | {pocket_report['post_x_expected_mm']:.3f} |", "",
          "### Clip stations", "", "| Clip | thickness | bar w | prong w | barb w | bite w | cup dia | tip w |",
          "|---|---|---|---|---|---|---|---|"]
    for label, s in stations.items():
        if label == "REF":
            L.append(f"| REF | {s['thickness_measured_mm']:.2f} | {s['bar_w_mm']:.2f} | {s['prong_w_mm']:.2f} | "
                     f"{s['barb_w_measured_mm']:.2f} | -- (eye {s['eye_max_measured_mm']:.2f}) | -- | -- |")
        else:
            L.append(f"| {label} | {s['thickness_measured_mm']:.2f} | {s['bar_w_mm']:.2f} | {s['prong_w_mm']:.2f} | "
                     f"{s['barb_w_measured_mm']:.2f} | {s['bite_w_measured_mm']:.2f} | {s['cup_dia_measured_mm']:.2f} | {s['tip_w_mm']:.2f} |")
    L += ["", "## Wall post vs. official v4.3 outline", "",
          f"- clearance: **{wall_post['clearance_mm']:.3f} mm**; collides: **{wall_post['collides']}**; "
          f"post/clip intersection: {wall_post['post_clip_intersection_mm3']:.4g} mm3; wall collision: {wall_post['wall_collision_mm3']:.4g} mm3",
          "", "## Cube spot-checks (collision with the built solid, post interference)", "",
          "| Face | Clip | collision mm3 | post interference mm3 |", "|---|---|---|---|"]
    for face, row in cube_spots.items():
        for label, v in row.items():
            L.append(f"| {face} | {label} | {v['collision_mm3']:.4g} | {v['post_interference_mm3']:.4g} |")
    L.append("")
    path.write_text("\n".join(L))


def main():
    P = spec.Process()
    d_post = dims(post=True, chamfer=True)
    d_nopost = dims(post=False, chamfer=True)
    d_ref = dims(post=False, chamfer=False)

    coupon_post = build_merged_coupon(d_post, True, True)
    coupon_nopost = build_merged_coupon(d_nopost, False, True)
    coupon_ref = build_merged_coupon(d_ref, False, False)
    for name, c in (("merged-post", coupon_post), ("merged-nopost", coupon_nopost), ("openlock-ref", coupon_ref)):
        t = c["floor_coupon"]
        print(f"coupon {name:14s} solids={len(t.solids())} valid={t.is_valid} vol={t.volume:.1f}", flush=True)

    wall_merged = build_merged_wall(d_post, True, True)
    wall_ref = build_merged_wall(d_ref, False, False)
    for name, w in (("wall-merged", wall_merged), ("wall-ref", wall_ref)):
        c = w["wall_coupon"]
        print(f"{name:14s} solids={len(c.solids())} valid={c.is_valid} vol={c.volume:.1f}", flush=True)

    cube_shapes = build_merged_cube(d_post, chamfer=True)
    print(f"cube           solids={len(cube_shapes['cube'].solids())} valid={cube_shapes['cube'].is_valid} "
          f"vol={cube_shapes['cube'].volume:.1f}", flush=True)

    hybrid_records = {}
    for t, grip, i, b in CLIP_MATRIX:
        label = clip_label(t, grip)
        clip, barb_w, bite_w, method = hybrid_clip(d_post, t, i, b, label)
        hybrid_records[label] = (clip, t, i, b, barb_w, bite_w)
        print(f"clip {label} solids={len(clip.solids())} valid={clip.is_valid} vol={clip.volume:.1f} label_method={method}", flush=True)
    ref_clip_rec = reference_clip(d_post, "REF")
    print(f"clip REF solids={len(ref_clip_rec[0].solids())} valid={ref_clip_rec[0].is_valid} vol={ref_clip_rec[0].volume:.1f}", flush=True)

    c1, d_ref_socket = check_c1(P, hybrid_records)
    c2 = check_c2(d_post, coupon_post)
    c3 = check_c3(d_post, coupon_post, hybrid_records)
    pocket_report, stations = check_c4(d_post, coupon_post, hybrid_records, ref_clip_rec)
    wall_post = check_wall_post(d_post)
    cube_spots = check_cube_spots(d_post, cube_shapes)
    printability = printability_report(d_post)

    failed = []
    for label, v in c1.items():
        if not (v["outside_ok"] and v["barb_ok"] and v["transit_ok"]):
            failed.append(f"C1 {label}")
    for label, v in c3.items():
        if not (v["outside_ok"] and v["barb_ok"] and v["transit_ok"]):
            failed.append(f"C3 {label}")
    if c2["collides"]:
        failed.append("C2 (v4.3 vs post)")
    if wall_post["collides"]:
        failed.append("wall post vs v4.3")

    results = {
        "lab": "tile-clip-sockets/merged", "build123d": __import__("build123d").__version__,
        "scale": 1.0, "process": spec.as_dict(P), "merged_spec": spec.as_dict(M),
        "dims_merged_post": {k: v for k, v in d_post.items() if not isinstance(v, dict)},
        "hybrid_clip_matrix": [{"label": clip_label(t, grip), "t": t, "grip": grip, "i": i, "b": b} for t, grip, i, b in CLIP_MATRIX],
        "c1_hybrid_in_reference_socket": c1,
        "c2_v43_in_merged_socket_with_post": c2,
        "c3_hybrid_in_merged_socket": c3,
        "c4_section_measurements": {"pocket": pocket_report, "clip_stations": stations},
        "wall_post_vs_v43_outline": wall_post,
        "cube_spot_checks": cube_spots,
        "printability_report": printability,
        "flags": failed,
        "physical_print": "not performed", "physical_fit": "not measured", "strength": "not tested",
    }
    res = HERE / "results"
    res.mkdir(exist_ok=True)
    (res / "merged.json").write_text(json.dumps(results, indent=2, default=str) + "\n")
    write_results_table(res / "merged-table.md", c1, c2, c3, pocket_report, stations, wall_post, cube_spots)
    print("status:", "passed" if not failed else f"{len(failed)} check(s) failed: {failed}", flush=True)

    manifest = build_print_package(d_post, d_nopost, d_ref, coupon_post, coupon_nopost, coupon_ref,
                                    wall_merged, wall_ref, cube_shapes, hybrid_records, ref_clip_rec)
    ok3mf, msg3mf = build_plate_3mf(manifest)
    print("3mf:", ok3mf, msg3mf, flush=True)
    (PRINT_DIR / "manifest.json").write_text(json.dumps({
        "lab": "tile-clip-sockets/merged", "generated_by": "labs/tile-clip-sockets/merged.py",
        "plate_3mf": {"written": ok3mf, "message": msg3mf}, "files": manifest,
    }, indent=2, default=str) + "\n")
    write_print_readme(PRINT_DIR / "README.md", d_post, printability, ok3mf, msg3mf)
    print("done. failed:", failed, flush=True)
    raise SystemExit(1 if failed else 0)


# ------------------------------------------------------------------ print/README.md
def write_print_readme(path: Path, d, printability, ok3mf, msg3mf):
    rows = "\n".join(f"| {r['coupon']} | {r['pose']} | {r['feature']} | {r['span_mm']} | {r['note']} |" for r in printability)
    variant_rows = "\n".join(f"| {clip_label(t, g)} | {t:.1f} | {i:.2f} | {b:.2f} |" for t, g, i, b in CLIP_MATRIX)
    variant_rows += f"\n| REF | {d['clip_t_v54']:.1f} | {(d['barb_w']-d['neck_w'])/2:.2f} | -- (plain eye slot) |"
    three_mf = f"`plate.3mf` was written ({msg3mf})." if ok3mf else f"`plate.3mf` was **not** written: {msg3mf}. Import the individual STLs instead."
    text = f"""# Print package -- merged socket / hybrid clip

Generated by `labs/tile-clip-sockets/merged.py`. Everything here is scale 1. See
`../results/merged.json` and `../results/merged-table.md` for the geometric
checks behind these parts; nothing here has been printed yet.

## What to print

| Qty | File | Notes |
|---|---|---|
| 2 | `coupon-merged-post.stl` | the actual merged design: post + 0.4 mm lead-in chamfer |
| 1 | `coupon-merged-nopost.stl` | same pocket, no post (post is optional per the brief) |
| 1 | `coupon-openlock-ref.stl` | control: reference OpenLOCK through-pocket, same 1.2 mm top plate so it prints |
| 1 | `wall-merged-standing.stl` + `wall-merged-lying.stl` | merged wall, both print orientations |
| 1 | `wall-openlock-ref-standing.stl` + `wall-openlock-ref-lying.stl` | control wall, both orientations |
| 2 | `cube-merged-50.8.stl` | six-face pocket cube, one face down |
| 2 each | `clip-35S.stl` `clip-35T.stl` `clip-37S.stl` `clip-37T.stl` `clip-39S.stl` `clip-39T.stl` `clip-REF.stl` | flat, engraving up |
| 1 | `clip-37S-onedge.stl` | same 37S clip, standing on its long edge -- compare flat vs. on-edge printing |

{three_mf}

## Print settings (Bambu Lab A1, 0.4 mm nozzle, PLA)

- Layer height 0.2 mm, 3 walls, 4 top/bottom layers, 15% infill.
- Clips: flat orientation, **no brim, no raft**, no supports.
- Tiles/walls/cube: brim optional (helps the small footprint of the standing wall), no supports --
  every downward-facing pocket feature below is a bridge or a shallow overhang, not an enclosed void.
- `clip-37S-onedge.stl`: no supports; expect a rougher jaw-slot surface than the flat print, that is
  the point of the comparison.

## Orientation and printability

Every pocket has a downward-facing ceiling somewhere; the table below lists the actual bridge/overhang
spans (computed from the pocket dimensions, not a mesh/slicer analysis -- see `results/merged.json`
key `printability_report` for the same table with the raw numbers).

| Coupon | Pose | Feature | Span (mm) | Note |
|---|---|---|---|---|
{rows}

What to look at after printing:

- **Sagging over the mouth**: the 14 mm mouth bridge (tile flat, wall standing) is the widest
  unsupported span in the set; check the mouth opening is still the right width and not drooping
  into the taper.
- **Elephant's foot at the lead-in**: the 0.4 mm chamfer sits right at the first layers on the
  contact face; over-squished first layers will fill it in and the clip will not lead in cleanly.
- **Post adhesion**: the post is a small-diameter (Ø2.0) column bridging from the bed/floor to the
  top plate (tile) or standing alone across a slot (wall/cube side-lock); if it does not adhere well
  on layer 1 it can lean or snap off before the top plate closes over it.
- **First-layer squish in the clip thickness**: the thinnest clip (3.5 mm, REF) is 17-18 layers at
  0.2 mm; a fat first layer eats a larger fraction of that than it does on the tile, so check the
  clip still measures its nominal thickness with calipers before fitting it.

## Hybrid clip variants

| Label | thickness t (mm) | barb interference i per side (mm) | bite interference b per side (mm) |
|---|---|---|---|
{variant_rows}

## Cube face labels

`cube-merged-50.8.stl` carries one engraved label per face (Build123d Text, 0.4 mm deep, ~5 mm letters),
placed in a corner clear of that face's pocket mouth:

| Face | Label | Pocket thin axis |
|---|---|---|
| +Z (up in print pose) | TOP | along X |
| -Z (down, on the bed) | BOTTOM | along X |
| -X | LYING L | vertical (Z) -- floor-tile-edge style |
| +X | LYING R | vertical (Z) -- floor-tile-edge style |
| -Y | STANDING F | horizontal (X) -- wall-end style |
| +Y | STANDING B | horizontal (X) -- wall-end style |

Text engraving worked in this environment (`build123d.Text`); the notch fallback in `merged.py`
(`notch_label`) was not exercised.

## Test protocol

Test these combinations first: **ref clip in ref socket** (both controls, should match the existing
OpenLOCK lab), **merged clip in merged socket** (the actual design), **ref clip in merged socket**
(does an official clip still enter our tile, C.2 -- also try REF against the wall's side-lock post),
**merged clip in ref socket** (does our clip still enter an official tile, C.1). Then work through the
grip/thickness matrix.

| Clip | Socket | Hand fit (loose/snug/forced/no-go) | Vertical play (feeler gauge, mm) | Pull-apart holding (rank 1-7) | Survives 5 insertions (Y/N) | Notes |
|---|---|---|---|---|---|---|
| REF | coupon-openlock-ref | | | | | |
| REF | coupon-merged-post | | | | | |
| 35S | coupon-merged-post | | | | | |
| 35T | coupon-merged-post | | | | | |
| 37S | coupon-merged-post | | | | | |
| 37S | coupon-openlock-ref | | | | | |
| 37S (on edge) | coupon-merged-post | | | | | |
| 37T | coupon-merged-post | | | | | |
| 39S | coupon-merged-post | | | | | |
| 39T | coupon-merged-post | | | | | |
| REF | wall-openlock-ref (side-lock) | | | | | |
| REF | wall-merged (side-lock, post) | | | | | |
| 37S | wall-merged (side-lock, post) | | | | | |
| 37S | cube-merged-50.8 (top) | | | | | |
| 37S | cube-merged-50.8 (bottom) | | | | | |
| 37S | cube-merged-50.8 (a lying side) | | | | | |
| 37S | cube-merged-50.8 (a standing side) | | | | | |

## manifest.json

`manifest.json` lists every file above with its sha256 and the parameters used to build it.
"""
    path.write_text(text)


if __name__ == "__main__":
    main()
