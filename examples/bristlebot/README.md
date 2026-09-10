# Bristlebot: variants and calibration

The Bristlebot work combines reusable components, different form directions, spring legs and dedicated calibration coupons. In the Fusion branch, a shared frame is separated from variant-specific geometry.

## A fair comparison

The illustrated form study presents four variants at the same scale. A common geometric base makes both design comparisons and purely visual changes easier to recognise.

Mechanical parameters such as leg angle, stiffness and spread belong in a separate comparison. The MuJoCo prototype produces motion under its contact and spring assumptions. That simulation is distinct from the form render and requires physical calibration.

## What belongs in the framework

Reusable frames, parameter-driven variants, separate form and mechanics questions, and meaningful test coupons are shared patterns. One attractive variant image or a high simulated speed does not by itself establish a reliable design.

## Transferable rule

Variants should isolate the question being examined. Consistent cameras and scale help with form studies; shared boundary conditions help with mechanical comparisons.

Continue: [Construction patterns](../../knowledge/construction-patterns.md) · [Verification](../../knowledge/verification.md)

The English comparison figure is regenerated from the recorded frozen CAD inputs. Camera, scale and geometry pixels match the original; only label bands differ. Its display names map to the original configuration IDs as Pebble → `kiesel`, Comet → `komet`, Upright → `hochkant`, and Cricket → `grille`. The [regeneration helper](render_english.py) reads a supplied original review directory and requires its CAD runtime; it is separate from the offline documentation build. The check is recorded in [figure verification](../../validation/bristlebot-english-figure.json).
