# Checker lab

Four small test geometries are generated locally with Trimesh and inspected by the consolidated mesh checker. The reports are actual program outputs. They test the helper and do not represent product approval.

```sh
uv run python examples/checker-lab/build.py
```

| Case | Expected observation |
| --- | --- |
| Closed block | No findings within the selected screening scope |
| Thin plate | Wall-thickness finding |
| Incorrect print pose | The declared orientation does not fit, even though a quarter-turn would fit |
| Detached island | Separate bodies and a floating underside remain findings |

Outputs include STL, a JSON report, the profile, hashes and a summary. The HTML documentation reads only the saved results. After changing the checker, regenerate the examples and rebuild the documentation.
