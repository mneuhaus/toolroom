"""Record a feeder clip for the offline renderer, and preview it cheaply.

  python -m sim.clip run [--pieces 40] [--seconds 40] [--speeds 10,20,30,30] [--seed 0]
  python -m sim.clip views --target X,Y,Z [--dist D] [--azs A,A,..] [--els E,E,..] [--at S]
  python -m sim.clip preview --target X,Y,Z --dist D --az A --el E [--start S] [--end S]

run pours pieces into the bulk section over C1 and turns the rotors at the given output
speeds (deg/s, C1..C4, clockwise seen from above). Nothing about the pieces' path is
scripted: it is whatever the contact physics does. Every rotor angle and piece pose is
logged at 30 fps to out/clip/traj.npz, with out/clip/meta.json (station origins, each
piece's LDraw part and colour) for the offline renderer.

A camera is a target point, a distance, the azimuth it looks along (0 = looking along +X,
counter-clockwise from above) and its elevation above the horizontal. views renders one
moment from every azimuth/elevation pair into a contact sheet, to match a reference
angle; preview renders the log from one camera to out/clip/preview.mp4 and writes
out/clip/camera.json for the offline renderer. Both use MuJoCo's own renderer, which needs
an OpenGL context: MUJOCO_GL=egl on a headless Linux box.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import time
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw

from sim import scene
from sim.assets import out_root

FPS = 30


def clip_dir() -> Path:
    d = out_root() / "clip"
    d.mkdir(parents=True, exist_ok=True)
    return d


def vec3(s: str) -> np.ndarray:
    return np.array([float(v) for v in s.split(",")])


def where(adr: list[int], qpos: np.ndarray, stations: dict) -> str:
    """How many pieces sit in each station, and how many have left the feeder."""
    counts = dict.fromkeys(stations, 0)
    off = 0
    for a in adr:
        p = qpos[a:a + 3]
        k = min(stations, key=lambda s: math.dist(p[:2], stations[s][:2]))
        s = stations[k]
        if math.dist(p[:2], s[:2]) < 0.15 and s[2] - 0.03 < p[2] < s[2] + 0.3:
            counts[k] += 1
        else:
            off += 1
    return " ".join(f"C{k} {c:2d}" for k, c in counts.items()) + f"  off {off:2d}"


def run(args) -> None:
    d = clip_dir()
    xml = d / "scene.xml"
    xml.write_text(scene.build(args.pieces, feeder_only=True, seed=args.seed, feed="bulk"))
    model = mujoco.MjModel.from_xml_path(str(xml))
    data = mujoco.MjData(model)
    speeds = [float(s) for s in args.speeds.split(",")]
    stations, rotor_adr = {}, []
    for k, dps in enumerate(speeds, 1):
        data.ctrl[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"rotor_c{k}")] = scene.SPIN * math.radians(dps)
        rotor_adr.append(int(model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"rotor_c{k}")]))
        stations[k] = model.body_pos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, f"rotor_c{k}")].tolist()
    labels = dict(re.findall(r'<text name="(piece_\d+)" data="([^"]*)"', xml.read_text()))
    names = [n for n in (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, b) for b in range(model.nbody))
             if n and n.startswith("piece_")]
    adr = [int(model.jnt_qposadr[model.body_jntadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n)]])
           for n in names]

    n = int(args.seconds * FPS) + 1
    qpos = np.zeros((n, model.nq), np.float32)
    t0 = time.time()
    for f in range(n):
        while data.time < f / FPS - 1e-9:
            mujoco.mj_step(model, data)
        if not np.isfinite(data.qpos).all():
            print(f"unstable at t={data.time:.3f}s, stopping with {f} frames")
            n = f
            break
        qpos[f] = data.qpos
        if f % (5 * FPS) == 0:
            print(f"t={data.time:5.1f}s  {where(adr, data.qpos, stations)}  "
                  f"{data.time / max(time.time() - t0, 1e-6):.2f}x realtime", flush=True)
    qpos = qpos[:n]
    np.savez_compressed(d / "traj.npz", qpos=qpos, rotor=qpos[:, rotor_adr],
                        pos=np.stack([qpos[:, a:a + 3] for a in adr], 1),
                        quat=np.stack([qpos[:, a + 3:a + 7] for a in adr], 1))  # w x y z
    pieces = []
    for nm in names:
        part, colour = labels[nm].split()
        pieces.append({"body": nm, "part": part, "colour": int(colour)})
    meta = {"fps": FPS, "frames": n, "speeds_deg_s": speeds, "spin": scene.SPIN, "seed": args.seed,
            "stations": stations, "pieces": pieces}
    (d / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {d / 'traj.npz'}: {n} frames, {len(names)} pieces, {time.time() - t0:.0f}s wall")


def camera(target: np.ndarray, dist: float, az: float, el: float) -> np.ndarray:
    a, e = math.radians(az), math.radians(el)
    return target - dist * np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), -math.sin(e)])


def load_with_cameras(cams: dict, fovy: float, w: int, h: int) -> mujoco.MjModel:
    """The recorded scene with extra fixed cameras, name -> (position, target)."""
    xml = (clip_dir() / "scene.xml").read_text()
    extra = "".join(f'\n    <camera name="{k}" pos="{scene.vec(p)}" xyaxes="{scene.look_at(p, t)}" fovy="{fovy}"/>'
                    for k, (p, t) in cams.items())
    model = mujoco.MjModel.from_xml_string(xml.replace("<worldbody>", "<worldbody>" + extra, 1))
    model.vis.global_.offwidth = max(model.vis.global_.offwidth, w)
    model.vis.global_.offheight = max(model.vis.global_.offheight, h)
    return model


def views(args) -> None:
    target = vec3(args.target)
    pairs = [(float(a), float(e)) for e in args.els.split(",") for a in args.azs.split(",")]
    cams = {f"v{i}": (camera(target, args.dist, a, e), target) for i, (a, e) in enumerate(pairs)}
    w, h = 480, 346
    model = load_with_cameras(cams, args.fovy, w, h)
    data = mujoco.MjData(model)
    data.qpos[:] = np.load(clip_dir() / "traj.npz")["qpos"][int(args.at * FPS)]
    mujoco.mj_forward(model, data)
    r = mujoco.Renderer(model, h, w)
    cols = len(args.azs.split(","))
    sheet = Image.new("RGB", (w * cols, h * math.ceil(len(pairs) / cols)), "white")
    for i, (a, e) in enumerate(pairs):
        r.update_scene(data, camera=f"v{i}")
        tile = Image.fromarray(r.render())
        ImageDraw.Draw(tile).text((8, 8), f"az {a:g}  el {e:g}", fill=(255, 0, 0))
        sheet.paste(tile, ((i % cols) * w, (i // cols) * h))
    r.close()
    sheet.save(clip_dir() / "views.png")
    print(f"wrote {clip_dir() / 'views.png'}")


def preview(args) -> None:
    d = clip_dir()
    target = vec3(args.target)
    pos = camera(target, args.dist, args.az, args.el)
    w, h = (int(v) for v in args.size.split("x"))
    model = load_with_cameras({"clip": (pos, target)}, args.fovy, w, h)
    data = mujoco.MjData(model)
    qpos = np.load(d / "traj.npz")["qpos"]
    lo, hi = int(args.start * FPS), int(args.end * FPS) if args.end else len(qpos) - 1
    frames = d / "preview"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir()
    r = mujoco.Renderer(model, h, w)
    for i, f in enumerate(range(lo, hi + 1)):
        data.qpos[:] = qpos[f]
        mujoco.mj_forward(model, data)
        r.update_scene(data, camera="clip")
        Image.fromarray(r.render()).save(frames / f"{i:05d}.png")
    r.close()
    (d / "camera.json").write_text(json.dumps({"pos": pos.tolist(), "target": target.tolist(), "fovy": args.fovy,
                                               "start_frame": lo, "end_frame": hi}, indent=1))
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(frames / "%05d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", str(d / "preview.mp4")], check=True)
    print(f"wrote {hi - lo + 1} frames to {frames}, {d / 'preview.mp4'}, {d / 'camera.json'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--pieces", type=int, default=40)
    p.add_argument("--seconds", type=float, default=40.0)
    p.add_argument("--speeds", default="10,20,30,30", help="output deg/s for C1..C4")
    p.add_argument("--seed", type=int, default=0)
    for name in ("views", "preview"):
        p = sub.add_parser(name)
        p.add_argument("--target", required=True)
        p.add_argument("--dist", type=float, default=0.65)
        p.add_argument("--fovy", type=float, default=30.0)
    sub.choices["views"].add_argument("--azs", default="-30,-15,0,15")
    sub.choices["views"].add_argument("--els", default="30,40")
    sub.choices["views"].add_argument("--at", type=float, default=0.0, help="seconds into the log")
    p = sub.choices["preview"]
    p.add_argument("--az", type=float, required=True)
    p.add_argument("--el", type=float, required=True)
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--end", type=float, default=0.0)
    p.add_argument("--size", default="960x692")
    args = ap.parse_args()
    {"run": run, "views": views, "preview": preview}[args.cmd](args)


if __name__ == "__main__":
    main()
