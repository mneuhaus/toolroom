> Imported field notes from the Sorter V2 feeder clip handoff (September 2026). Machine-specific values are examples; the current project and its profiles govern reuse.

# Sorter V2 feeder clip handoff

## How the Sorter V2 feeder clip was made

The clip shows LEGO pieces poured into the bulk section of the Sorter V2 feeder and carried
through the c-channels by the spinning rotors. Nothing about the pieces' path is animated by
hand: MuJoCo simulates the physics, and Blender replays the result with the real CAD, real
LEGO geometry and materials.

```
Onshape assembly
  -> glTF export (translate_gltf.py, async translation API with tessellation tolerances)
  -> per-part meshes + convex collision pieces (sim.extract, sim.collide)
LDraw parts library
  -> LEGO piece library: mesh, convex hulls, mass, inertia (sim.pieces)
MuJoCo
  -> 40 pieces poured into the bulk section, rotors driven, every pose logged at 30 fps (sim.clip run)
  -> camera and time window picked from cheap previews (sim.clip views / preview)
Blender 5.2
  -> the log replayed on the real assembly, rendered in two looks (sorter_render.py --stage clip)
ffmpeg
  -> frames composited on white and encoded (clip.sh)
```

### What is in this folder

| path | what |
|---|---|
| `sim/` | The simulation code as committed (MuJoCo, Python). Its `AGENTS.md` explains the modelling in more depth. |
| `render/code/sorter_render.py` | The Blender pipeline. The `clip` stage is the part used here. |
| `render/code/ldraw_parts.py` | LDraw part loader for Blender (mesh, smooth shading, ABS materials). |
| `render/code/translate_gltf.py` | The Onshape glTF export. |
| `render/code/jobs/clip.sh` | Renders one look of the clip and encodes it on white. |
| `data/traj.npz`, `data/meta.json`, `data/camera.json` | The exact simulation log and camera behind the clip, so the video can be re-rendered without re-simulating. |

### Software and hardware used

- Onshape, reached through Onshape Bridge (a local authenticated proxy to Onshape's REST API on `127.0.0.1:8317`), for the export. Run on a Mac.
- A Linux desktop with an RTX 3090 and a 4-core CPU for the simulation and all rendering.
- Python 3.10 on the Linux box (3.11 on the Mac): `mujoco 3.13.0`, `coacd 1.0.14`, `trimesh 5.1.0`, `numpy`, `scipy`, `Pillow` (`sim/requirements.txt`).
- Blender 5.2.1 LTS, the official Linux tarball. Cycles on CUDA (OptiX listed no device on our NVIDIA driver 525).
- ffmpeg 4.4.
- The complete LDraw parts library (library.ldraw.org, about 14,000 parts, with `LDConfig.ldr`).

### 1. Export the assembly from Onshape

The master assembly is `0001_Main` in the document `001_Sorter V2 - Main`; the document,
workspace and element IDs are at the top of `translate_gltf.py`.

```
python translate_gltf.py sorter_medium.gltf medium
```

It posts a translation job to `/api/assemblies/d/{doc}/w/{workspace}/e/{element}/translations`
with `formatName: GLTF`, `flattenAssemblies: false`, `yAxisUp: false`, `grouping: true` and the
tessellation tolerances, polls `/api/translations/{id}` until it is `DONE`, and downloads the
result from `/api/documents/d/{doc}/externaldata/{id}`.

- **Use the async translation route.** The direct `/gltf` endpoint ignores every tolerance
  parameter and returns one fixed, coarse mesh.
- `medium` (angular 0.06, distance 0.0004 m, max chord 0.012 m) gives 2.8 million unique
  triangles in 3,513 nodes, about 206 MB, in about 4 minutes. That is what the clip uses.
  `fine` is about 15 million triangles and 733 MB.
- The file is in metres, Z up, in the CAD's own frame: the chute column is the world Z axis.

### 2. Build the simulation assets

From `sim/`, with the export at `assets/export/sorter_medium.gltf`:

```
python -m sim.extract assets/export/sorter_medium.gltf --skip-fasteners   # ~15 s
python -m sim.collide                                                     # ~2 min
```

- `sim.extract` writes one STL per unique part mesh plus `assets/machine/manifest.json` (part
  names, transforms, materials). The export re-tessellates every instance of a repeated part,
  so identical parts are deduplicated by part name, face count and local bounds, not by bytes.
  `--skip-fasteners` drops screws, nuts and inserts (size-gated, because one plate carries
  "screw holes" in its part name).
- `sim.collide` runs CoACD convex decomposition on the parts pieces actually touch: the four
  rotors (`Rotor - Faceted`), the stators, the output guides, the rotor caps and the bulk cap.
  Everything else in the scene is visual only.

### 3. Build the LEGO piece library

```
SIM_LDRAW=/path/to/ldraw python -m sim.pieces
```

For each part in the starter set (46 common bricks, plates, slopes, tiles, round and technic
parts) it follows the LDraw subfile references, converts LDraw units (0.4 mm, Y down) to
metres Z up, welds the mesh, and writes `assets/pieces/<part>/visual.stl`, convex collision
pieces in `col/`, and an entry in `assets/pieces/library.json`.

- CoACD with threshold 0.1, capped at 6 hulls per part. Contact cost grows with the hull
  count, and the studs and hollow underside would otherwise become dozens of hulls.
- LDraw parts are open shells, so mass is estimated as 0.45 of the convex hull's volume times
  ABS density (1,050 kg/m³). A 2x4 brick lands at about 2.4 g against 2.3 g real.
- The body inertia is the convex hull's at uniform density, written explicitly. Splitting the
  mass across the CoACD hulls gave thin hulls near-zero inertia and the simulation went NaN at
  first contact.
- 30 to 100 s per part on a 4-core CPU.

### 4. Simulate

```
python -m sim.clip run --pieces 40 --seconds 50 --speeds 10,20,30,30 --seed 0
```

This builds the feeder-only scene (`out/clip/scene.xml`), pours 40 random library pieces in
random LEGO colours into the bulk section over the first rotor, turns the four rotors, and
logs every rotor angle and every piece pose at 30 fps to `out/clip/traj.npz`, with
`out/clip/meta.json` (rotor station origins, each piece's LDraw part number and colour).

How the machine is modelled (`sim/sim/scene.py`):

- Timestep 1 ms, elliptic friction cones, `impratio` 10, contact `solref` 0.005 (0.002, twice
  the timestep, was too stiff), friction 0.5.
- Each rotor is a hinge about world Z through its origin, carrying the rotor, its cap and its
  130-tooth output gear. The joint is armature-heavy (20) and driven by a velocity actuator
  (kv 500), so a piece can be carried by it but can never slow it, like a stepper.
- The rotors turn clockwise seen from above. Pieces land on each channel on the side facing
  the channel above and ride most of the way round to the stator's opening, which sits just
  ahead of the output guide.
- Machine collision geoms collide with pieces only, never with each other (contact type and
  affinity masks). Without that, rotor hulls against stator hulls lock the rotors.
- Pieces start on a jittered 40 mm grid in layers inside the bulk section. Pieces that start
  overlapping fly apart on the first step.
- Speeds are output degrees per second for the four rotors. The clip uses 10, 20, 30 and 30 so
  that a lot happens in a few seconds; the machine's control software defaults to 2, 6, 10 and 10.

It ran at about 0.22x real time on the 4-core CPU (50 s of physics in 220 s). Pieces reach the
second rotor by 5 s, the third by 15 s and the fourth by 25 s.

### 5. Pick the camera and the time window

These use MuJoCo's own renderer, which is fast and ugly, to decide before spending GPU time.
On a headless Linux box it needs `MUJOCO_GL=egl`.

```
MUJOCO_GL=egl python -m sim.clip views --target=-0.19,0.04,1.13 --dist 0.6 --azs=-25,-15 --els=32,40,48 --at 32
MUJOCO_GL=egl python -m sim.clip preview --target=-0.19,0.04,1.13 --dist 0.6 --az=-15 --el 40 --start 28 --end 40
```

A camera is a target point, a distance, the azimuth it looks along (0 = along +X,
counter-clockwise from above) and its elevation. `views` renders one moment from several
azimuth and elevation pairs as a contact sheet; `preview` renders the chosen camera over a
time window to `out/clip/preview.mp4` and writes `out/clip/camera.json` (position, target,
vertical field of view, first and last frame), which the Blender render reads. The clip is
frames 840 to 1200, 28 s to 40 s of the simulation, with a 30 degree vertical field of view.
At 30 degrees of elevation the near stator wall hides the rim the pieces ride on; 40 degrees
looks into the channel.

### 6. Render in Blender

```
render/code/jobs/clip.sh cad   <sim>/out/clip out/clip_cad
render/code/jobs/clip.sh photo <sim>/out/clip out/clip_photo
```

`clip.sh` runs Blender in the background with `sorter_render.py --stage clip`, then
composites the frames on white and encodes them with ffmpeg (libx264, CRF 18, 30 fps). As
written, it expects Blender at `~/blender/blender-5.2.1-linux-x64/blender`, the render code in
`~/renders/sorter-v2/code`, the export at `~/renders/sorter-v2/sorter_medium.gltf` and the LDraw
library at `~/renders/ldraw`, which is how our render box was laid out.

What the `clip` stage does:

1. Imports the glTF and rotates its root node -90 degrees about X. The export is Z up and
   Blender's importer assumes Y up; after the rotation Blender's world is the CAD's world, the
   same frame the simulation uses.
2. Assigns materials by part name and sub-assembly: frame and electronics boxes matte black
   PLA, chute white PLA, feeder parts gray PLA, lamp reflectors white and emissive, aluminium
   profiles anodized black, fasteners chrome, bins cardboard, the top plate plywood. Motors,
   casters and electronics keep their CAD colours.
3. Parents each station's rotor, rotor cap and output gear to a pivot at the rotor's origin.
4. Creates one object per simulated piece from the LDraw library (`ldraw_parts.py`: the same
   unit conversion as the simulation, duplicate vertices merged, smooth shading by angle at 35
   degrees, an ABS material per LDraw colour).
5. Places the camera from `camera.json`, with the same vertical field of view as the preview.
6. For each frame, turns each pivot by the logged rotor angle, sets each piece to its logged
   position and rotation, and renders. Frames are written whole (`.part`, then renamed), so a
   stopped render resumes where it left off.

The two looks:

- **photo**: Cycles on the GPU, 32 samples with adaptive sampling and OpenImageDenoise on the
  GPU, AgX view transform with the Medium High Contrast look, studio area lights, transparent
  film composited on white. The lamp reflectors glow with a small point light inside each: an
  emissive material on a mesh of tens of thousands of triangles made Cycles about 30 times
  slower, so their emission is excluded from light sampling. About 8.5 s a frame at 1280x924
  on the RTX 3090, so about 50 minutes for the 361 frames.
- **cad**: the Workbench engine with every part in the appearance colour the export carries,
  studio lighting, cavity shading and dark object outlines, 16x anti-aliasing. It reads like
  Onshape and renders in about 0.5 s a frame. Workbench runs headless on Linux with the NVIDIA
  driver.

### Re-rendering this exact clip

`data/` holds the simulation log behind the clip. With the same glTF export and the LDraw
library, point `clip.sh` at it instead of a fresh simulation:

```
render/code/jobs/clip.sh cad data out/clip_cad
```

That reproduces the clip. Re-simulating from scratch gives a different but
equivalent clip: the contact physics is sensitive to the collision decomposition, the
platform and the MuJoCo version.

### Things that bit us

- Onshape's direct glTF endpoint ignores tessellation tolerances; only the async translation
  route honours them.
- The export re-tessellates every instance of a repeated part, so deduplicate by name, face
  count and bounds.
- Rotor collision hulls touching stator hulls lock the rotors: keep machine geoms from
  colliding with each other.
- Explicit hull inertia for pieces, or the first contact goes NaN.
- A contact `solref` of twice the timestep is too stiff.
- Overlapping spawn positions explode on the first step.
- Emissive high-poly meshes slow Cycles about 30x; exclude them from light sampling and add a
  real light.
- ffmpeg 4.4's `ffprobe -of csv` rejects a space separator; `csv=s=x:p=0` works.


# Simulation repository AGENTS.md

## AGENTS.md

**This file is committed to the public repo.** Anything here must be generally
useful to any agent or contributor working in this repository: how things
build, where things live, what the conventions are. Nothing specific to one
person's machines, accounts or setup goes here; that belongs in the gitignored
`agents.local/` directory and `.env`.

If a gitignored `agents.local/` directory exists next to this file, read its
`README.md` and the files it lists first: it carries machine-local private
context (machine names, paths, access details) that never gets committed.

### What this is

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

### Layout

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

### Assets are never in git

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

### Frame and units

Metres, Z up, the CAD's own frame: the chute column axis is world Z through
the origin. The export re-tessellates every instance of a repeated part, so
`sim.extract` deduplicates by part name, face count and local bounds, not by
bytes. Part names in the manifest are the CAD part names; use them to find
things (`Rotor - Faceted`, `Stator`, `dummy camera`, `lamp inner reflector`).

### How the machine is modelled

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

### Plugging in the control software

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

### Roadmap

1. Static scene, rotors turning, test bricks riding the rim, camera snapshots. **Done.**
2. Fake firmware + MJPEG cameras; the backend boots against the sim, homes, and drives the rotors.
3. Real piece shapes (LDraw meshes, convex-decomposed, ABS mass) fed onto C1; pieces flow C1 -> C4 under the backend's feeder logic; perception in the loop.
4. Calibrate rim friction and facet behaviour against footage of the real feeder.
5. Trajectory export (per-body poses per frame) to the offline render pipeline for footage. **Started**: `sim.clip run` pours 40 pieces into C1 and logs `out/clip/traj.npz` + `meta.json`; `sim.clip views` and `preview` pick the camera and window cheaply and write `camera.json`, which the offline renderer replays. The physics runs at about 0.2x real time on a 4-core desktop with 40 pieces.
6. Chute, flaps and bins (stubbed until then: a piece leaving C4 is counted and removed).

### Conventions

- Delete, don't preserve. When something is replaced, remove the old path in
  the same change. Git is the backup.
- Nothing environment-specific in tracked files: no hostnames, absolute paths,
  or account details. `.env` and `agents.local/` hold those.
- Big files never enter git or LFS.
