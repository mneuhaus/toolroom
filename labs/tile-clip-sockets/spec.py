"""Nominal (scale 1) dimensions of the two clip-in-pocket tile joint systems.

Every number carries a source string. The only permitted fact sources are
`var/research/openlock/findings.md` sections 6 to 9 (OL6 .. OL9) and
`var/research/dragonlock/findings.md` sections 3 to 5 (DL3 .. DL5). Values
marked "proposed" are lab choices, not measured facts.

Frames. Pocket: x = depth into the tile from the contact face (x = 0 at the
face), y = along the edge (0 at the pocket centre), z = up from the tile
bottom. Clip: X = width, Y = length, Z = thickness, origin at the bar centre.
At the inserted pose the clip Y axis lies along the pocket x axis.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict, fields
import math

OL = "var/research/openlock/findings.md"
DL = "var/research/dragonlock/findings.md"


@dataclass(frozen=True)
class Process:
    """FDM process floors. Not scaled with the geometry. Clearances and the
    interference are totals across both flanks (pocket minus clip)."""
    nozzle: float = 0.4
    layer: float = 0.2
    perimeters: int = 2
    first_layer: float = 0.2
    clearance_xy: float = 0.15   # total, mouth/throat minus clip bar
    clearance_z: float = 0.2     # total, pocket height minus clip thickness
    interference_min: float = 0.4  # total across both sides = one line width
    roof_min_layers: int = 2
    rim_min_perimeters: int = 2
    support_bar: float = 0.5
    clip_thickness_min_layers: int = 4
    lead_in_chamfer: float = 0.4  # proposed, optional (--chamfer)
    sources: dict = field(default_factory=lambda: {
        "clearances": "proposed lab floors; no official clearance is published (OL9 'Design tolerance', DL5)",
        "interference_min": "proposed: one 0.4 mm line width across both flanks (OL9: 10.0 prongs / 10.4 barbs into a 12.8 chamber)",
        "layer": "OL9 PS-TPL/PS-CLIPS 0.2 mm recommended; DL5 FDG 0.15 to 0.2 mm",
        "support_bar": "OL7.1 built-in 1.0 mm support bars; DL4 ribs 0.4 to 0.6; 0.5 proposed",
    })

    @property
    def roof_min(self) -> float: return self.roof_min_layers * self.layer
    @property
    def floor_min(self) -> float: return self.first_layer + self.layer  # proposed: first layer + one layer
    @property
    def rim_min(self) -> float: return self.rim_min_perimeters * self.nozzle
    @property
    def clip_thickness_min(self) -> float: return self.clip_thickness_min_layers * self.layer


@dataclass(frozen=True)
class OpenLock:
    """OpenLOCK floor/wall pocket (OF-LOCK reconstruction, OL7) and v4.3/v5.4 clip (OL6)."""
    base_height: float = 6.0
    pocket_z0: float = 1.4
    pocket_z1: float = 5.6           # height 4.2
    mouth_w: float = 14.0
    mouth_d: float = 2.0
    taper_w0: float = 12.0           # at x = mouth_d
    taper_x1: float = 5.0            # 10.0 wide from here
    neck_w: float = 10.0
    neck_x1: float = 6.0
    chamber_w: float = 12.8
    chamber_x1: float = 10.7         # total pocket depth
    rim_w: float = 16.0
    rim_d: float = 2.0
    rim_z0: float = 0.4
    rim_h: float = 5.6
    support_w: float = 1.0
    support_y0: float = 2.05
    support_y1: float = 3.05
    support_z0: float = 1.2
    support_z1: float = 5.8
    support_x1: float = 2.0
    pitch: float = 12.7
    wall_t: float = 12.7
    wall_mouth_d: float = 1.0        # inside the wall face (OL7.2: x ±7.35 to ±5.35, 1 mm is the cut buffer)
    wall_taper_x1: float = 4.0       # taper ends at x ±2.35 about the wall centre
    wall_neck_len: float = 4.7
    side_t: float = 4.2              # side-lock pocket thickness (y ±2.1)
    side_mouth_h: float = 14.0
    side_mouth_d: float = 2.0
    side_taper_x1: float = 5.0
    side_neck_h: float = 10.0
    side_neck_x1: float = 5.9
    side_chamber_h: float = 10.52
    side_chamber_x1: float = 10.43
    side_rim_d: float = 11.43
    side_rim_t: float = 6.2
    side_rim_h: float = 16.0
    # clip (v4.3 outline, OL6); bar width default from the v5.4 bbox
    clip_bar_w: float = 13.2         # v5.4 (13.2 x 19.5 x 3.5); v4.3 option = 14.0
    clip_bar_w_v43: float = 14.0
    clip_len: float = 19.5
    clip_t: float = 3.6
    clip_t_v54: float = 3.5
    bar_len: float = 3.45
    prong_w: float = 10.0
    prong_y0: float = 1.775
    prong_y1: float = 5.675
    barb_w: float = 10.4
    barb_y0: float = 6.0
    barb_y1: float = 6.25
    taper_stations: tuple = ((9.98, 7.0), (9.6, 7.5), (8.6, 8.0), (7.6, 8.5), (6.6, 9.0))  # (width, |y|)
    tip_y: float = 9.75
    tip_w: float = 5.1               # proposed: 45 degree taper continued from 6.6 at y 9.0 to the tip
    eye_open: float = 0.53
    eye_open_y: float = 1.75
    eye_max: float = 3.64
    eye_max_y: float = 4.5
    eye_y9: float = 2.54
    eye_tip: float = 2.0
    sources: dict = field(default_factory=lambda: {
        "base_height": "OL7.1 '6 mm base' (derived roof 0.4, floor 1.4)",
        "pocket_z0/z1": "OL7.1 pocket height 4.2 from z 1.4 to 5.6 (OF-LOCK L7-15, CAIT, PVDC)",
        "mouth": "OL7.1 mouth 14.0 wide x 2.0 deep (L7, CAIT, PVDC)",
        "taper": "OL7.1 hull 12.0 wide at x 0-2 to 10.0 at x 3.01-5.01 -> taper 12 at x 2 to 10 at x 5",
        "neck": "OL7.1 10.0 wide from x 5 to 6 (MEAS chamber_raw)",
        "chamber": "OL7.1 12.8 wide, x 6.0-10.7, z -1 to 6.1 (through the full base)",
        "rim": "OL7.1 openlock_positive 2.0 deep x 16 wide x 5.6 high at z 0.4 (L38)",
        "supports": "OL7.1 two 1.0 mm bars at y +-(2.05-3.05), x -1.1..2.0, z 1.2-5.8 (L19-35); clamped to x >= 0 here",
        "pitch": "OL7.1 port centre every 12.7 mm; mouth spans y 5.7-19.7 on a 25.4 tile",
        "wall": "OL7.2 12.7 wall: mouth 14 wide x +-7.35 to +-5.35 (1 mm cut buffer), taper 12->10 to +-2.35, neck 4.7 long",
        "sidelock": "OL7.3 pocket 4.2 thick; mouth 14 tall x -1..2, taper to 10 tall at x 5, 10 tall to 5.9, chamber 10.52 tall x 5.9-10.43; rim 11.43 x 6.2 x 16",
        "clip_v43": "OL6 table column v4.3: 14.0 x 19.5 x 3.6, bar y +-1.725, prongs 10.0 from |y| 1.775 to 5.675, barb 10.40 at 6.0-6.25, taper stations, tip 6.6 at y 9.0 ends 9.75, eye slot 0.53 @1.75, 3.64 @4.5, 2.54 @9, 2.0 at tip",
        "clip_v54": "OL6 'Current official v5.4 standard clip: 13.2 x 19.5 x 3.5 (PS-MEAS-3)' [inferred]",
        "tip_w": "proposed: the 45 degree taper (OL6) continued 0.75 mm beyond y 9.0",
    })

    @property
    def pocket_h(self) -> float: return self.pocket_z1 - self.pocket_z0
    @property
    def roof(self) -> float: return self.base_height - self.pocket_z1
    @property
    def floor(self) -> float: return self.pocket_z0
    @property
    def rim_side(self) -> float: return (self.rim_w - self.mouth_w) / 2
    @property
    def half_len(self) -> float: return self.clip_len / 2

    def clip_outer_quadrant(self, bar_w: float | None = None) -> list[tuple[float, float]]:
        """Right/upper quadrant of the clip outline, (x = half width, y), from the
        bar centre line to the tip centre. Documented outline points."""
        bw = (bar_w if bar_w is not None else self.clip_bar_w) / 2
        pts = [(bw, 0.0), (bw, self.bar_len / 2), (self.prong_w / 2, self.bar_len / 2),
               (self.prong_w / 2, self.prong_y1), (self.barb_w / 2, self.barb_y0), (self.barb_w / 2, self.barb_y1)]
        pts += [(w / 2, y) for w, y in self.taper_stations]
        pts += [(self.tip_w / 2, self.tip_y), (0.0, self.tip_y)]
        return pts

    def clip_eye_half(self) -> list[tuple[float, float]]:
        """Eye slot (right half, y >= 0) polyline (x = half gap, y)."""
        return [(self.eye_open / 2, self.eye_open_y), (self.eye_max / 2, self.eye_max_y),
                (self.eye_y9 / 2, 9.0), (self.eye_tip / 2, self.tip_y)]


@dataclass(frozen=True)
class Dragonbite:
    """DRAGONLOCK / Dragonbite socket (DL4, 2017 tile and 2020 port block) and v3 combo-clip half (DL3)."""
    base_height: float = 6.35
    throat_w: float = 13.65
    throat_z0: float = 1.4
    throat_z1: float = 4.55          # findings quote '3.2 high (z 1.4-4.55)'; the z band (3.15) is used
    lip_d: float = 3.15
    cavity_w: float = 16.35
    cavity_x1: float = 11.7
    post_nose_x: float = 5.3
    head_d: float = 5.6
    head_cx: float = 8.1
    post_neck_w: float = 4.2
    pad_w: float = 7.82              # OF-SCAD pad 3.9095*2 under the post (open-bottom variant)
    pad_disc_d: float = 9.24
    floor_t: float = 1.4             # blind variant (2020 port block)
    rib_w: float = 0.5
    rib_y: tuple = (0.0, 3.6, -3.6)
    rim_w: float = 15.68             # OF positive 7.8418*2 wide, 2 thick, z 0.4-6.0
    rim_d: float = 2.0
    rim_z0: float = 0.4
    rim_h: float = 5.6
    pitch: float = 12.7
    # clip
    clip_t: float = 3.08
    bar_len: float = 3.6
    clip_bar_w: float = 13.4
    half_len: float = 10.73
    jaw_neck_w: float = 9.7
    jaw_neck_y0: float = 2.6
    jaw_neck_y1: float = 3.0
    jaw_max_w: float = 12.5
    jaw_max_y0: float = 8.6
    jaw_max_y1: float = 9.45
    jaw_tip_w: float = 10.9
    gap_root: float = 1.2
    gap_cup: float = 5.9
    gap_cup_y: float = 7.95
    gap_bite: float = 4.6
    gap_bite_y: float = 9.85
    gap_tip: float = 5.3
    sources: dict = field(default_factory=lambda: {
        "base_height": "DL4 tile 6.35 (DLU_2x2_Master), base 6.35 (WallBase_1)",
        "throat": "DL4 throat 13.65 wide, z 1.4-4.55 (quoted 3.2 high), lip depth 3.15",
        "cavity": "DL4 Dragonbite_Port (2020): 16.35 wide, back wall at 11.7, ceiling z 4.55",
        "post": "DL4 nose at 5.3, head dia ~5.6 centred at ~8.1, neck 4.2 (WallBase 4.2, port 4.25, OF 4.24), full cavity height",
        "floor": "DL4 2017 tile: pad only under the post, open underside outside it; 2020 port: closed 1.4 floor",
        "pad": "DL4 OF-SCAD pad 7.82 wide (3.9095*2) up to z 1.3695, dia 9.24 disc round the post; pad x extent proposed (lip to back wall)",
        "ribs": "DL4 bridging ribs in the throat at y 0 and +-3.6 (0.4 to 0.6 wide; 0.5 used)",
        "rim": "DL4 OF positive cube([2, 7.8418*2, 5.6]) at z 0.4",
        "clip": "DL3 combo clip DL half: thickness 3.08, bar 3.6 long x 13.4 wide, half length 10.73, root 9.7 at y 2.6-3.0, max 12.5 at 8.6-9.45, tip 10.9, gap root 1.1-1.2, cup 5.9 at 7.95, bite 4.6 at 9.85, lead-in 5.3, wall 3.3-3.8",
        "clip_outline": "proposed polyline through the DL3 stations; cup follows a circle r 2.95 centred at y 7.95",
    })

    @property
    def throat_h(self) -> float: return self.throat_z1 - self.throat_z0
    @property
    def roof(self) -> float: return self.base_height - self.throat_z1
    @property
    def rim_side(self) -> float: return (self.rim_w - self.throat_w) / 2
    @property
    def clip_len(self) -> float: return 2 * self.half_len

    def clip_outer_quadrant(self, bar_w: float | None = None) -> list[tuple[float, float]]:
        """(x = half width, y) from the bar centre to the tip. Widths at the stations:
        bar 13.4, neck 9.7 (y 2.6-3.0), 12.4 at the cup (y 7.95), 12.5 max (y 8.6-9.45),
        12.0 at the bite (9.85), 10.9 at the tip (10.73)."""
        bw = (bar_w if bar_w is not None else self.clip_bar_w) / 2
        return [(bw, 0.0), (bw, self.bar_len / 2), (self.jaw_neck_w / 2, self.jaw_neck_y0),
                (self.jaw_neck_w / 2, self.jaw_neck_y1), (6.2, self.gap_cup_y),
                (self.jaw_max_w / 2, self.jaw_max_y0), (self.jaw_max_w / 2, self.jaw_max_y1),
                (6.0, self.gap_bite_y), (self.jaw_tip_w / 2, self.half_len), (0.0, self.half_len)]

    def clip_gap_half(self, bite: float | None = None) -> list[tuple[float, float]]:
        """Inner jaw face (x = half gap, y): root 1.2, circle r 2.95 about y 7.95 (cup 5.9),
        bite 4.6 at 9.85 (the circle continued gives 4.51), lead-in 5.3 at the tip."""
        r = self.gap_cup / 2
        cy = self.gap_cup_y
        bite = self.gap_bite if bite is None else bite
        pts = [(0.55, self.bar_len / 2), (self.gap_root / 2, self.jaw_neck_y1), (1.2, 4.5)]
        for y in (6.0, 6.5, 7.0, 7.5, cy, 8.5, 9.0, 9.4):
            pts.append((math.sqrt(r * r - (y - cy) ** 2), y))
        pts += [(bite / 2, self.gap_bite_y), (self.gap_tip / 2, self.half_len)]
        return pts


@dataclass(frozen=True)
class Merged:
    """Toolroom 'merged' socket and hybrid clip: a Toolroom design (this lab's own
    brief), not a reconstruction from OL/DL findings. It reuses the OpenLOCK pocket
    mouth/taper/neck/chamber envelope and clip outline verbatim (see `OpenLock`
    above; `merged.py.dims()` copies those fields straight from `OpenLock`
    rather than re-typing them here, so there is nothing to fall out of sync)
    and adds a full-height post that
    carries a thin top plate over the open chamber, plus a clip whose eye slot is
    reshaped into compliant jaws around that post. All numbers here are lab design
    choices scoped to this task, at scale 1 only (not run through `spec.scaled`)."""
    tile: float = 25.4
    pitch: float = 12.7
    base_height: float = 6.0
    top_plate: float = 1.2
    post_dia: float = 2.0
    post_x: float = 8.0                # from the contact face, same station as the clip's jaw cup (y = post_x when seated)
    lead_in_chamfer: float = 0.4
    cube_edge: float = 50.8            # six-face pocket cube (2 x tile pitch), keeps side chambers clear of each other/the centre
    # hybrid clip jaw slot control points (right half, half-width at y); straight
    # segments between stations, same polyline convention as OpenLock.clip_eye_half
    # / Dragonbite.clip_gap_half above.
    jaw_root_w: float = 0.53
    jaw_root_y: float = 1.75
    jaw_compliance_w: float = 3.0
    jaw_compliance_y: float = 4.5
    jaw_bite_y: float = 7.0
    jaw_cup_dia: float = 2.2           # post_dia + 0.2 running clearance
    jaw_cup_y: float = 8.0
    jaw_tip_w: float = 2.6
    jaw_tip_y: float = 9.75
    thicknesses: tuple = (3.5, 3.7, 3.9)
    grip_standard: tuple = (0.20, 0.10)   # (barb interference i, bite interference b) per side
    grip_tight: tuple = (0.30, 0.15)
    label_engrave_depth: float = 0.4
    label_letter_height: float = 2.0
    label_cube_letter_height: float = 5.0
    sources: dict = field(default_factory=lambda: {
        "pocket_envelope": "reuses OpenLock mouth/taper/neck/chamber/rim/pitch verbatim (OL7.1); not an independent fact",
        "clip_outline": "reuses OpenLock.clip_outer_quadrant verbatim (OL6, v5.4 bar); not an independent fact",
        "top_plate/post": "Toolroom design (task brief): 1.2 mm plain roof over an open chamber, carried on a central Ø2.0 post",
        "jaws": "Toolroom design (task brief): DragonLock-style compliant slot (DL3 'jaws' vocabulary) inside the OpenLOCK outline, sized around the post",
        "matrix": "task brief: t in {3.5,3.7,3.9} x grip {standard i0.20/b0.10, tight i0.30/b0.15}",
    })

    @property
    def total_height(self) -> float: return self.base_height + self.top_plate


def as_dict(obj) -> dict:
    d = asdict(obj)
    d.pop("sources", None)
    return d


def scaled(obj, s: float) -> dict:
    """All length dimensions x s. Tuples of stations are scaled element-wise;
    counts and sources are left alone."""
    out = {}
    for f in fields(obj):
        v = getattr(obj, f.name)
        if f.name == "sources" or isinstance(v, (int, bool)) and not isinstance(v, float):
            out[f.name] = v
        elif isinstance(v, float):
            out[f.name] = v * s
        elif isinstance(v, tuple):
            out[f.name] = tuple(tuple(x * s for x in e) if isinstance(e, tuple) else e * s for e in v)
        else:
            out[f.name] = v
    return out
