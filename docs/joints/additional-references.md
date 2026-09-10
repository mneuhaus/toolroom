# Further joint references: panels and elastic clips

Four additional videos extend the joint library beyond sliding bars and keyed scarfs. The repeated [NeedItMakeIt link at 0:06](https://www.youtube.com/watch?v=fSISiR5XIbk&t=6s) is the same source already used for J08; it is not a ninth native example.

The new references were reviewed on 10 September 2026 using downloaded video frames and, where available, automatic English transcripts. The short sequences were sampled at one-second intervals; the panel video at ten seconds and the open-ring clip at four seconds, with additional detail frames. This is sampled visual review, not a measured reconstruction or a continuous motion analysis. The [source record](../../examples/printed-joints/additional-sources.json) identifies creators, dates, analysis basis and hashes. Original CAD files and full transcripts are not redistributed.

## Reference map

| Reference | What it adds | Status in this framework |
| --- | --- | --- |
| [Designer Snap Kit](https://www.youtube.com/shorts/UUiE-b5xlbo), Dsk, 10 December 2022 | A separate connector inserted between two receiving parts | Visual reference; no native reconstruction |
| [Thin panel joint](https://www.youtube.com/watch?v=E6BHts_ii8s), Payo, 21 November 2024 | Interleaved upper and lower engagement at a thin panel seam | Transcript and visual review; no native reconstruction |
| [Snap-fit prototype 3](https://www.youtube.com/shorts/JXoMlPqsxLQ), V3DPrints, 15 February 2023 | A clip installed from the accessible rim of an enclosure | Visual reference; internal dimensions not established |
| [Open-ring connector](https://www.youtube.com/shorts/ER19yHpgT30), Joseph Willis, 10 February 2024 | An elastic connector with open circular ends and a narrower entry slot | Transcript and visual review; selected source dimensions visible |

The native [Printed Joints Lab](../../examples/printed-joints/README.md) still contains J01–J08. These four references add design knowledge and candidates for subsequent coupons; they do not add verified native parts or load ratings.

## A separate connector as a reusable interface

Dsk's short shows a loose connector, two receiving parts, insertion into the first receiver, engagement with the second, and subsequent separation. The visible ends are open and shaped to yield during engagement. No dimensions, material, insertion force or cycle count are provided in the reviewed source. The title points to a separately distributed kit; its geometry is not imported here. [Source video](https://www.youtube.com/shorts/UUiE-b5xlbo).

**Framework interpretation:** treat the connector as a third component with its own material, print orientation and replacement policy. Keep the receiving geometry stable across products. A replaceable connector could move wear away from a large enclosure, but the receiver still needs sufficient wall and root thickness. Establish the release path, retention direction and permitted deflection before selecting a clip shape.

## Thin panels need engagement through the thickness

Payo demonstrates a flush seam between two 4 mm printed panels, with alternating engagement at the upper and lower faces. The transcript describes features reaching halfway through the thickness, or 2 mm, and a 0.05 mm CAD gap; 0.1 mm is suggested when using adhesive. The assembly is pressed into place and bent by hand in both directions. CAD views show the alternating seam features. These are source values and demonstrations, not calibrated settings or measured load capacity for our framework. [Source video, assembly around 0:58 and CAD around 1:46](https://www.youtube.com/watch?v=E6BHts_ii8s&t=58s).

**Framework interpretation:** a plan-view puzzle seam alone does not establish resistance to out-of-plane bending. Record which upper and lower faces carry each bending direction, and check the remaining hook roots. The pressing demonstration does not establish a collision-free rigid assembly path: any required flex, tilt or sequential engagement must be modelled and tested explicitly. A coupon should include a continuous panel control and identical support spacing for both bending directions.

## A rim clip adds an assembly-access pattern

V3DPrints shows a separate white clip pushed down over mating features at the upper rim of a black and white enclosure. It seats at the accessible edge. The brief sequence does not establish a release operation, material, dimensions or fatigue life. Subtitle retrieval was unavailable; this interpretation relies on the visible sequence and metadata. [Source video](https://www.youtube.com/shorts/JXoMlPqsxLQ).

**Framework interpretation:** record the access direction as part of the interface. A top-installed clip needs insertion space above the rim and a release route after neighbouring panels are fitted. Determine whether the clip only retains the panels or also locates them; locating surfaces should not be assumed to emerge from spring pressure. A seated clip in a short demonstration is not evidence of repeated serviceability.

## Open-ring clips make compliance explicit

Joseph Willis explains a connector whose open circular ends flex through a narrower entry. The shown sketch uses 16 mm outer end diameter and a 14 mm central width. Their 2 mm difference is a total width change, not an established per-arm displacement. The source describes 0.1 mm extra space on the front/back faces; the frame at 0:37 explicitly shows a 0.05 mm outer clearance operation, resolving an ambiguous automatic transcript. Rounded ends and an entry chamfer ease insertion. The creator attributes the concept to a prior enclosure design. These dimensions describe this example, not a general snap-fit recipe. [Source video](https://www.youtube.com/shorts/ER19yHpgT30).

**Framework interpretation:** keep end diameter, throat width, ring section, gap opening, depth clearance and lead-in as separate parameters. Orient the compliant shape deliberately relative to the deposited layers. Measure insertion and withdrawal forces, permanent set and behaviour after repeated assembly; assess sustained loading separately. A loop shape or a 2 mm width difference alone does not establish acceptable strain.

## Extend the verification method before adding native clips

The existing lab checks rigid bodies moving through sampled translations and rotations. A snap fit deliberately passes through a state where its undeformed solids overlap. Treating every overlap as failure rejects useful snaps; simply ignoring it can accept a clip that must break to assemble.

For an elastic joint, record three states: free shape, maximum assembly deflection and seated shape. Identify the compliant region and what supplies its restoring force. Use a justified deformation model or a measured coupon to establish acceptable strain; retain rigid interference checks for surrounding parts and tool access. Report geometric reconstruction, elastic analysis, printed fit, cycle testing and load testing separately.

A useful next coupon sequence is:

1. A panel seam with mirrored upper/lower engagement, alongside an unbroken panel control.
2. An open-ring connector with fixed receivers and a small, documented variation in ring section and entry width.
3. A rim clip with visible insertion and release access, tested after the surrounding enclosure is assembled.

These are proposed experiments. No native CAD, printed fit or strength result is claimed for them in this edition. See [Fits and retention](../../knowledge/fits-and-retention.md) for the general separation of guidance, preload and retention.
