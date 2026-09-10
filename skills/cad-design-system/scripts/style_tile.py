#!/usr/bin/env python3
"""style_tile.py — generate the physical "style tile" from a design-language profile and a
manufacturing profile (build123d). Prints the profile's decisions on one 60 x 40 mm block:

  * plan-view corner radius, top edge treatment (chamfer/fillet), bottom chamfer
  * a reveal groove at plate_thickness below the top if the style has layering
  * a two-colour label (separate body, inlay depth from the mfg profile)
  * a grille patch (round holes or slots) in a 20 x 14 field
  * four insert holes in the fastener pattern
  * one knob cap (separate body) with its indicator inlay

Outputs one STL per body in shared assembly coordinates plus one STEP.
Feed the STLs to the slicer as one multi-part object; assign filaments by name.
Inlay bodies intentionally sit above Z=0. This is a generic enclosure demonstration,
not a test of the user's structural parts, custom fasteners or actual glyph size.

Usage:
  style_tile.py --style profiles/design-language/te-like.yaml \
                --mfg profiles/manufacturing/fdm-bambu-a1-0.4.yaml --out tile/ [--font "DejaVu Sans"]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:
    import yaml
    from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Circle, Compound, Cone, Cylinder,
                           FontStyle, GeomType, GridLocations, Location, Locations, Mode, Plane, Rectangle, RectangleRounded,
                           Text, chamfer, export_step, export_stl, extrude, fillet, offset)
except ImportError as e:  # pragma: no cover
    print(f"missing dependency: {e}. pip install build123d pyyaml", file=sys.stderr)
    sys.exit(2)

TILE_W, TILE_D, TILE_H = 60.0, 40.0, 12.0


def load(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def g(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d if d is not None else default


def q(value: float, step: float) -> float:
    """Quantise to a process step (layer height) — never below one step."""
    if not step:
        return value
    return max(step, round(value / step) * step)


def build(style: dict, mfg: dict, font: str | None):
    method = g(style, "fasteners", "method", default="heat-set inserts")
    if method != "heat-set inserts":
        raise ValueError("This demonstration uses insert holes; create a dedicated coupon for " + str(method))
    layer = float(g(mfg, "layer_height", "default", default=0.2))
    edges = g(style, "edges", default={})
    treat = g(edges, "edge_treatment", default={}) or {}
    t_type = treat.get("type", "chamfer")
    t_size = float(treat.get("size", 0.6))
    corner_r = float(g(edges, "outer_corner_radius", default=2.0))
    bottom = g(edges, "bottom_edge", default={}) or {}
    bottom_size = float(bottom.get("size", g(mfg, "edges", "bottom_chamfer", default=0.5)))
    bottom_type = bottom.get("type", "chamfer")

    grid = float(g(style, "proportions", "grid", default=5.0)) or 5.0
    plate_t = float(g(style, "proportions", "plate_thickness", default=2.0))
    layering = g(style, "proportions", "layering", default=[]) or []
    reveal = g(style, "proportions", "reveal", default={}) or {}
    reveal_w = float(reveal.get("width", 0) or 0)
    reveal_d = float(reveal.get("depth", 0) or 0)

    inset_units = float(g(style, "fasteners", "pattern", "inset_grid_units", default=2))
    inset = inset_units * grid
    insert = g(mfg, "inserts", "M3", default={"hole": 4.0, "depth": 5.7}) or {}
    ins_hole = float(insert.get("hole", 4.0))
    ins_depth = float(insert.get("depth", 5.7)) + 1.0
    mouth = float(g(mfg, "inserts", "mouth_chamfer", default=0.5))

    text_h = max(float(g(style, "typography", "min_height", default=5.0)),
                 float(g(mfg, "text", "min_height", default=5.0)))
    inlay = q(float(g(mfg, "text", "inlay_depth", default=0.4)), layer)
    case = g(style, "typography", "case", default="lowercase")
    label = "style tile" if case == "lowercase" else "STYLE TILE"

    grille = g(style, "grilles", "pattern", default={}) or {}
    g_type = grille.get("type", "round_holes")
    g_margin = float(g(style, "grilles", "edge_margin", default=2.0))

    knob = g(style, "controls", "knob_cap", default={}) or {}
    knob_d = float(knob.get("dia", 12.0))
    knob_h = float(knob.get("height", 9.0))
    knob_ch = float(knob.get("chamfer", 0.6) or 0)
    knob_fil = float(knob.get("fillet", 0) or 0)
    tight = float(g(mfg, "clearances", "tight", default=0.15))

    # tile height: the visible stack (plate + reveal + top edge treatment) must fit above a
    # plain 6 mm body zone, otherwise reveal and edge treatment collide (rugged styles)
    global TILE_H
    TILE_H = max(12.0, math.ceil(plate_t + reveal_w + max(t_size, 1.0) + bottom_size + 6.0))

    # ------------------------------------------------------------------ tile body
    with BuildPart() as body:
        with BuildSketch():
            RectangleRounded(TILE_W, TILE_D, corner_r)
        extrude(amount=TILE_H)
        top_edges = body.faces().sort_by(Axis.Z)[-1].edges()
        if t_type == "fillet":
            fillet(top_edges, radius=t_size)
        else:
            chamfer(top_edges, length=q(t_size, layer))
        bot_edges = body.faces().sort_by(Axis.Z)[0].edges()
        if bottom_type == "fillet":
            # a fillet tangent to the bed starts as a 90° overhang; the process wins here and
            # the style's bottom fillet becomes a 45° chamfer of the same size
            print(f"note: bottom_edge fillet {bottom_size} translated to a {q(bottom_size, layer)} chamfer (overhang rule)")
        chamfer(bot_edges, length=q(bottom_size, layer))

        # reveal groove around the body at plate_thickness below the top; its ceiling gets a
        # 45° chamfer so the groove prints without an overhang (design the support away)
        if len(layering) > 1 and reveal_w > 0 and reveal_d > 0:
            z0 = TILE_H - plate_t - reveal_w
            with BuildSketch(Plane.XY.offset(z0)):
                RectangleRounded(TILE_W, TILE_D, corner_r)
                RectangleRounded(TILE_W - 2 * reveal_d, TILE_D - 2 * reveal_d, corner_r, mode=Mode.SUBTRACT)
            extrude(amount=reveal_w, mode=Mode.SUBTRACT)
            ceiling = [f for f in body.faces() if f.geom_type == GeomType.PLANE
                       and abs(f.center().Z - (z0 + reveal_w)) < 1e-3 and f.normal_at().Z < -0.99]
            if ceiling:
                room = (TILE_H - (t_size if t_type != "fillet" else 0.0)) - (z0 + reveal_w) - 0.3
                for length in (min(0.8 * reveal_d, room), 0.5 * reveal_d):
                    try:
                        chamfer(ceiling[0].outer_wire().edges(), length=length)
                        break
                    except ValueError:
                        continue

        # insert holes, fastener pattern: four corners inset by the grid rule
        with Locations(*[(sx * (TILE_W / 2 - inset), sy * (TILE_D / 2 - inset), TILE_H) for sx in (-1, 1) for sy in (-1, 1)]):
            Cylinder(ins_hole / 2, ins_depth, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
            Cone(ins_hole / 2, ins_hole / 2 + mouth, mouth, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)

        # label pocket (top face, centred at y = +9)
        with BuildSketch(Plane.XY.offset(TILE_H)) as lab:
            with Locations((0, 9)):
                Text(label, font_size=text_h * 1.4, font=font or "Arial", font_style=FontStyle.BOLD)
        extrude(amount=-inlay, mode=Mode.SUBTRACT)
        label_faces = lab.sketch

        # grille field 20 x 14 centred at y = -9
        fx, fy, fcx, fcy = 20.0, 14.0, 0.0, -9.0
        if g_type == "round_holes":
            dia = float(grille.get("dia", 2.0))
            pitch = float(grille.get("pitch", 3.5))
            nx = int((fx - 2 * g_margin) // pitch) + 1
            ny = int((fy - 2 * g_margin) // pitch) + 1
            with Locations((fcx, fcy, TILE_H)):
                with GridLocations(pitch, pitch, nx, ny):
                    Cylinder(dia / 2, TILE_H + 2, mode=Mode.SUBTRACT)
        elif g_type == "slots":
            w = float(grille.get("w", 1.5))
            l = min(float(grille.get("l", 10.0)), fy - 2 * g_margin)
            pitch = float(grille.get("pitch", 3.0))
            n = int((fx - 2 * g_margin) // pitch) + 1
            with BuildSketch(Plane.XY.offset(TILE_H)):
                with Locations((fcx, fcy)):
                    with GridLocations(pitch, 1, n, 1):
                        RectangleRounded(w, l, w / 2 - 0.01)
            extrude(amount=-(TILE_H + 2), mode=Mode.SUBTRACT)

    # ------------------------------------------------------------------ label body (second colour)
    with BuildPart() as label_body:
        with BuildSketch(Plane.XY.offset(TILE_H - inlay)):
            with Locations((0, 9)):
                Text(label, font_size=text_h * 1.4, font=font or "Arial", font_style=FontStyle.BOLD)
        extrude(amount=inlay)

    # ------------------------------------------------------------------ knob cap + indicator
    with BuildPart() as cap:
        Cylinder(knob_d / 2, knob_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
        top = cap.faces().sort_by(Axis.Z)[-1].edges()
        if knob_fil > 0:
            fillet(top, radius=min(knob_fil, knob_d / 2 - 0.5))
        elif knob_ch > 0:
            chamfer(top, length=q(knob_ch, layer))
        chamfer(cap.faces().sort_by(Axis.Z)[0].edges(), length=q(bottom_size, layer))
        # D-shaft bore: Ø6 shaft with 4.5 flat; bore printed vertically → +compensation
        comp = float(g(mfg, "holes", "compensation_vertical", default=0.2))
        bore = 6.0 + comp + tight
        flat = 4.5 + tight                      # round wall to flat, D-shaft 6 x 4.5
        with BuildSketch(Plane.XY):
            Circle(bore / 2)
            with Locations((-bore / 2 + flat, 0)):
                Rectangle(bore, bore, align=(Align.MIN, Align.CENTER), mode=Mode.SUBTRACT)
        extrude(amount=knob_h - 2.0, mode=Mode.SUBTRACT)
        # indicator groove on top: 1 mm wide radial line, inlay deep, clear of the edge treatment
        x0, x1 = 1.0, knob_d / 2 - max(knob_ch, knob_fil) - 0.6
        with BuildSketch(Plane.XY.offset(knob_h)):
            with Locations(((x0 + x1) / 2, 0)):
                Rectangle(x1 - x0, 1.0)
        extrude(amount=-inlay, mode=Mode.SUBTRACT)
    with BuildPart() as indicator:
        with BuildSketch(Plane.XY.offset(knob_h - inlay)):
            with Locations(((x0 + x1) / 2, 0)):
                Rectangle(x1 - x0, 1.0)
        extrude(amount=inlay)

    # the cap sits beside the tile so combined STEP/renders read at a glance
    shift = (TILE_W / 2 + knob_d, 0, 0)
    return {
        "tile_body_base": body.part,
        "tile_label_accent": label_body.part,
        "cap_body_accent": cap.part.moved(Location(shift)),
        "cap_indicator_base": indicator.part.moved(Location(shift)),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--style", required=True)
    ap.add_argument("--mfg", required=True)
    ap.add_argument("--out", default="tile")
    ap.add_argument("--font", default=None, help="font family for the label (must exist on this machine)")
    args = ap.parse_args(argv)

    style, mfg = load(args.style), load(args.mfg)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    bodies = build(style, mfg, args.font)
    for name, part in bodies.items():
        export_stl(part, str(out / f"{name}.stl"), tolerance=0.02, angular_tolerance=0.1)
    export_step(Compound(children=list(bodies.values())), str(out / "style_tile.step"))
    sid = g(style, "meta", "id", default="style")
    print(f"style tile for '{sid}' written to {out}/ :", ", ".join(f"{n}.stl" for n in bodies), "+ style_tile.step")
    print("colour roles: *_base = body colour, *_accent = accent colour. Print tile bodies as one object.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
