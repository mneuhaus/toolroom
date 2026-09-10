> Imported field notes. Project-specific numbers, personal preferences and historical runtime assumptions are examples. The current framework entrypoint and explicit project profiles govern reuse.

# Scan → parametric CAD

Toolkit: `~/Workspace/cad/scan-toolkit/`, with flat modules rather than a package. Scripts set `sys.path[:0] = [<own src>, '<user-home>/Workspace/cad/scan-toolkit']`. Reference project: `~/Workspace/cad/linak-gehaeuse/`, the LINAK motor cover.

The recorded environment used **Python 3.12** because open3d had no 3.13 wheels at the time: `uv` with `requires-python = ">=3.12,<3.13"`, and dependencies numpy, scipy, open3d, trimesh, matplotlib, pillow and rtree.

## A proven working sequence

**0. Photographs first.** Inspect or request photographs of the actual part before measuring. In the LINAK project, interpreting topology from scans alone consumed over an hour; a photograph resolved it in seconds. Photographs also distinguish actual form features from artefacts: the circular “dents” were attached Revopoint markers.

1. **Inspect:** `views.py` provides six axial views and `spin.py` a 12-view orbit. Both splat area-weighted points inside triangles. CAD exports can contain a few very large triangles; splatting their centroids makes a solid surface look perforated.
2. **Clean:** `clean.py` removes the turntable below a height and then filters components; `clean2.py` uses a RANSAC plane and DBSCAN. Revopoint output is not necessarily upright: the turntable may be normal to Y. Detect the plane without assuming its orientation or z ≈ 0. Filter marker spheres by bounding-box diameter.
3. **Register:** `reg.py` uses global FPFH + RANSAC followed by point-to-plane ICP at three resolutions. In the recorded project, fitness >0.7 and RMSE <0.3 mm indicated the same part in the same pose. A large amount of turntable geometry interferes with registration; clean it first.
4. **Align canonically:** axis hypotheses from `primitives.py` usually yield an orthogonal triplet of main axis, transverse axis and plane normal. Refine the axis using centres from circle fits in individual slices, rather than normals alone. **NumPy trap:** `xs = vc[:,0]` is a view. After `vc[:,0] -= xs.min()`, `xs.min()` is already zero. Save offsets as floats beforehand.
5. **Measure:** use `sections.py` for actual contour sections, zoomed plots with fine grids, `fitlib.py` for circle/plane fitting with outlier rejection, and `primitives.py` for Efficient RANSAC plane/cylinder/cone/sphere detection.
6. **Separate base form from features:** `decompose.py` applies greyscale morphology to polar radius R(θ). `opening` removes narrow convex ridges; `closing` fills narrow concave grooves. The difference represents the feature and becomes its own parametric CAD element.
7. **Compare:** `outer_ref.py` generates a dense exterior-only point cloud using the polar maximum per section, excluding internal ribs. `diff2.py` computes bidirectional deviation and a map. Use median and p90 as the main metrics rather than the maximum alone.

## Tool reference

| Module | Purpose |
| --- | --- |
| `meshio.py` | Fast binary STL reading/writing, `weld`, `components`, `face_props`, `submesh` |
| `fitlib.py` | `fit_circle`, `fit_plane` with iterative outlier rejection |
| `sections.py` | Triangle-plane intersections into segments; plots at multiple stations |
| `contour.py` | `outer_contour`: polar maximum per angular bin, interpolated gaps, circular smoothing; `resample` |
| `decompose.py` | Greyscale morphology: `opening`, `closing`, `base_profile` |
| `primitives.py` | Efficient RANSAC segmentation and least-squares refits |
| `clean.py` / `clean2.py` | Remove turntable and marker spheres |
| `reg.py` | Global registration and ICP with open3d |
| `merge.py`, `apply_T.py`, `crop.py` | Apply transforms, merge and crop |
| `holes.py` | Find open boundary loops and distinguish real openings from scan holes |
| `views.py`, `spin.py` | Axial views and orbit contact sheets |
| `outer_ref.py`, `diff2.py` | Reference skin and deviation measurement |
| `fus.py` | Fusion MCP client with a 900-second timeout; Khana's recorded `fcall.py` timed out after 300 seconds |

### Cone refitting for usable segmentation

Two linear relationships make the fit robust:

- Surface normals make the same angle with the axis. Recover the axis from an SVD of the centred normals.
- The apex lies in every tangent plane: `N_i · (apex − p_i) = 0`. Solve for the apex with `lstsq`.

Without this refit, sphere fits split a cone into bands. A sphere of approximately r33 mm can locally fit a 14 mm strip within 0.35 mm, producing misleading segmentation.

## Recover design intent

Aim for the simplest form that functionally replaces the part. Maximum agreement with the scan is not sufficient by itself.

- **Rationalise:** the LINAK body measured as a slightly bulging cone, approximately +0.2 mm over 90 mm. The project interpreted this as shrinkage rather than an intended feature and used a straight cone with 1.25° draft.
- **Look for draft:** plot radius along the axis with `profile.py`. A clean linear dR/dx indicates a draft candidate that belongs in the model rather than being averaged away.
- **Prioritise functional surfaces:** fits, channels, holes and seating planes need accurate reconstruction. The recorded project allowed approximately 0.5–1 mm deviation on cosmetic regions; this is not a universal tolerance.
- **Check symmetry and coincidence:** they reveal likely construction intent. Both LINAK transverse-channel wall openings fitted at x = 126.15 mm, placing the channel axis in the mouth plane and suggesting one shared parameter.
- **Measure simplification hypotheses:** a head modelled as a two-profile loft with tangencies sounded plausible but had a median deviation of 2.0 mm and was rejected. A rolling transition represented by one R32.9 mm arc achieved RMS 0.18 mm over 33 mm. Calculate before accepting the hypothesis.

## Pitfalls

- **Polar maximum bridges undercuts.** `outer_contour` returns the outermost hit on each ray and covers channels and pockets. This is useful when constructing a base form before cutting pockets, but it can mislead measurements.
- **Boundary loops are not necessarily scan holes.** Use `holes.py` to classify them. A smooth loop with perimeter close to a circle suggests a real opening; a ragged loop with roughly twice that perimeter suggests missing scan data. Confirm with the physical reference.
- **Scan markers** sit approximately 0.1–0.2 mm above the surface and slightly increase the polar maximum radius. This matters at tolerances below 0.3 mm.
- **STL deviation sampling must sample inside triangles.** Otherwise the measurement reflects the CAD export's tessellation rather than its geometry.
