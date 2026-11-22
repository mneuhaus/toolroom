# From CAD assembly to rigid-body simulation and replay

A CAD assembly describes a machine at rest. A rigid-body simulation lets it handle loose parts before it exists, and a renderer can replay what happened on the real geometry. This article distils one worked pipeline: the Sorter V2 feeder, an Onshape assembly, turned into a MuJoCo simulation of LEGO pieces riding four spinning rotors and replayed in Blender for a clip. The handoff is vendored under the [cad-physics-simulation skill](../../skills/cad-physics-simulation/SKILL.md). Every number below is cited to a handoff file, and none is a measurement of the real machine.

## What this answers

- **Watching a mechanism handle loose parts before it exists.** Do pieces ride the rim, where do they land. A CAD motion study cannot say, because loose parts are not constrained; only contact physics moves them [handoff README, intro].
- **Exercising control software against a virtual machine.** The simulation exposes the same serial protocol and camera streams the real boards and cameras do, so the unmodified backend can boot, home and drive the rotors without hardware [sim/AGENTS.md, "Plugging in the control software"].
- **Producing footage that is physically driven rather than hand-animated.** Nothing about the pieces' path is keyframed; the renderer replays a logged trajectory on the real CAD [handoff README, intro].

What it does not answer: without calibration it predicts no real throughput, jam rate or force; friction and decomposition are stability choices, not fits. In [what a check establishes](../foundations/verification.md), the simulation row applies: behaviour of the defined model under its assumptions, with unmodelled effects and physical calibration unresolved.

## The pipeline

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
[handoff README, intro]

- **CAD export**: one glTF of the master assembly in metres, Z up; `translate_gltf.py` through the Onshape translation API.
- **Per-part meshes and collision pieces**: one STL per unique part, a manifest of names, transforms and materials, and convex hulls for each touched part; `sim.extract` and `sim.collide`.
- **Part library**: visual mesh, collision hulls, mass and inertia per LEGO part; `sim.pieces` from the LDraw library.
- **Physics**: driven rotor joints, every pose logged to `traj.npz` and `meta.json`; `sim.clip run` in MuJoCo.
- **Cheap preview**: a contact sheet, a preview video and `camera.json`; `sim.clip views` and `preview` with MuJoCo's renderer.
- **Replay render**: one PNG per frame in one of two looks; `sorter_render.py --stage clip` in Blender.
- **Encode**: the MP4 composited on white; `clip.sh` with ffmpeg.

## Exporting the assembly

Use the asynchronous translation route. The direct `/gltf` endpoint ignores every tolerance parameter and returns one fixed, coarse mesh; the translation job honours them [render/code/translate_gltf.py docstring]. The script posts `formatName: GLTF`, `flattenAssemblies: false`, `yAxisUp: false`, `grouping: true`, polls until `DONE` and downloads the external data [render/code/translate_gltf.py].

| Preset | Angular | Distance | Max chord | Result [handoff README §1] |
| --- | --- | --- | --- | --- |
| medium | 0.06 | 0.0004 m | 0.012 m | 2.8 M unique triangles in 3,513 nodes, about 206 MB, about 4 minutes |
| fine | 0.02 | 0.0001 m | 0.004 m | about 15 M triangles, 733 MB |

[render/code/translate_gltf.py, `LEVELS`]. The clip uses medium. The file is in metres, Z up, in the CAD's own frame with the chute column as world Z [handoff README §1]. Blender's glTF importer assumes Y up, so the render code rotates the imported root -90 degrees about X; after that Blender's world is the CAD's world, the frame the simulation logs in [render/code/sorter_render.py, main; handoff README §6].

The export re-tessellates every instance of a repeated part: same faces and bounds, different bytes. Deduplicate by part name, face count and local bounds, never by file hash [sim/sim/extract.py docstring]. Fasteners are dropped by a name pattern plus a size gate of 30 mm, because a 600 mm plate carries "screw holes" in its part name [sim/sim/extract.py, `FASTENER_MAX_M`].

## Collision geometry

MuJoCo collides a mesh as its convex hull, and a stator's hull would fill the channel. Convex decomposition is needed, but only for the parts pieces actually touch: the four rotors, the stators, the output guides, the rotor caps and the bulk cap [sim/sim/collide.py, `DEFAULT_PARTS`; handoff README §2]. Everything else is a visual geom with contact disabled [sim/sim/scene.py, class `vis`].

The LEGO pieces run CoACD with concavity threshold 0.1 and at most 6 hulls per part [sim/sim/pieces.py, argument defaults]. Contact cost grows with the hull count, and a fine decomposition turns every stud and the hollow underside into dozens of hulls, so the cap absorbs the studs [sim/sim/pieces.py, `decompose`]. Machine parts use threshold 0.04 and no cap [sim/sim/collide.py].

Machine collision geoms collide with pieces only, never with each other. Machine geoms carry `contype 2, conaffinity 1`, pieces `contype 1, conaffinity 1`, so a machine-machine pair shares no bit and generates no contact [sim/sim/scene.py, classes `col` and `piece`]. Without this, rotor hulls against stator hulls locked the rotors [handoff README, "Things that bit us"].

## Mass and inertia of the pieces

LDraw parts are open shells, so their mesh volume is meaningless. The library estimates a solid volume as 0.45 of the convex hull volume and multiplies by an ABS density of 1050 kg/m³; a watertight part uses its own volume instead [sim/sim/pieces.py, `SOLID_FRACTION`, `ABS_DENSITY`, `main`]. The handoff reports a 2x4 brick at about 2.4 g against 2.3 g real [handoff README §3], a plausibility check on the fraction, not a measurement made here.

Inertia is written explicitly: centre of mass and the six full-inertia terms of the convex hull at uniform density, scaled to the estimated mass [sim/sim/pieces.py, `inertia_props`]. The scene passes them as an `<inertial>` element and gives the collision hulls zero mass of their own [sim/sim/scene.py, piece body]. The reason is a failure: mass split across the CoACD hulls gave thin hulls near-zero inertia, and the simulation went NaN at first contact [handoff README §3].

## Driving the machine

Each rotor station is one body carrying the rotor, its cap and its 130-tooth output gear, on a hinge about world Z through the rotor's origin; C1 is the highest, the bulk section [sim/sim/scene.py, `ROTOR_PARTS`, `build`]. The joint has armature 20, damping 2 and a velocity actuator with kv 500 [sim/sim/scene.py]. The armature makes it heavy against contact: a piece can be carried by the rim but never slow it, as a stepper does not slip [sim/AGENTS.md, "How the machine is modelled"].

The bridge to the control software is arithmetic. The real drive is NEMA17 to 12T to a 24T idler to 130T at 1600 microsteps per motor revolution, so one output degree is 1600 × (130/12) / 360 microsteps; the fake firmware maps stepper velocity commands to joint velocities through that ratio [sim/AGENTS.md]. Speeds in the recorder are output degrees per second per rotor. The clip uses 10, 20, 30 and 30 so that a lot happens in a few seconds; the control software defaults to 2, 6, 10 and 10 [sim/sim/clip.py, `--speeds`; sim/sim/scene.py, `ROTOR_DEG_PER_S`].

Spin direction is a modelling fact. The rotors turn clockwise seen from above, `SPIN = -1` about +Z; pieces then land on a channel on the side facing the channel above and ride most of the way round to the stator's opening, just ahead of the output guide [sim/sim/scene.py, `SPIN`]. Check that against the real machine before believing anything downstream of it.

## Contact and time stepping

Options: timestep 1 ms, elliptic friction cones, `impratio` 10 [sim/sim/scene.py, `<option>`]. Contact: `solref 0.005 1`, `solimp 0.9 0.95 0.001`; a solref of 0.002, twice the timestep, was too stiff [sim/sim/scene.py; handoff README §4]. Friction 0.5, torsional 0.005, rolling 0.0001 [sim/sim/scene.py], an uncalibrated placeholder that roadmap step 4 is meant to replace with a fit against footage of the real feeder [sim/AGENTS.md, "Roadmap"].

Spawning matters as much as stepping. Pieces start on a 40 mm grid within a 95 mm radius over C1, jittered by ±6 mm, in layers 35 mm apart, the first 30 mm above the rotor top, so that no two pieces overlap; overlapping bodies fly apart on the first step [sim/sim/scene.py, `spawn_points`]. Part, colour and yaw come from a seeded generator [sim/sim/scene.py, `build`].

The recorder steps to each 30 fps frame, stops on the first non-finite state, and writes rotor angles, piece positions and quaternions to `traj.npz`; `meta.json` carries fps, frames, speeds, spin, seed, station origins and each piece's part and colour [sim/sim/clip.py, `run`]. The handoff observed about 0.22x real time with 40 pieces on a 4-core CPU, 50 s of physics in 220 s [handoff README §4]: one observation on one machine.

## Choosing the shot before spending GPU time

MuJoCo's own renderer is fast and plain, so it decides the camera before any GPU time. `sim.clip views` renders one moment from a grid of azimuth and elevation pairs as a contact sheet; `sim.clip preview` renders one camera over a time window. Headless Linux needs `MUJOCO_GL=egl` [sim/sim/clip.py].

A camera is a target point, a distance, an azimuth (0 looks along +X, counter-clockwise from above) and an elevation [sim/sim/clip.py, `camera`]. The preview writes `camera.json` with the resolved position, target, vertical field of view and first and last frame [sim/sim/clip.py, `preview`]. The Blender stage reads exactly that file: vertical sensor fit, `angle_y` from `fovy`, location and aim from `pos` and `target` [render/code/sorter_render.py, clip stage]. Nothing is re-framed by hand, so the cheap preview is the commitment.

The clip is frames 840 to 1200, 28 s to 40 s of the log, at 30 degrees vertical field of view [data/camera.json; handoff README §5]. The observation that set the elevation: at 30 degrees the near stator wall hid the rim the pieces ride on; 40 degrees looked into the channel [handoff README §5].

## Replaying in a renderer

The Blender clip stage rebuilds the simulated world from `meta.json`, `camera.json` and `traj.npz` [render/code/sorter_render.py, clip stage].

- One empty pivot per station at the logged rotor origin; rotor, cap and output gear are parented to the nearest pivot keeping their world matrix, and each frame sets the pivot's Z rotation to the logged angle.
- One object per simulated piece from the LDraw library, one mesh per part-and-colour variant. The loader uses the simulation's unit conversion (0.4 mm per LDraw unit, Y down to Z up), merges duplicate vertices and shades smooth at 35 degrees [render/code/ldraw_parts.py]. Each frame writes the logged quaternion and position into the object's world matrix.
- Frames render to a `.part` path and are renamed when complete; an existing frame is skipped, so a stopped render resumes without truncated images [render/code/sorter_render.py, `render_to`].

Two looks share this loop. Photo: Cycles on the GPU at 1280x924, 32 samples, adaptive sampling, OpenImageDenoise, AgX Medium High Contrast, transparent film [render/code/sorter_render.py, `setup_render`]; about 8.5 s per frame on an RTX 3090, about 50 minutes for 361 frames [handoff README §6]. CAD: Workbench with the export's own colours, studio light, cavity shading, outlines and 16x anti-aliasing [render/code/sorter_render.py, `cad_look`]; about 0.5 s per frame [handoff README §6].

One trap cost a factor of thirty. The lamp reflectors are emissive, and an emissive material on a mesh of tens of thousands of triangles made Cycles about 30 times slower. The fix sets `emission_sampling = "NONE"` on that material and adds a small point light inside each reflector [render/code/sorter_render.py, `add_lamp_lights`; handoff README §6].

Encoding overlays the frames on a white source and writes libx264 at CRF 18, 30 fps [render/code/jobs/clip.sh]. With ffmpeg 4.4, `ffprobe -of csv` rejects a space separator; `csv=s=x:p=0` works [render/code/jobs/clip.sh].

## Evidence and reproducibility

Log, camera file and export reproduce the exact clip without re-simulating: point the render job at the data folder [handoff README, "Re-rendering this exact clip"]. A re-simulation gives a different but equivalent clip, because contact physics is sensitive to the collision decomposition, the platform and the engine version [same section]. So keep `traj.npz`, `meta.json` and `camera.json` with the frames, plus export preset and tool versions, and bind any quantitative claim to that exact run. The handoff's timings (second rotor by 5 s, third by 15 s, fourth by 25 s) belong to seed 0, speeds 10/20/30/30, the medium export and the stated versions [handoff README §4].

Calibration is the open step. Rim friction and facet behaviour have not been fitted against footage of the real feeder [sim/AGENTS.md, "Roadmap", step 4]. Until then the simulation is a model of the drawing, not of the machine.

The control-software boundary is deliberately narrow: the backend talks to boards over a serial bus and to cameras by URL. A fake firmware answers the bus protocol on a pseudo-terminal per board, fake cameras serve the MuJoCo cameras as MJPEG streams named in the machine config, and a ground-truth side channel provides piece poses so perception can be stubbed with truth [sim/AGENTS.md, "Plugging in the control software"; sim/config/machine.sim.toml]. The scene camera's field of view is a placeholder until the real lens is measured [sim/sim/scene.py, `CAMERA_FOVY_DEG`].

## Qualifying a loose-part orientation change

Separate **loading, capture, turning, landing and reset**. A part deliberately placed at a useful contact can turn successfully while a freely dropped part never reaches that contact. A deep receiving pocket can permit one turn but prevent the next. Test these initial conditions separately, then repeat the complete cycle without respawning the part.

A planar section is a useful first model for the gravity line, contact edge and opposing-wall clearance. Measure stop height normal to the actual supporting ramp, not relative to the tray's lowest point. A high stop and an elevated turning location have different effects. Let the part translate, rotate and release freely in the subsequent contact simulation; a permanently pinned pivot only tests a conditional kinematic path. Yaw, cavities, studs and interlocked parts require later three-dimensional checks.

Define the requested observation before scoring. A large angle between two surface normals does not by itself mean that the required top and bottom changed places, especially on different resting slopes. Compare settled observations at a declared tray pose. For a marked top face, opposite signs of its world-up projection can identify a side change, with a declared minimum projection to exclude ambiguous edge-on states. Symmetric parts need a different requirement. Preserve earlier scores when refining the criterion and reassess the original trajectories rather than silently relabelling them.

For repeated turning, count transitions between distinct settled states: A→B→B is one turn, A→B→A is two. Do not respawn between them. If different tray poses are admissible, check both world and tray-relative orientation: either frame alone can mistake carrier rotation for a turn. Combine the side labels with a declared minimum change of the marked normal to exclude partial rocking. Verify the motion bound throughout the trajectory and its interpolation, rather than only at observation times. Missing orientation evidence cannot establish a pass.

Low directional stops can be of the same order as contact penetration or collision-proxy errors. Compare timestep, contact softness and contour resolution before ranking small geometric changes. A successful clip whose outcome changes under numerical refinement is mechanism evidence, not a qualified reliability result. Counts on a chosen friction/orientation grid are not measured success probabilities. For long parts spanning a concave bowl, use their actual supporting chord and additional contacts; the tangent directly below one edge is not the part's support angle.

Spawn from the **collision geometry**, which may extend beyond the visual mesh after decomposition. Check initial overlap, stationary-drive controls and a bounded timestep comparison before interpreting successes. Failed settling, numerical errors and unclassified orientations remain separate from physical failures. Apply the [verification evidence rules](../foundations/verification.md) to every reported result.

For a return-path sphere, unsigned distance to obstacle surfaces also requires an initially outside center before it can support a solid-clearance conclusion. An open obstacle mesh remains surface evidence unless an independent enclosing bound excludes the whole path. A corridor for each individual part does not prove a corridor for an interlocked pair or its carrier.

Separate the retained manipulation range from deliberate discharge. Material protruding above a rim is not necessarily lost; complete separation from a conservative container box is a sufficient, potentially late exit witness, not the earliest release angle. Test reversals and braking as well as a slow one-way discharge, and distinguish leaving the container from reaching the intended receiver. When comparing amplitudes, record whether move times were scaled to preserve speed. Return to a common inspection pose when large carrier angles make side classification ambiguous. Exploratory larger-angle trials must not silently widen the operating contract.

Check positional actuator travel across all modes of the same joint, including discharge, with explicit end reserves and transmission ratio. A shifted zero can place the required interval inside the actuator range but cannot reduce its span. Asymmetric manipulation may use travel already needed for discharge; a geometrically successful motion outside the joint budget remains only a diagnostic case.

Origin: Single Step Feeder tray and return-path study, September 2026. These are modelling and evidence rules; the study's mechanism dimensions, uncalibrated trial outcomes and raw trajectories remain in the originating project.

## Piles of loose parts in a hopper

- **Write `type="mesh"` on every mesh geom.** A geom that names a mesh through a default class but has no explicit type compiles as a sphere; every piece fell through the floor until the type was set.
- **Show the render group of the pieces.** The default visual options draw geom groups 0 to 2 only; pieces kept in group 3 to separate them from the machine are invisible until `geomgroup[3]` is switched on.
- **Measure pile mobility, not only deliveries.** Count per stroke the pieces in the machine that moved more than a few millimetres. A floor flatter than the friction angle (tan of the slope below μ) gives empty strokes while the pile stands still, which a delivery count alone cannot tell apart from an empty hopper.
- **Run a second seed before ranking variants.** A narrowed pickup that looked like a clear improvement on one seed starved on the next.
- **Large piles are expensive.** With 120 to 150 free pieces at a 0.25 ms timestep the CG solver ran about twice as fast as Newton with equivalent outcomes in a side-by-side check. Newton with 300 pieces ran about 100 times slower than real time. Pick the piece count for the question; a full bulk bin of thousands of pieces is usually out of reach.
- **Separate hull seams from mechanism edges.** Force peaks recurring at one height where two machine parts meet can come from the seam between their convex hulls. Ray-cast from the moving face through both the CAD meshes and the hulls before calling it a step in the design. The joint remains the edge a carried part runs over, so specify the downstream part set back or chamfered rather than proud.

Origin: Single Step Feeder S2 LEGO hopper study, October 2026. Dimensions, run results and videos remain in the originating project.

## Checklist

1. Export through the route that honours tessellation tolerances, and record the preset.
2. Fix units and up axis at export; rotate once at import so simulation and renderer share the CAD frame.
3. Deduplicate repeated parts by name, face count and bounds, not by file bytes; gate fastener removal by size as well as name.
4. Decompose only the parts loose pieces touch, cap hulls per piece, leave the rest visual.
5. Let machine geoms collide with pieces only, never with each other.
6. Write mass and inertia per body explicitly from one solid; never split mass across thin hulls.
7. Drive joints as heavy, velocity-controlled hinges when the real drive cannot slip, and keep the sim-to-controller ratio as arithmetic in one place.
8. Check the spin direction and landing side against the real machine.
9. Choose solref against the timestep; twice the timestep was too stiff here.
10. Spawn on a grid with clearance, and stop on the first non-finite state.
11. Pick camera and time window with the cheap renderer, then consume its camera file unchanged.
12. Exclude emissive high-poly meshes from light sampling and add a real light; write frames whole and rename.
13. Keep log, camera, export preset and versions with the output, and state that the model is uncalibrated.

## Source and limits

- Source: the Sorter V2 feeder clip handoff, September 2026 (README, `sim/`, `render/code/`, trajectory data of one clip). README and `AGENTS.md` are verbatim in the skill's [field notes](../../skills/cad-physics-simulation/references/field-notes.md); the code is a snapshot under `references/sorter-v2-feeder-clip/` in the [cad-physics-simulation skill](../../skills/cad-physics-simulation/SKILL.md), not maintained here.
- Licence: software MIT + Commons Clause, design content CC BY-NC-SA 4.0, like the sorter-v2 repository [sim/README.md].
- Not verified: no figure here is a measurement of the real machine. Triangle counts, file sizes, runtimes, per-frame render times and the 2x4 brick mass are the handoff's observations on its own hardware and versions. Friction, solref and the solid fraction are stability choices, not calibrated values.
- Environment: a Linux box with an RTX 3090 and a 4-core CPU, Blender 5.2.1, MuJoCo 3.13.0, ffmpeg 4.4; the export ran on a Mac through a local Onshape bridge [handoff README, "Software and hardware used"]. Endpoints and paths belong in `profiles/environment/`.
