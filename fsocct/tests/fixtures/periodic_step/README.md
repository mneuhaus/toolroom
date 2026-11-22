# Trimmed periodic STEP face

This valid toroidal ring with its attached stem was captured from `hotWireDeployed`
in the [frozen hot-wire source](../../../cases/workspace/hot_wire.fs). Source
provenance and SHA-256 are in the [manifest](../../../cases/workspace/manifest.json).
Coordinates are millimeters; the source volume is 1,103.6016389553097 mm³.

Default OCCT 7.9 STEP export/reimport produces an unorientable toroidal face,
although the original seven-face solid is valid. Splitting closed faces on a
deep copy before retrying the export produces a valid eleven-face solid. The
test checks the STEP round trip, volume drift below 0.002 mm³, and that export
does not alter the original solid's volume, validity or topology.
