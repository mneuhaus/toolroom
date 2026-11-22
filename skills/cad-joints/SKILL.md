---
name: cad-joints
description: Design or compare mechanical joints between CAD parts, including their fit, retention and assembly or release path.
---

# CAD joints

Design both mating parts around the requested connection, load directions and permitted movement. Preserve the user's part-count, material and simplicity requirements. Distinguish rigid stops, friction and elastic retention; add a mechanism only when it serves an identified requirement.

- Derive mating surfaces from common reference geometry. State which part owns the allowance and whether it is per face, diametral or normal to the surface; do not offset both parts accidentally.
- Check insertion and removal with the surrounding parts and tools present. A clear final pose does not prove a usable assembly path. A rigid interference check cannot establish elastic insertion or holding force.
- Keep nominal dimensions, source observations and measured fits distinct. A source clip's proportions or a successful coupon do not transfer its force or lifetime to another size, material or print pose.

Read the relevant reference when that issue is part of the task:

| Question | Reference |
| --- | --- |
| Selecting or reconstructing a joint | [Joint principles](../../knowledge/construction/joints.md) |
| Sliding fit, pressfit, preload or an elastic latch | [Fits and retention](../../knowledge/construction/fits-and-retention.md), including unloaded, insertion and seated states |
| Access, hardware, assembly sequence or moving neighbours | [Assembly review](../../knowledge/construction/assembly-review.md) |
| OpenLOCK/Dragonbite-style sockets and clips | [Tile clip joints](../../knowledge/construction/tile-clip-joints.md) and the [socket lab](../../labs/tile-clip-sockets/README.md) |
| Other printed connection examples | [Panel and clip references](../../knowledge/construction/joints-panels-and-clips.md) or the [joint lab](../../labs/printed-joints/README.md) |

For bending or tensile claims, assess the weakest root, remaining socket wall and layer direction; larger engagement alone proves no strength gain. Elastic checks need an appropriate deflection model or measured coupon, with assumptions and limits recorded.

Use the selected CAD backend for construction. For printed fit comparisons, use [FDM preparation](../cad-fdm-design/SKILL.md), fixed counterpart geometry and a small allowance series in the intended pose/material. Apply [verification](../../knowledge/foundations/verification.md) to the changed interfaces; distinguish geometric acceptance, print readiness and physical fit/load results.
