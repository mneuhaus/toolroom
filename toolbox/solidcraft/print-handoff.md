# Print hand-off from SolidCraft

From a finished design to the delivered Bambu Lab A1 project. The delivery rule itself (a complete plate as the
normal 3MF, never the `.gcode.3mf`, with print time and filament weight) is in the `cad-fdm-design` skill and
[toolbox/print](../README.md).

## The route

1. **Mark the print face in the design.** `body.print_face` with a point on the flat face that goes on the bed, once
   per printed body. The choice is stored in the `.sc` file and follows the face when parameters change.
   **Run:** a bracket marked on a side face, then lengthened by a parameter, is still laid on that face.
2. **Export one STL per body, laid on its print face.** `file.export` with `bodies: [one body]`,
   `lay_on_print_faces: true` and `quality: "fine"` for parts with curved faces. The body comes out with the marked
   face at Z = 0 and its centre of mass over the origin.
   **Run:** bounding box Z from 0 to 20, centre of mass at 0, 0, mesh closed.
3. **Check each export for open edges** before anything else looks at it. A slicer hides them. If one is open,
   the fallback is the STEP export meshed with `mesh/step2stl.py`; STEP is never laid on the print face, so that part
   needs `rotate` in the plate file (quarter turns only).
4. **Build the plate** with `print/plate-3mf.mjs`: one entry per STL with its position `at`, and no `rotate` for a
   laid export, because the orientation is already in the file. **Run:** the plate report shows the laid height.
5. **Make the project and slice it as a check** with `print/slice-a1.sh`; state time and weight.
   **Run:** the laid bracket alone gives a Bambu project of 19 min and 3.8 g.

[`examples/print-handoff.json`](examples/print-handoff.json) is the script for steps 1 and 2.

## Decisions

- **Per-body exports, not one laid file for the plate.** In an export of several bodies with `lay_on_print_faces`,
  every body that has a print face is moved to the origin on its own, and a body without one stays where it was
  modelled. **Run:** two bodies in one laid 3MF, one moved to the origin and one left at X = 60. The file is neither
  the assembly nor a plate. Placement is the plate builder's job.
- **A body without a print face is exported as it lies, without a warning.** The reply lists the laid bodies in
  `print_faces`; a printed body missing from that list was not laid. **Run.**
- **The orientation belongs in the design, the placement in the plate file.** `rotate` in a plate JSON stays for
  STLs from other sources.
- **`file.send_to_slicer` is not the delivery route.** It opens the model in the desktop slicer without the A1
  project settings, and it starts a program on the user's screen. Use it only when the user asks to see the part in
  their slicer. **Not run.** `file.slicers` lists what it would find; **run:** it found the installed slicers.
- **`file.open_in_easyprint` uploads the model to a third party** and needs the user's explicit consent each time.
  Never for client parts. **Not run.**
- **3MF with `objects: "component"`** writes a component of several bodies as one object with parts, for
  multi-colour pieces. **Not run**; the multi-colour route in use is the `filaments` list of `plate-3mf.mjs`.

## What SolidCraft does not check

Overhangs, bridges, wall thickness, bed contact and plate arrangement have no command. They stay with the slicer and
the tools in [toolbox/mesh](../README.md): `sliceability.py` for supports, bridges and orientation comparison,
`strengthcheck.py` for the layer direction. `inspect.draft` and `inspect.accessibility` are view overlays for the
app, not measurements a script can read.
