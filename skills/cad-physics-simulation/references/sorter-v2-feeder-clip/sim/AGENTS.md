# AGENTS.md

**This file is committed to the public repo.** Anything here must be generally
useful to any agent or contributor working in this repository: how things
build, where things live, what the conventions are. Nothing specific to one
person's machines, accounts or setup goes here; that belongs in the gitignored
`agents.local/` directory and `.env`.

If a gitignored `agents.local/` directory exists next to this file, read its
`README.md` and the files it lists first: it carries machine-local private
context (machine names, paths, access details) that never gets committed.

## What this is

A simulation of the Sorter V2 machine: the CAD assembly in a physics engine,
LEGO pieces as rigid bodies, the rotors and chute driven the way the real
steppers drive them, virtual cameras where the real cameras are, and a fake
control board so the unmodified `sorter-v2` control software can run against
it. The point is to watch the machine sort in 3D and to exercise the control
software without a machine.

The engine is [MuJoCo](https://mujoco.org) from Python. It was chosen for the
part that matters most here: many small rigid bodies in frictional contact
with moving concave geometry, stable at real scale, deterministic, faster than
real time on a laptop, with offscreen camera rendering built in. It is not a
renderer; pretty footage comes from exporting a trajectory to a real renderer
(see the roadmap).

## Layout

```
sim/
  assets.py      where the asset set lives (./assets, or SIM_ASSETS)
  extract.py     CAD export (glTF) -> per-part STL meshes + manifest.json
  collide.py     CoACD convex decomposition for the parts pieces touch
  materials.py   part name -> material (colour, finish); shared spec
  scene.py       manifest -> MJCF: static machine, rotor hinges, cameras, lights
  snapshot.py    headless render of every camera to out/snap/*.png
  clip.py        a feeder clip: pieces poured into C1, every pose logged at 30 fps; previews
  viewer.py      interactive 3D view (mjpython on macOS)
config/
  machine.sim.toml   the control software's machine config when it runs against the sim
scripts/
  fetch-assets.sh    rsync the asset set into ./assets from SIM_ASSET_SOURCE (.env)
  push-assets.sh     the reverse, after regenerating assets
assets/    (gitignored) the asset set, see below
out/       (gitignored) generated scenes, renders, trajectories
```

Python: plain `pip install -r requirements.txt` into whatever interpreter you
use; no virtualenv is assumed. MuJoCo's interactive viewer needs `mjpython`
on macOS (installed with the `mujoco` wheel).

## Assets are never in git

The asset set is derived from the CAD and is large (hundreds of MB). It is
fetched with `scripts/fetch-assets.sh` from `SIM_ASSET_SOURCE` in `.env` (a
local path or an rsync `host:/path`), and regenerated with the pipeline below.
Do not commit it, and do not add it to Git LFS. Anything else big (renders,
trajectories, piece libraries) goes the same way.

```
assets/
  export/sorter_medium.gltf     the CAD master assembly, metres, Z up (from Onshape's
                                 async translation API; the direct glTF endpoint
                                 ignores tolerance parameters and is layout-only)
  machine/manifest.json          parts, transforms, materials (sim.extract)
  machine/meshes/<id>.stl        one file per unique mesh; repeated parts share one
  machine/collision/<id>/*.stl   convex pieces for contact (sim.collide)
```

Pipeline, from a fresh export:

```
python -m sim.extract assets/export/sorter_medium.gltf --skip-fasteners   # ~15 s
python -m sim.collide                                                     # ~2 min
python -m sim.scene --pieces 8 && python -m sim.snapshot --seconds 6      # proof it moves
mjpython -m sim.viewer                                                    # look at it
```

`--skip-fasteners` drops screws, nuts and inserts (about half the occurrences,
no function in the sim).

## Frame and units

Metres, Z up, the CAD's own frame: the chute column axis is world Z through
the origin. The export re-tessellates every instance of a repeated part, so
`sim.extract` deduplicates by part name, face count and local bounds, not by
bytes. Part names in the manifest are the CAD part names; use them to find
things (`Rotor - Faceted`, `Stator`, `dummy camera`, `lamp inner reflector`).

## How the machine is modelled

- **Rotor stations** C1 to C4 are the four `Rotor - Faceted` parts, highest
  first (C1 is the bulk section under the bucket, each station sits 80 mm
  below the last). Each is a hinge about world Z through the part origin,
  armature-heavy and velocity-driven, so contact can never slow it: a stepper
  does not slip. The rotors turn clockwise seen from above (`SPIN` in
  `scene.py`): pieces land on the side facing the channel above and ride most
  of the way round to the stator's opening, just ahead of the output guide. The body carries the rotor, its cap and its 130-tooth output
  gear. The real drive is NEMA17 -> 12T -> 24T idler -> 130T, 1600 microsteps
  per motor rev, so one output degree is 1600 * (130/12) / 360 microsteps.
  Default output speeds in the control software: C1 2, C2 6, C3 10 deg/s.
- **Contact** is the rotor, stator, output guide, rotor cap and bulk cap
  meshes, convex-decomposed. Machine geoms collide with pieces only and never
  with each other (contact masks in `scene.py`). The rest of the machine is
  visual only.
- **Cameras** are placed at the centre of each `dummy camera` part, looking
  straight down, named for the channel under them: `c_channel_2`,
  `c_channel_3`, `classification_channel` (C4). The real cameras run
  1280x720 at 30 fps. The field of view is a placeholder (43.3 deg vertical,
  a 78 deg diagonal webcam) until the real lens is measured.
- **Lights** are one spot per lamp reflector.
- **Materials** follow the render pipeline's approved look, ported to
  `sim/materials.py` so every consumer agrees; parts it returns `None` for keep
  the colour the export carries.
- **Pieces** are LDraw parts from the piece library (`sim.pieces`), parked
  above C2 or poured into the bulk section over C1 (`sim.scene --feed bulk`).
  Each piece's part and colour ride along in the scene as `<custom>` text.

## Plugging in the control software

The `sorter-v2` backend talks to two things: control boards over a serial
bus (COBS-framed frames, one per command, a JSON `INIT` reply naming the
board's steppers), and cameras through OpenCV, which takes a URL as well as a
device index. Both are stubbed at that boundary so the backend runs
unmodified:

- **Fake firmware** answers the bus protocol on a pseudo-terminal per board: a
  feeder board (`first/second/third_c_channel_rotor`, `carousel`, which the
  classification-channel setup uses as the C4 rotor) and a distribution board
  (`chute_stepper`, servos) that just accepts commands. Stepper velocity
  commands become rotor joint velocities through the gear ratio above.
- **Fake cameras** render the MuJoCo cameras and serve each as an MJPEG stream
  at a URL; `config/machine.sim.toml` points the backend's camera roles at
  them. A ground-truth side channel (piece poses in each camera's frame) lets
  perception be stubbed with truth before the real detectors are trusted on
  rendered images.
- The backend enumerates buses by USB vendor/product id, so it needs one
  small upstream change to accept an explicit port list from the environment.

## Roadmap

1. Static scene, rotors turning, test bricks riding the rim, camera snapshots. **Done.**
2. Fake firmware + MJPEG cameras; the backend boots against the sim, homes, and drives the rotors.
3. Real piece shapes (LDraw meshes, convex-decomposed, ABS mass) fed onto C1; pieces flow C1 -> C4 under the backend's feeder logic; perception in the loop.
4. Calibrate rim friction and facet behaviour against footage of the real feeder.
5. Trajectory export (per-body poses per frame) to the offline render pipeline for footage. **Started**: `sim.clip run` pours 40 pieces into C1 and logs `out/clip/traj.npz` + `meta.json`; `sim.clip views` and `preview` pick the camera and window cheaply and write `camera.json`, which the offline renderer replays. The physics runs at about 0.2x real time on a 4-core desktop with 40 pieces.
6. Chute, flaps and bins (stubbed until then: a piece leaving C4 is counted and removed).

## Conventions

- Delete, don't preserve. When something is replaced, remove the old path in
  the same change. Git is the backup.
- Nothing environment-specific in tracked files: no hostnames, absolute paths,
  or account details. `.env` and `agents.local/` hold those.
- Big files never enter git or LFS.
