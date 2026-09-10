# The shared core

A task selects the required steps. The core keeps together information that can otherwise be lost between CAD, manufacturing and documentation.

## Establish the authoritative source

| Starting point | Authoritative source | Consequence |
| --- | --- | --- |
| Build123d or Fusion-Khana model | Current source program and parameters | Build from the documented program; record the runtime and dependencies |
| Natively revised Onshape model | Current native features and consumed source revision | Preserve later user features; an older generator may be incomplete |
| Scan reconstruction | Reference data and a justified replacement model | Document measurement uncertainty separately from simplified form assumptions |
| Assembly manual | CAD snapshot, bill of materials and build-stage recipe | Separate cameras and exploded offsets from actual installed poses |

Before editing, establish what is current, which parts are affected, which source is actually consumed and which interfaces remain protected.

## Identity, units and pose

A part has a semantic identity, such as “right bearing carrier”. Native IDs and array positions map to that identity. The same ID can refer to changed geometry; a new ID can replace an otherwise unchanged part.

Native model coordinates, assembly pose, print pose and illustration offset are different data. Every transform has a known direction and unit. Check orthogonality and determinant +1 for rotations; mirroring is a separate design operation.

STL does not contain reliable explicit units. Record the unit from the export workflow and verify it against actual dimensions.

## Rule precedence

1. Explicit task instructions and protected mechanical interfaces.
2. Verified native geometry and the purchased components actually used.
3. Calibrated process data with documented measurements.
4. Agreed design-language rules.
5. Uncalibrated example values and historical cases.

An approved material does not imply approval of a particular joint. A style profile does not determine the number of screws. A manual does not require geometry changes when only its page layout is being revised.

## Bind results to evidence

Exports are bound to their source, revision, settings and geometry hash. Inspection results apply to those exact inputs. When inputs change, renew the affected evidence; unchanged results may be reused when their identity is demonstrated.

[Verification](verification.md) distinguishes the evidence types. [Project layout](../workflow/project-layout.md) describes an appropriate file structure for longer tasks.
