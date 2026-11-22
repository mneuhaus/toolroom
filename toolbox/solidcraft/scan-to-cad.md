# From a scan to a SolidCraft design

Three starting points: a flatbed scan of a profile section, a photo or drawing to trace, and a 3D scan. Cleaning,
registering and fitting a 3D scan is the job of the `scan-reverse-engineering` skill; scanning itself is the
`scanwerk` skill. This file covers the step into SolidCraft and back out as a measurement.

The numbers below come from a synthetic scan with known dimensions (an L section of 40 x 30 mm with one hole, at
20 px/mm), not from a real scanner. They show what each route does to a known shape.

## Flatbed scan of a section: two routes

| | DXF route | Canvas route |
| --- | --- | --- |
| Steps | [`scan/scan_kontur.py`](../scan/scan_kontur.py) traces the scan and takes the scale from the ruler in it, then `sketch.insert_dxf` | `canvas.insert`, `canvas.calibrate` with two points a known distance apart, `canvas.to_sketch` |
| Size of the result | **Run:** a DXF outline keeps its size exactly, 4677.46 of 4677.46 mm3 for the extruded section | **Run:** 40.06 x 30.07 mm for 40 x 30, about one pixel too large all round, +0.47 % volume |
| Scale | From the ruler's ticks, measured over its whole length | **Run:** the image comes out 70.0006 mm wide for 70 mm after calibrating on a 50 mm bar |
| What the sketch holds | Straight segments: a closed polyline arrives as lines, and so does every arc | Splines, unconstrained; **run:** 166 free degrees in the test sketch |
| Also traces | Only what the tracer was told to keep | Every dark shape in the image; **run:** the reference bar became a body of its own |

- **A measuring scan goes the DXF route.** The tracer works at sub-pixel level and reports the scale's linearity;
  the canvas trace is about a pixel off, which is 0.05 mm at 20 px/mm and would be about 0.01 mm at 2400 dpi.
  `scan_kontur.py` itself was last used on a real scan on 2026-11-03 and was not run again here; the test used a DXF
  of the form it writes.
- **The canvas route is for looking and for free shapes:** a photo or drawing under the sketch, an organic outline.
  Delete the traced shapes that are not the part before extruding.
- **Neither result is the design.** A traced outline is the reference. Mating faces, bores and reference lengths are
  redrawn as lines and real arcs with dimensions, and the trace stays underneath for comparison. A fit is first
  proven by a printed test piece; check the scale of an earlier print before fitting to it.
- Client scans stay local in their project and never become examples here.

## 3D scan

- **Measure the reconstruction against the scan with `pointcloud.deviation`.** `pointcloud.insert` reads the scan
  points (PLY, PCD, E57, XYZ and others); the deviation is measured from each point to the exact faces of a body and
  is signed for a closed body. **Run:** a cloud placed 0.05 mm outside a box reports a mean of +0.05000 mm with all
  2166 points measured. This is the acceptance number for "the rebuilt part matches the scan"; say how many points
  were measured and the worst ones.
- **`file.insert_mesh` brings the scan in as a mesh body** to model against. Mesh bodies are not measured by
  `inspect.clearance` or `inspect.interference` (they are listed as unchecked), so a collision check needs the native
  part.
- **`mesh.convert` gives an editable solid only for a part of constant section.** **Run:** the STL of a block
  becomes a solid with its 6 planar faces and the exact volume, and with a straight bore through it the bore comes
  back as one real cylinder. The same block with a countersink becomes a faceted solid of 4692 planar faces: closed,
  but nothing to edit. Rebuild such parts natively and use the mesh as the reference.
- **`body.repair`** sews and patches an imported body the kernel refuses. **Not run.**

## Examples

[`scan-dxf.json`](examples/scan-dxf.json), [`scan-canvas.json`](examples/scan-canvas.json),
[`pointcloud-deviation.json`](examples/pointcloud-deviation.json), [`mesh-convert.json`](examples/mesh-convert.json);
the scan inputs are written by
[`make_test_inputs.py`](examples/make_test_inputs.py).
