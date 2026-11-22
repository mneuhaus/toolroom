"""Public Python API used by the CLI and integration tests."""

import time
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

from . import __version__
from .kernel import Context, export_step, export_stl
from .runtime import Engine, Feature
from .syntax import FSError, parse
from .values import Id, Quantity, Tagged, Vector


def report_value(value):
    if isinstance(value, Quantity):
        return {
            "type": "ValueWithUnits",
            "value_si": value.value,
            "dimensions": {"length": value.dims[0], "angle": value.dims[1]},
        }
    if isinstance(value, Tagged):
        return {"type": value.tag, "value": report_value(value.value)}
    if isinstance(value, (list, Vector, Id)):
        return [report_value(x) for x in value]
    if isinstance(value, dict):
        return {k: report_value(v) for k, v in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {"type": type(value).__name__, "value": "opaque"}


@dataclass
class Build:
    context: Context
    engine: Engine
    entrypoint: str
    elapsed_seconds: float
    definition: dict

    def report(self):
        return {
            "schema_version": 1,
            "fsocct_version": __version__,
            "ocp_version": version("cadquery-ocp"),
            "entrypoint": self.entrypoint,
            "definition": report_value(self.definition),
            "limits": {"max_steps": self.engine.max_steps, "max_depth": self.engine.max_depth},
            "elapsed_seconds": self.elapsed_seconds,
            "ast_steps": self.engine.steps,
            "sources": self.engine.sources + self.context.assets,
            "warnings": self.engine.warnings,
            "console": self.engine.output,
            **self.context.report(),
        }

    def step(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return export_step(self.context, path)

    def stl(self, path, tolerance=0.05):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        export_stl(self.context, path, tolerance)


def expression(engine, source, env=None):
    nodes = parse(f"const parameter = {source};", "<parameter>")
    if len(nodes) != 1 or nodes[0].kind != "declare" or nodes[0].args[0] != "parameter":
        raise FSError("Expected a single parameter expression")
    return engine.eval(nodes[0].args[2], engine.base if env is None else env)


def run(
    path,
    *,
    feature=None,
    definition=None,
    parameters=None,
    imports=None,
    fonts=None,
    max_steps=1_000_000,
    max_depth=128,
    progress=None,
):
    start = time.perf_counter()
    engine = Engine(imports=imports, max_steps=max_steps, max_depth=max_depth)
    module = engine.load(path)
    if feature is None:
        choices = sorted(k for k in module.exports if isinstance(module.env.get(k), Feature))
        if len(choices) != 1:
            raise FSError("Select --feature; exported features: " + (", ".join(choices) or "none"))
        feature = choices[0]
    if feature not in module.exports:
        raise FSError(f"Entrypoint {feature!r} is not exported")
    values = dict(definition or {})
    for name, expr in (parameters or {}).items():
        values[name] = expression(engine, expr, module.env)
    context = Context(progress=progress, fonts=fonts)
    fn = module.env.get(feature)
    if isinstance(fn, Feature):
        values = {**fn.defaults, **values}
    module.call(feature, context, Id((feature,)), values)
    return Build(context, engine, feature, time.perf_counter() - start, values)
