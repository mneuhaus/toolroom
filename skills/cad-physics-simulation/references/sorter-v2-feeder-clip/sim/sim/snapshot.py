"""Render the scene's cameras to PNG, headless.

Steps the physics for --seconds first with the rotors turning at their default
speeds, so test pieces settle and ride. Writes out/snap/<camera>.png.

Usage: python -m sim.snapshot [--xml out/sorter.xml] [--seconds 0] [--cameras c_channel_2,overview]
"""
from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

from sim.assets import out_root
from sim.scene import ROTOR_DEG_PER_S, SPIN


def drive_rotors(model: mujoco.MjModel, data: mujoco.MjData) -> None:
    for k, dps in ROTOR_DEG_PER_S.items():
        i = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"rotor_c{k}")
        if i >= 0:
            data.ctrl[i] = SPIN * math.radians(dps)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", default=None)
    ap.add_argument("--seconds", type=float, default=0.0)
    ap.add_argument("--cameras", default="c_channel_2,c_channel_3,classification_channel,overview,front,top")
    ap.add_argument("--size", default="1280x720")
    args = ap.parse_args()
    xml = Path(args.xml) if args.xml else out_root() / "sorter.xml"
    w, h = (int(v) for v in args.size.split("x"))

    t0 = time.time()
    model = mujoco.MjModel.from_xml_path(str(xml))
    data = mujoco.MjData(model)
    print(f"loaded {xml.name}: {model.ngeom} geoms, {model.nmesh} meshes, {model.nbody} bodies, "
          f"{model.ncam} cameras in {time.time() - t0:.1f}s")

    drive_rotors(model, data)
    t0 = time.time()
    steps = int(args.seconds / model.opt.timestep)
    for _ in range(steps):
        mujoco.mj_step(model, data)
    if steps:
        print(f"stepped {args.seconds}s of physics in {time.time() - t0:.1f}s")
    mujoco.mj_forward(model, data)

    out = out_root() / "snap"
    out.mkdir(parents=True, exist_ok=True)
    renderer = mujoco.Renderer(model, height=h, width=w)
    for cam in args.cameras.split(","):
        cam = cam.strip()
        if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, cam) < 0:
            print(f"no camera {cam}")
            continue
        t0 = time.time()
        renderer.update_scene(data, camera=cam)
        img = renderer.render()
        Image.fromarray(img).save(out / f"{cam}.png")
        print(f"{cam}: {out / (cam + '.png')} ({time.time() - t0:.2f}s)")
    renderer.close()


if __name__ == "__main__":
    main()
