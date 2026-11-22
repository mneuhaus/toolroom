# Boolean unification regression

These operands were captured immediately before `channelBasesR3/n34/op` in the
[frozen workspace source](../../../cases/workspace/channel_bases.fs), whose
original path and SHA-256 are recorded in the [manifest](../../../cases/workspace/manifest.json).
Coordinates are millimeters. They contain a valid accumulated channel base and
the next union tool.

On OCP 7.9.3.1.1 the raw union is valid and has volume 37,234.504628831484 mm³.
`ShapeUpgrade_UnifySameDomain` makes that result invalid, changes its volume to
36,817.801903508 mm³ and mutates its input even with safe-input mode enabled.
The adapter therefore simplifies a deep copy and retains the untouched raw
boolean if simplification fails validity. The regression checks union volume,
result validity and unchanged, valid input operands.
