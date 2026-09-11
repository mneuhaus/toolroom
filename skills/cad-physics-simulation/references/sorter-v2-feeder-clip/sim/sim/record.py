"""Record video from the scene's cameras while the physics runs.

Steps the simulation in real time with the rotors at their default speeds and
pipes each camera's frames into ffmpeg (H.264 mp4). One file per camera in
out/video/<camera>.mp4.

Usage: python -m sim.record [--seconds 20] [--fps 30] [--pieces 24] [--seed 0]
                            [--cameras overview,feeder,c_channel_2] [--size 1280x720]
Headless on Linux: MUJOCO_GL=egl (GPU) or osmesa (CPU).
"""
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import time
from pathlib import Path

import mujoco

from sim.assets import out_root
from sim.scene import build
from sim.snapshot import drive_rotors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--pieces", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cameras", default="overview,feeder,c_channel_2")
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--xml", default=None, help="use an existing scene instead of building one")
    args = ap.parse_args()
    w, h = (int(v) for v in args.size.split("x"))
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg not on PATH")

    out = out_root() / "video"
    out.mkdir(parents=True, exist_ok=True)
    xml = Path(args.xml) if args.xml else out_root() / "record.xml"
    if not args.xml:
        xml.write_text(build(args.pieces, False, args.seed))
    model = mujoco.MjModel.from_xml_path(str(xml))
    data = mujoco.MjData(model)
    drive_rotors(model, data)
    cams = [c.strip() for c in args.cameras.split(",") if c.strip()]
    for c in cams:
        if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, c) < 0:
            raise SystemExit(f"no camera {c}")

    renderer = mujoco.Renderer(model, height=h, width=w)
    procs = {}
    for c in cams:
        procs[c] = subprocess.Popen(
            [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{w}x{h}", "-r", str(args.fps), "-i", "-",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             str(out / f"{c}.mp4")],
            stdin=subprocess.PIPE)

    frames = int(args.seconds * args.fps)
    steps_per_frame = max(1, round(1.0 / args.fps / model.opt.timestep))
    t0 = time.time()
    for f in range(frames):
        for _ in range(steps_per_frame):
            mujoco.mj_step(model, data)
        for c in cams:
            renderer.update_scene(data, camera=c)
            procs[c].stdin.write(renderer.render().tobytes())
        if f % args.fps == 0:
            el = time.time() - t0
            print(f"{f / args.fps:5.1f}s of {args.seconds:.0f}s  ({el:.0f}s wall, {el / max(f, 1) * 1000:.0f} ms/frame)", flush=True)
    for c in cams:
        procs[c].stdin.close()
        procs[c].wait()
        print(f"{c}: {out / (c + '.mp4')} ({(out / (c + '.mp4')).stat().st_size / 1e6:.1f} MB)")
    renderer.close()
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
