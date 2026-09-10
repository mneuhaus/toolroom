# Assembly, access and load-path review

Use for screwed adapters, rail carriages, belt tensioners and compact mechanisms.
Derived from Sparky R4–R7 and Alternate Chute / SC15 (September 2026); the
particular hardware and dimensions are examples, not universal design rules.

## Retrofitting an existing interface

Measure mounting-hole axes, seating planes and the real hardware envelope
before adding material. An offset bracket should not acquire little extensions
merely to conceal misalignment. Set the intended flush contact and verify the
axes together; if the envelopes conflict, redesign the load path explicitly.
Keep purchased hardware geometry faithful to the source. A large chamfer on a
printed housing can change; a real servo case cannot be reshaped to pass a check.

Connector access includes the inserted plug, insertion/removal path and cable
exit/bend space. For a daisy-chained servo, check **both sockets**, including the
one obscured by a lower bracket. A simplified servo solid may omit connectors;
mark the measured/assumed plug envelope instead of reporting housing clearance
as proof of connector access. Check again with the complete assembly present.

Before detailing a cheaper servo plus reduction, compare the complete option:
required output torque/travel/speed, losses, backlash, bearings, extra printed
parts, envelope, assembly effort and total cost. A nominal reduction ratio alone
does not establish useful torque, reachable travel or economic value. Use
available bearing models/inventory where suitable; order history is not proof
of remaining stock. Record and respect a discarded drive branch rather than
reviving it from old source files.

## Before cutting access windows

Describe a feasible assembly sequence, including which parts are present at each
step. If A must be fastened before B but B blocks A's fasteners, the sequence has
a cycle. Resolve it in the design: separate subassemblies with a later accessible
joint, captive fasteners, or a genuinely reachable access route. Do not merely
write “install these screws first” when the next step makes that impossible.

Choose access together with the load path. The Sparky front-loading belt opening
removed too much supporting material and was rejected as flimsy. Rear belt loading
with an externally accessible tension screw was accepted. Keep a broad reacting
wall/ledge, guided slider and adequate material around holes and nut pockets.
Do not extend a thin cantilever solely to achieve a preferred access direction.

For a split adapter, retain support across the interface, define alignment/shear
transfer where needed, and ensure fastener heads are recessed on both mating
faces. A stepped split can retain the tensioner wall while sharing central plate
thickness. Select the split and bed faces together; a small projecting pad can
lift the entire plate off the bed.

## Check three different geometries

1. **Fastener installation:** actual head diameter/height, shaft, washers, nut
   pockets and nut insertion path. Check the head's travel separately from the
   thinner driver shaft. Model the straight tool approach and working space;
   never assume a ball-end key or a special tool the user has not specified.
2. **Subassembly joining:** move the pre-fastened subassemblies through the real
   insertion path, with their screws and already-installed accessories present.
   A sensor flange or its screw head may clear the final position but block the
   approach. Test relevant adjustment extremes as well as the displayed pose.
3. **Operation and service:** sweep all moving bodies, including newly added
   halves and hardware, against fixed parts. Check both travel ends and changes
   near collisions; use denser/adaptive samples or swept envelopes for narrow
   obstacles. A finite sample set is not a proof for every intermediate pose.
   Include a suitable overtravel negative control when checking travel stops.

Compare the complete hardware envelope against width/depth limits. Check collars,
washer diameters, head protrusion and screw tips, not just the printed silhouette.
Sparky's washers affected PCB clearance; a half-millimeter screw-tip protrusion
also breached the width limit. Removing either from the test would hide the bug.

Choose fastener length from the real stack and available threaded depth. “Longer
for more engagement” can hit internals: the longer laser screws in Sparky did.
A geometrically fitting short screw is not proof of sufficient thread strength;
record actual engagement and remaining physical/load validation explicitly.

## Belt and bearing specifics

- Determine whether the belt is open or endless from the physical reference.
  Draw separate ends for an open belt, with a fixed anchor and a guided moving
  anchor when that is the intended mechanism. A visually continuous reference
  belt must not erase the tensioning gap.
- Check belt width, actual tooth profile and slot insertion direction. Reference
  tooth dimensions are a starting point for the user's real belt and print fit.
- Prove slider insertion, tension travel, nut capture and tool access separately.
  Tightening must move the intended anchor in the direction that increases belt
  tension. Do not consume the rail's full nominal travel when the user needs less.
- An integrated idler pedestal can remove an unnecessary separate bracket. Verify
  the axle stack and nut access; stationary supports/shims should bear on the
  intended inner race, clear rotating flanges/shields, and permit free rotation.

## Evidence and handoff

Use semantic part roles for collision exemptions and moving groups. Reconcile
expected printed-part count separately from hardware/reference body count.
Record intentional contacts narrowly (for example simplified smooth belt envelope
against tooth pockets), and investigate every other contact. Numerical slivers
need a localized diagnosis; do not globally delete “small” bodies to pass counts.

A larger volume or unchanged minimum layer section does not establish stiffness.
Assess the actual load path and chosen print orientation; distinguish geometric
clearance, slicing, strength heuristics and physical fit/load testing in results.

Deliver a short assembly sequence, concrete fastener stack, retained parts, and
replacement parts relative to the revision the user actually printed. A completed
CAD export or sliced plate does not mean that a print has started.
