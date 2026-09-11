"""Interactive 3D view of the scene with the rotors turning.

Run with mjpython on macOS (MuJoCo's viewer needs the main thread there):

    mjpython -m sim.viewer [--xml out/sorter.xml] [--pieces 8]

Elsewhere plain python works. Build the scene first with sim.scene, or pass
--pieces to build one here.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import mujoco
import mujoco.viewer

from sim.assets import out_root
from sim.scene import build
from sim.snapshot import drive_rotors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", default=None)
    ap.add_argument("--pieces", type=int, default=None, help="rebuild the scene with N test bricks first")
    args = ap.parse_args()
    xml = Path(args.xml) if args.xml else out_root() / "sorter.xml"
    if args.pieces is not None or not xml.exists():
        xml.parent.mkdir(parents=True, exist_ok=True)
        xml.write_text(build(args.pieces or 0, False))

    model = mujoco.MjModel.from_xml_path(str(xml))
    data = mujoco.MjData(model)
    drive_rotors(model, data)
    with mujoco.viewer.launch_passive(model, data) as v:
        v.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
        v.cam.fixedcamid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "overview")
        while v.is_running():
            t0 = time.time()
            mujoco.mj_step(model, data)
            v.sync()
            dt = model.opt.timestep - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)


if __name__ == "__main__":
    main()
