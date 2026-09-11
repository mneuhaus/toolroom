"""Geometric verification of the built coupons and clips.

Used by build.py (verify_case) on the in-memory solids, and standalone:

    uv run python labs/tile-clip-sockets/verify.py

which re-hashes every export listed in results/summary.json, imports every STEP
back into Build123d, checks validity and volume, and validates the SVG as XML.
All checks are geometric; nothing here establishes a physical fit or strength.
"""
from __future__ import annotations
import hashlib, json, sys, xml.etree.ElementTree as ET
from pathlib import Path

from build123d import Box, Plane, Pos, Rot, import_step

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOL = 1e-3          # mm^3: protrusion / seated interference above this is a finding
PROBE = 0.02        # mm: probe bar cross-section
MEAS_TOL = 0.02     # mm: measured section width vs expected


def vol(shape) -> float:
    if shape is None:
        return 0.0
    try:
        solids = shape.solids()
    except AttributeError:
        return 0.0
    return float(sum(abs(s.volume) for s in solids))


def _bar(center, axis, length):
    size = [PROBE, PROBE, PROBE]
    size[axis] = length
    return Pos(*center) * Box(*size)


def _piece_containing(solids, point, axis):
    for s in solids:
        bb = s.bounding_box()
        lo, hi = tuple(bb.min)[axis], tuple(bb.max)[axis]
        if lo - 1e-6 <= point[axis] <= hi + 1e-6:
            return s
    return None


def void_width(solid, center, axis, length=40.0):
    """Width of the empty space through `center` along `axis` (pocket width, slot gap)."""
    void = _bar(center, axis, length) - solid
    piece = _piece_containing(void.solids(), center, axis)
    if piece is None:
        return 0.0
    bb = piece.bounding_box()
    return float(tuple(bb.max)[axis] - tuple(bb.min)[axis])


def void_reach(solid, start, axis, length=60.0):
    """How far the empty space that starts at `start` reaches along +axis (pocket depth)."""
    c = list(start)
    c[axis] += length / 2
    void = _bar(c, axis, length) - solid
    piece = _piece_containing(void.solids(), start, axis)
    if piece is None:
        return 0.0
    return float(tuple(piece.bounding_box().max)[axis] - start[axis])


def solid_extent(solid, center, axis, length=40.0, containing=True):
    """Extent of material along `axis`: the piece containing `center` (containing=True)
    or the overall bounding extent of all pieces (outer width of a slotted clip)."""
    hit = _bar(center, axis, length) & solid
    solids = hit.solids()
    if not solids:
        return 0.0
    if containing:
        piece = _piece_containing(solids, center, axis)
        if piece is None:
            return 0.0
        bb = piece.bounding_box()
    else:
        bb = hit.bounding_box()
    return float(tuple(bb.max)[axis] - tuple(bb.min)[axis])


def floor_roof(solid, x, y, base):
    """Material below and above the pocket on a vertical probe; None = open."""
    hit = _bar((x, y, base / 2), 2, base + 2) & solid
    pieces = sorted(hit.solids(), key=lambda s: s.bounding_box().min.Z)
    if not pieces:
        return None, None
    bot, top = pieces[0].bounding_box(), pieces[-1].bounding_box()
    floor = float(bot.max.Z - bot.min.Z) if bot.min.Z < 1e-6 else 0.0
    roof = float(top.max.Z - top.min.Z) if top.max.Z > base - 1e-6 else 0.0
    if len(pieces) == 1:  # solid through: no pocket on this probe
        return floor, roof
    return floor, roof


def seated_pose(clip, zmid, tile):
    """Clip lying in the x0-edge pocket of a tile x tile coupon, bar centred on the joint plane x = 0."""
    return Pos(0, tile / 2, zmid) * Rot(0, 0, -90) * clip


def barb_region(d, ol, center_y, zmid, axis=0):
    """Joint-frame region where the clip is meant to touch the pocket: beyond the
    prong end (OpenLOCK barb ramp meets the neck edge) / beyond the post nose (Dragonbite)."""
    start = d["prong_y1"] if ol else d["post_nose_x"]
    big = Pos(0, center_y, zmid) * Box(60, 60, 60)
    inner = Pos(0, center_y, zmid) * Box(2 * start, 60, 60) if axis == 0 else Pos(center_y, 0, zmid) * Box(60, 2 * start, 60)
    if axis == 1:
        big = Pos(center_y, 0, zmid) * Box(60, 60, 60)
    return big - inner


def verify_case(system, S, d, shapes, P) -> dict:
    tile, neg, clip = shapes["floor_coupon"], shapes["floor_negative"], shapes["clip"]
    single = shapes.get("measure_coupon", tile)   # one pocket: simpler booleans for probes and the insertion check
    flags = []
    ol = system == "openlock"
    z0, z1 = (d["pocket_z0"], d["pocket_z1"]) if ol else (d["throat_z0"], d["throat_z1"])
    zmid = (z0 + z1) / 2
    yc, base = d["tile"] / 2, d["base_height"]
    # (a) insertion check
    seated = seated_pose(clip, zmid, d["tile"])
    joint_neg = neg + neg.mirror(Plane.YZ)
    pair = single + single.mirror(Plane.YZ)
    region = barb_region(d, ol, yc, zmid)
    prot = seated - joint_neg
    protrusion, prot_barb = vol(prot), vol(prot & region)
    inter = seated & pair
    seated_interf, barb_interf = vol(inter), vol(inter & region)
    if ol:
        shift = (d["barb_y0"] + d["barb_y1"]) / 2 - (d["taper_x1"] + d["neck_x1"]) / 2
        interf_total, half_len = d["barb_w"] - d["neck_w"], d["clip_len"] / 2
        # barb ramp (prong end -> barb start) inside the neck, both flanks, both tiles
        ramp = max(0.0, d["neck_x1"] - d["prong_y1"])
        barb_expected = 2 * 2 * 0.5 * ramp * (interf_total / 2) * (ramp / (d["barb_y0"] - d["prong_y1"])) * d["clip_t"]
    else:
        shift = d["gap_bite_y"] - d["head_cx"]
        interf_total, half_len = d["head_d"] - d["gap_bite"], d["half_len"]
        barb_expected = 0.0   # cup and bite clear the post head when seated (DL4 fit check)
    transit = vol((Pos(-shift, 0, 0) * seated) & single)
    transit_upper = interf_total * half_len * d["clip_t"]
    support_hit = vol(seated & shapes["supports"]) if shapes.get("supports") is not None else None
    outside = protrusion - prot_barb
    stray = seated_interf - barb_interf
    barb_ok = abs(barb_interf - barb_expected) <= 0.1 * barb_expected + TOL
    passed = outside < TOL and stray < TOL and TOL < transit < transit_upper and barb_ok
    if outside >= TOL: flags.append("protrusion")
    if stray >= TOL: flags.append("seated_interference_outside_barb")
    if not barb_ok: flags.append("barb_seated_interference_unexpected")
    if not (TOL < transit < transit_upper): flags.append("transit_interference_out_of_range")
    insertion = {"pose": "bar centred on the joint plane between the coupon and its mirror image, clip centred in the pocket band",
                 "protrusion_mm3": protrusion, "protrusion_outside_barb_mm3": outside, "barb_region_protrusion_mm3": prot_barb,
                 "seated_interference_mm3": seated_interf, "barb_seated_interference_mm3": barb_interf,
                 "barb_seated_expected_mm3": barb_expected,
                 "barb_region": ("|x| >= prong end %.3f (barb ramp against the neck edge)" % d["prong_y1"]) if ol
                                else ("|x| >= post nose %.3f (jaws around the post)" % d["post_nose_x"]),
                 "transit_pose_shift_mm": shift, "transit_interference_mm3": transit,
                 "transit_expected_range_mm3": [TOL, transit_upper],
                 "support_bar_overlap_mm3": support_hit, "passed": passed}
    # (b) section measurements at mid pocket height
    if ol:
        st = {"mouth_w": d["mouth_d"] / 2, "taper_mid_w": (d["mouth_d"] + d["taper_x1"]) / 2,
              "neck_w": (d["taper_x1"] + d["neck_x1"]) / 2, "chamber_w": (d["neck_x1"] + d["chamber_x1"]) / 2}
        expect = {"mouth_w": d["mouth_w"], "taper_mid_w": (d["taper_w0"] + d["neck_w"]) / 2, "neck_w": d["neck_w"], "chamber_w": d["chamber_w"]}
        pocket = {k: void_width(single, (x, yc, zmid), 1) for k, x in st.items()}
        pocket["depth"] = void_reach(single, (-0.5, yc, zmid), 0)
        pocket["depth_expected"] = d["chamber_x1"] + 0.5
        f, r = floor_roof(single, st["neck_w"], yc, base)
        pocket["floor"], pocket["roof"] = f, r
        fc, rc = floor_roof(single, st["chamber_w"], yc, base)
        pocket["floor_chamber"], pocket["roof_chamber"] = (fc if fc else None), (rc if rc else None)
    else:
        st = {"mouth_w": d["lip_d"] / 2, "cavity_front_w": (d["lip_d"] + d["post_nose_x"]) / 2,
              "chamber_w": (d["head_cx"] + d["head_d"] / 2 + d["cavity_x1"]) / 2}   # behind the head: neck beside cavity wall
        expect = {"mouth_w": d["throat_w"], "cavity_front_w": d["cavity_w"], "chamber_w": (d["cavity_w"] - d["post_neck_w"]) / 2}
        pocket = {"mouth_w": void_width(single, (st["mouth_w"], yc, zmid), 1),
                  "cavity_front_w": void_width(single, (st["cavity_front_w"], yc, zmid), 1),
                  "chamber_w": void_width(single, (st["chamber_w"], yc + d["post_neck_w"] / 2 + 0.5, zmid), 1)}
        pocket["neck_w"] = solid_extent(single, (d["head_cx"], yc, zmid), 1)   # post head diameter
        expect["neck_w"] = d["head_d"]
        pocket["post_nose_x"] = void_reach(single, (-0.5, yc, zmid), 0) - 0.5
        pocket["post_nose_expected"] = d["post_nose_x"]
        pocket["depth"] = void_reach(single, (-0.5, yc + d["head_d"] / 2 + 0.5, zmid), 0)   # beside the head, to the back wall
        pocket["depth_expected"] = d["cavity_x1"] + 0.5
        f, r = floor_roof(single, st["mouth_w"], yc, base)
        pocket["floor"], pocket["roof"] = f, r
        fc, rc = floor_roof(single, (d["lip_d"] + d["post_nose_x"]) / 2, yc + d["pad_w"] / 2 + 0.5, base)
        pocket["floor_cavity"], pocket["roof_cavity"] = (fc if fc else None), (rc if rc else None)
    rim_bb = shapes["rim"].bounding_box()
    pocket["rim_side"] = float((rim_bb.max.Y - rim_bb.min.Y) - pocket["mouth_w"]) / 2
    pocket["expected"] = expect
    for k, e in expect.items():
        if abs(pocket[k] - e) > MEAS_TOL:
            flags.append(f"section_{k}_deviates")
    if abs(pocket["depth"] - pocket["depth_expected"]) > MEAS_TOL:
        flags.append("section_depth_deviates")
    # clip stations (clip frame: X width, Y length)
    bb = clip.bounding_box()
    cm = {"thickness": float(bb.max.Z - bb.min.Z), "length": float(bb.max.Y - bb.min.Y),
          "bar_w": solid_extent(clip, (0, 0, 0), 0, containing=False)}
    if ol:
        cm["prong_w"] = solid_extent(clip, (0, (d["prong_y0"] + d["prong_y1"]) / 2, 0), 0, containing=False)
        cm["barb_w"] = solid_extent(clip, (0, (d["barb_y0"] + d["barb_y1"]) / 2, 0), 0, containing=False)
        cm["tip_w"] = solid_extent(clip, (0, d["tip_y"] - 0.05 * S, 0), 0, containing=False)
        cm["eye_max"] = void_width(clip, (0, d["eye_max_y"], 0), 0, 30)
        cexp = {"thickness": d["clip_t"], "length": d["clip_len"], "bar_w": d["clip_bar_w"], "prong_w": d["prong_w"],
                "barb_w": d["barb_w"], "eye_max": d["eye_max"]}
    else:
        cm["neck_w"] = solid_extent(clip, (0, (d["jaw_neck_y0"] + d["jaw_neck_y1"]) / 2, 0), 0, containing=False)
        cm["max_w"] = solid_extent(clip, (0, (d["jaw_max_y0"] + d["jaw_max_y1"]) / 2, 0), 0, containing=False)
        cm["tip_w"] = solid_extent(clip, (0, d["half_len"] - 0.05 * S, 0), 0, containing=False)
        cm["gap_cup"] = void_width(clip, (0, d["gap_cup_y"], 0), 0, 30)
        cm["gap_bite"] = void_width(clip, (0, d["gap_bite_y"], 0), 0, 30)
        cexp = {"thickness": d["clip_t"], "length": d["clip_len"], "bar_w": d["clip_bar_w"], "neck_w": d["jaw_neck_w"],
                "max_w": d["jaw_max_w"], "gap_cup": d["gap_cup"], "gap_bite": d["gap_bite"]}
    cm["expected"] = cexp
    for k, e in cexp.items():
        if abs(cm[k] - e) > MEAS_TOL:
            flags.append(f"clip_{k}_deviates")
    # (c) floors
    if pocket["roof"] is not None and pocket["roof"] < P.roof_min - 1e-6: flags.append("roof_below_min")
    if pocket["floor"] is not None and pocket["floor"] < P.floor_min - 1e-6: flags.append("floor_below_min")
    if pocket["rim_side"] < P.rim_min - 1e-6: flags.append("rim_below_min")
    # (d) validity and volumes
    validity = {k: {"valid": bool(v.is_valid), "solids": len(v.solids()), "volume_mm3": vol(v)}
                for k, v in shapes.items() if v is not None and k not in ("rim", "supports", "measure_coupon")}
    for k, v in validity.items():
        if not v["valid"]:
            flags.append(f"{k}_invalid")
        elif k == "floor_coupon" and v["solids"] == 2 and ol and d.get("variant") == "through":
            flags.append("through_centre_island")   # four through-chambers on a 1 inch base isolate the 4 mm centre (OF base needs its topper)
        elif v["solids"] != 1:
            flags.append(f"{k}_{v['solids']}_solids")
    result = {"insertion": insertion, "measurements": {"pocket": pocket, "clip": cm}, "validity": validity,
              "volumes": {"clip_mm3": vol(clip), "floor_coupon_mm3": vol(tile)}, "flags": flags}
    if ol:
        result["wall"] = verify_wall(d, shapes, zmid, flags)
    return result


def verify_wall(d, shapes, zmid, flags):
    wall, wneg, sneg, clip = shapes["wall_coupon"], shapes["wall_negative"], shapes["sidelock_negative"], shapes["clip"]
    T, L, H = d["wall_t"], d["tile"], d["tile"]
    seated = Pos(0, L / 2, zmid) * Rot(0, 0, -90) * clip
    half_in = seated & Pos(25, L / 2, zmid) * Box(50, 50, 50)
    through_prot, through_int = vol(half_in - wneg), vol(seated & wall)
    standing = Pos(T / 2, 0, H / 2) * Rot(0, 90, 0) * clip
    half_in = standing & Pos(T / 2, 25, H / 2) * Box(50, 50, 50)
    region = barb_region(d, True, T / 2, H / 2, axis=1)
    sprot = half_in - sneg
    side_prot, side_prot_barb = vol(sprot), vol(sprot & region)
    sint = standing & wall
    side_int, side_barb = vol(sint), vol(sint & region)
    depth = void_reach(wall, (T / 2, -0.5, H / 2), 1) - 0.5
    through_w = void_width(wall, (d["wall_mouth_d"] / 2, L / 2, zmid), 1)
    neck_w = void_width(wall, (T / 2, L / 2, zmid), 1)
    side_h = void_width(wall, (T / 2, d["side_mouth_d"] / 2, H / 2), 2)
    if through_prot >= TOL: flags.append("wall_through_bar_clash")
    if side_prot - side_prot_barb >= TOL: flags.append("sidelock_protrusion")
    return {"through_protrusion_mm3": through_prot, "through_interference_mm3": through_int,
            "through_mouth_w": through_w, "through_neck_w": neck_w,
            "sidelock_protrusion_mm3": side_prot, "sidelock_protrusion_outside_barb_mm3": side_prot - side_prot_barb,
            "sidelock_interference_mm3": side_int, "sidelock_barb_interference_mm3": side_barb,
            "sidelock_depth": depth, "sidelock_depth_expected": d["side_chamber_x1"],
            "sidelock_mouth_h": side_h, "sidelock_mouth_h_expected": d["side_mouth_h"],
            "volume_mm3": vol(wall), "valid": bool(wall.is_valid), "solids": len(wall.solids())}


def main():
    summary = json.loads((HERE / "results" / "summary.json").read_text())
    problems = []
    n_files = n_steps = 0
    for case in summary["cases"]:
        for rel, digest in case["exports"].items():
            p = ROOT / rel
            n_files += 1
            if not p.exists():
                problems.append(f"missing {rel}"); continue
            if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                problems.append(f"sha256 mismatch {rel}")
            if p.suffix == ".step":
                n_steps += 1
                shape = import_step(p)
                key = p.stem.split("-", 2)[2].replace("-", "_")
                recorded = case["validity"].get(key)
                if not shape.is_valid:
                    problems.append(f"invalid STEP {rel}")
                if recorded and abs(vol(shape) - recorded["volume_mm3"]) > 1e-3 * max(1.0, recorded["volume_mm3"]):
                    problems.append(f"volume mismatch {rel}: {vol(shape):.3f} vs {recorded['volume_mm3']:.3f}")
        if not case["insertion"]["passed"]:
            problems.append(f"insertion check failed: {case['system']} S={case['scale']}")
    svg = ROOT / "site" / "assets" / "tile-clips-sections.svg"
    try:
        root = ET.parse(svg).getroot()
        if not root.tag.endswith("svg") or "viewBox" not in root.attrib:
            problems.append("svg: no viewBox")
    except Exception as e:  # noqa: BLE001
        problems.append(f"svg: {e}")
    print(json.dumps({"files": n_files, "step_reimported": n_steps, "svg_bytes": svg.stat().st_size if svg.exists() else 0,
                      "problems": problems, "status": "passed" if not problems else "findings"}, indent=2))
    raise SystemExit(0 if not problems else 1)


if __name__ == "__main__":
    main()
