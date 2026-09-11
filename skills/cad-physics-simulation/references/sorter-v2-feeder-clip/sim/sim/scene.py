"""manifest.json -> MJCF scene for MuJoCo.

  world           every static part as a visual mesh geom (group 1, no contact)
  rotor_c1..c4    one hinge about world Z through each rotor's origin, C1 the
                  highest station; the body carries the rotor, its cap and its
                  output gear. The joint is armature-heavy and velocity-driven,
                  so a piece can be carried by the rim but cannot slow it.
  collision       convex pieces from assets/machine/collision/<mesh>/ when
                  present (group 3, invisible), on the body the part belongs to.
                  Machine geoms collide with pieces only (contype 2 / conaffinity
                  1 against the pieces' 1 / 1), never with each other.
  cameras         one per "dummy camera" part, at its centre, looking straight
                  down, named for the channel under it: c_channel_2,
                  c_channel_3, classification_channel; plus "overview", "front",
                  "top" and a "feeder" close-up
  lights          one spot per lamp reflector
  pieces          --pieces N pieces, parked above the C2 rotor (--feed c2) or poured
                  into the bulk section over C1 (--feed bulk): parts sampled from
                  assets/pieces/library.json (sim.pieces) when it exists, else
                  test boxes. Each piece's part and LDraw colour is a <custom>
                  text named after its body, for whatever replays the scene.

Usage: python -m sim.scene [--out out/sorter.xml] [--pieces 0] [--feed c2|bulk] [--seed 0] [--feeder-only]
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np
from scipy.spatial.transform import Rotation

from sim.assets import asset_root, out_root
from sim.materials import MATERIALS

ROTOR = "Rotor - Faceted"
ROTOR_PARTS = (ROTOR, "rotor cap", "Output gear (130 teeth)")
CAMERA = "dummy camera"
LAMP = "lamp inner reflector"
CAMERA_ROLES = {2: "c_channel_2", 3: "c_channel_3", 4: "classification_channel"}
# Vertical field of view for a 16:9 frame from a 78 degree diagonal webcam.
# Placeholder until the real camera is measured; see AGENTS.md.
CAMERA_FOVY_DEG = 43.3
# Output-side rotor speeds the control software runs by default, deg/s.
ROTOR_DEG_PER_S = {1: 2.0, 2: 6.0, 3: 10.0, 4: 10.0}
# The rotors turn clockwise seen from above (negative about +Z). Pieces land on a channel
# on the side facing the one above and ride most of the way round to the stator's opening,
# which sits just ahead of the output guide.
SPIN = -1.0
# Highest point of a rotor (the top of the faceted cone) above the rotor's origin, metres.
ROTOR_TOP = 0.0485


def xform(o: dict) -> np.ndarray:
    return np.array(o["xform"], dtype=float).reshape(4, 4)


def quat_wxyz(R: np.ndarray) -> str:
    q = Rotation.from_matrix(R).as_quat()  # x y z w
    return f"{q[3]:.9g} {q[0]:.9g} {q[1]:.9g} {q[2]:.9g}"


def vec(v) -> str:
    return " ".join(f"{float(x):.6g}" for x in v)


def world_centre(o: dict, meshes: dict) -> np.ndarray:
    T = xform(o)
    b = np.array(meshes[o["mesh"]]["bounds"])
    return (T @ np.append(b.mean(0), 1.0))[:3]


def look_at(pos, target, up=(0, 0, 1)) -> str:
    """MuJoCo camera xyaxes: x right, y up, camera looks along -z."""
    f = np.array(target, float) - np.array(pos, float)
    f /= np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return vec(r) + " " + vec(u)


def geom_xml(o: dict, meshes: dict, body_origin: np.ndarray | None, cls: str) -> str:
    T = xform(o)
    if not np.allclose(np.linalg.norm(T[:3, :3], axis=0), 1.0, atol=1e-4):
        raise ValueError(f"{o['name']}: transform carries scale; the export must be unit scale")
    pos = T[:3, 3] - (body_origin if body_origin is not None else 0)
    key = o["material"]
    if key:
        look = f'material="{key}"'
    else:
        cols = meshes[o["mesh"]]["gltf_colors"]
        rgba = cols[0] if cols else [0.5, 0.5, 0.5, 1]
        look = f'rgba="{vec(rgba)}"'
    return (f'<geom class="{cls}" mesh="m_{o["mesh"]}" pos="{vec(pos)}" quat="{quat_wxyz(T[:3, :3])}" '
            f'{look} name={quoteattr(o["name"] + " " + str(o["instance"]))}/>')


def collision_xml(o: dict, machine: Path, body_origin: np.ndarray | None) -> list[str]:
    d = machine / "collision" / o["mesh"]
    if not d.is_dir():
        return []
    T = xform(o)
    pos = T[:3, 3] - (body_origin if body_origin is not None else 0)
    q = quat_wxyz(T[:3, :3])
    return [f'<geom class="col" mesh="c_{o["mesh"]}_{f.stem}" pos="{vec(pos)}" quat="{q}"/>'
            for f in sorted(d.glob("*.stl"))]


# Colours for random pieces, LDraw code -> LDConfig sRGB: red, blue, yellow, white, black,
# green, light bluish grey, dark bluish grey, orange, tan.
LEGO_COLOURS = {4: (0.788, 0.102, 0.035, 1), 1: (0.0, 0.333, 0.749, 1), 14: (0.949, 0.804, 0.216, 1),
                15: (1.0, 1.0, 1.0, 1), 0: (0.02, 0.075, 0.114, 1), 2: (0.137, 0.471, 0.255, 1),
                71: (0.627, 0.647, 0.663, 1), 72: (0.424, 0.431, 0.408, 1), 25: (0.996, 0.541, 0.094, 1),
                19: (0.894, 0.804, 0.62, 1)}


def load_library() -> dict:
    f = asset_root() / "pieces" / "library.json"
    return json.loads(f.read_text()) if f.exists() else {}


def spawn_points(stations: dict, n: int, feed: str, rng: random.Random) -> list[tuple]:
    """Where the pieces start. c2: parked in a ring just above the C2 rotor. bulk: poured
    into the bulk section over C1, on a jittered grid in layers, 40 mm apart so no two
    start overlapping (overlapping bodies fly apart on the first step)."""
    if feed == "c2":
        p = stations[2]
        return [(p[0] + 0.078 * math.cos(2 * math.pi * i / n), p[1] + 0.078 * math.sin(2 * math.pi * i / n),
                 p[2] + ROTOR_TOP + 0.02 + 0.015 * (i % 4)) for i in range(n)]
    p = stations[1]
    grid = [(x, y) for x in np.arange(-0.10, 0.101, 0.04) for y in np.arange(-0.10, 0.101, 0.04)
            if math.hypot(x, y) <= 0.095]
    pts: list[tuple] = []
    layer = 0
    while len(pts) < n:
        for x, y in rng.sample(grid, len(grid))[:n - len(pts)]:
            pts.append((p[0] + x + rng.uniform(-0.006, 0.006), p[1] + y + rng.uniform(-0.006, 0.006),
                        p[2] + ROTOR_TOP + 0.03 + 0.035 * layer))
        layer += 1
    return pts


def build(pieces: int, feeder_only: bool, seed: int = 0, feed: str = "c2") -> str:
    machine = asset_root() / "machine"
    man = json.loads((machine / "manifest.json").read_text())
    meshes = man["meshes"]
    occ = man["occurrences"]
    if feeder_only:
        occ = [o for o in occ if any("feeder" in p.lower() for p in o["path"])]

    # Rotor stations: highest first is C1 (the bulk section).
    rotors = sorted([o for o in occ if o["name"] == ROTOR], key=lambda o: -xform(o)[2, 3])
    stations = {i + 1: xform(o)[:3, 3] for i, o in enumerate(rotors)}

    def station_of(p: np.ndarray) -> int:
        return min(stations, key=lambda k: np.linalg.norm(stations[k][:2] - p[:2]))

    used_meshes = {o["mesh"] for o in occ}
    assets = [f'<mesh name="m_{m}" file="machine/{meshes[m]["file"]}" maxhullvert="64"/>' for m in sorted(used_meshes)]
    for m in sorted(used_meshes):
        d = machine / "collision" / m
        if d.is_dir():
            assets += [f'<mesh name="c_{m}_{f.stem}" file="machine/collision/{m}/{f.name}"/>' for f in sorted(d.glob("*.stl"))]
    for key, spec in MATERIALS.items():
        extra = " ".join(f'{k}="{v}"' for k, v in spec.items() if k != "rgba")
        assets.append(f'<material name="{key}" rgba="{vec(spec["rgba"])}" {extra}/>')

    world: list[str] = []
    bodies: dict[int, list[str]] = {k: [] for k in stations}
    cameras: list[str] = []
    lights: list[str] = []
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for o in occ:
        c = world_centre(o, meshes)
        lo = np.minimum(lo, c)
        hi = np.maximum(hi, c)
        if o["name"] in ROTOR_PARTS:
            k = station_of(xform(o)[:3, 3])
            bodies[k].append(geom_xml(o, meshes, stations[k], "vis"))
            bodies[k] += collision_xml(o, machine, stations[k])
            continue
        world.append(geom_xml(o, meshes, None, "vis"))
        world += collision_xml(o, machine, None)
        if o["name"] == CAMERA:
            k = station_of(c)
            role = CAMERA_ROLES.get(k, f"camera_c{k}")
            cameras.append(f'<camera name="{role}" pos="{vec(c)}" fovy="{CAMERA_FOVY_DEG}"/>')
        elif o["name"] == LAMP:
            lights.append(f'<light pos="{vec(c)}" dir="0 0 -1" cutoff="70" exponent="2" '
                          f'diffuse="0.45 0.43 0.40" specular="0.1 0.1 0.1" attenuation="1 0 2"/>')

    centre = (lo + hi) / 2
    span = float(np.max(hi - lo))
    feeder = np.mean(list(stations.values()), axis=0)
    fpos = feeder + np.array([-0.58, 0.58, 0.40])
    cameras.append(f'<camera name="feeder" pos="{vec(fpos)}" xyaxes="{look_at(fpos, feeder + np.array([0, 0, 0.05]))}" fovy="38"/>')
    for name, off in (("overview", (1.4, -1.4, 0.7)), ("front", (0, -2.0, 0.25)), ("top", (0.0, -0.001, 1.6))):
        pos = centre + np.array(off) * max(span, 1.0)
        cameras.append(f'<camera name="{name}" pos="{vec(pos)}" xyaxes="{look_at(pos, centre + np.array([0, 0, 0.1]))}" fovy="40"/>')

    rotor_xml = []
    for k, p in stations.items():
        rotor_xml.append(
            f'<body name="rotor_c{k}" pos="{vec(p)}">\n'
            f'  <joint name="rotor_c{k}" type="hinge" axis="0 0 1" armature="20" damping="2"/>\n'
            + "\n".join("  " + g for g in bodies[k]) + "\n</body>")
    actuators = [f'<velocity name="rotor_c{k}" joint="rotor_c{k}" kv="500"/>' for k in stations]

    piece_xml = []
    texts = []
    if pieces:
        library = load_library()
        rng = random.Random(seed)
        parts = sorted(library) if library else []
        declared: set[str] = set()
        for i, pos in enumerate(spawn_points(stations, pieces, feed, rng)):
            colour = rng.choice(sorted(LEGO_COLOURS))
            rgba = LEGO_COLOURS[colour]
            yaw = rng.uniform(0, 360)
            if parts:
                part = parts[rng.randrange(len(parts))]
                spec = library[part]
                hulls = sorted((asset_root() / "pieces" / part / "col").glob("*.stl"))
                if part not in declared:
                    declared.add(part)
                    assets.append(f'<mesh name="p_{part}" file="pieces/{part}/visual.stl"/>')
                    assets += [f'<mesh name="p_{part}_{h.stem}" file="pieces/{part}/col/{h.name}"/>' for h in hulls]
                geoms = [f'  <inertial pos="{vec(spec["com"])}" mass="{spec["mass_kg"]:.6g}" fullinertia="{vec(spec["fullinertia"])}"/>',
                         f'  <geom class="piece_vis" mesh="p_{part}" rgba="{vec(rgba)}"/>'] + [
                    f'  <geom class="piece" type="mesh" mesh="p_{part}_{h.stem}"/>' for h in hulls]
                label = f'{part} {spec["name"]}'
            else:
                geoms = [f'  <geom class="piece" type="box" size="0.016 0.008 0.0048" mass="0.0025" rgba="{vec(rgba)}"/>']
                label = "box"
            piece_xml.append(
                f'<body name="piece_{i}" pos="{vec(pos)}" euler="0 0 {yaw:.1f}">\n  <freejoint/>\n'
                + "\n".join(geoms) + f'\n</body><!-- {label} -->')
            texts.append(f'<text name="piece_{i}" data="{part if parts else "box"} {colour}"/>')

    nl = "\n"
    custom = f"<custom>{nl}    " + f"{nl}    ".join(texts) + f"{nl}  </custom>" if texts else ""
    return f'''<mujoco model="sorter-v2">
  <compiler meshdir="{asset_root()}" autolimits="true"/>
  <option timestep="0.001" cone="elliptic" impratio="10" gravity="0 0 -9.81"/>
  <visual>
    <global offwidth="1280" offheight="720"/>
    <headlight ambient="0.3 0.3 0.3" diffuse="0.35 0.35 0.35" specular="0.1 0.1 0.1"/>
    <quality shadowsize="4096"/>
    <map znear="0.005" zfar="20"/>
  </visual>
  <default>
    <default class="vis"><geom type="mesh" contype="0" conaffinity="0" group="1"/></default>
    <!-- Contact masks: machine parts (col) collide with pieces only, never with each other. -->
    <default class="col"><geom type="mesh" contype="2" conaffinity="1" group="3" rgba="1 0.3 0.3 0.35"
        friction="0.5 0.005 0.0001" solref="0.005 1" solimp="0.9 0.95 0.001"/></default>
    <default class="piece"><geom contype="1" conaffinity="1" condim="4" group="3" rgba="0.3 1 0.3 0.35" mass="0"
        friction="0.5 0.005 0.0001" solref="0.005 1" solimp="0.9 0.95 0.001"/></default>
    <default class="piece_vis"><geom type="mesh" contype="0" conaffinity="0" group="2" mass="0"/></default>
  </default>
  <asset>
    {nl.join(assets)}
  </asset>
  <worldbody>
    <light directional="true" pos="0 0 3" dir="0.2 0.3 -1" diffuse="0.45 0.45 0.45"/>
    {nl.join(lights)}
    {nl.join(cameras)}
    <geom type="plane" size="3 3 0.1" pos="0 0 {lo[2] - 0.2:.4f}" rgba="0.9 0.9 0.9 1" contype="2" conaffinity="1"/>
    {nl.join(world)}
    {nl.join(rotor_xml)}
    {nl.join(piece_xml)}
  </worldbody>
  <actuator>
    {nl.join(actuators)}
  </actuator>
  {custom}
</mujoco>
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--pieces", type=int, default=0)
    ap.add_argument("--feeder-only", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--feed", choices=("c2", "bulk"), default="c2")
    args = ap.parse_args()
    out = Path(args.out) if args.out else out_root() / "sorter.xml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(args.pieces, args.feeder_only, args.seed, args.feed))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
