"""Bounded AST evaluation and an explicit local standard-library bridge."""

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

from .syntax import FSError, LimitExceeded, Unsupported, parse
from .values import (
    ANGLE,
    LENGTH,
    UNITS,
    Box,
    FSArray,
    Id,
    Matrix,
    Quantity,
    RuntimeErrorFS,
    Tagged,
    Vector,
    binary,
    boolean,
    check_key,
    clone,
    cross,
    display,
    dot,
    equal,
    index_get,
    index_set,
    matrix,
    norm,
    normalize,
    number,
    scalar,
    unary,
    untag,
    vector,
)


@dataclass
class Slot:
    value: object
    constant: bool = False
    constraint: str | None = None


class Env:
    def __init__(self, parent=None, module=False):
        self.parent, self.module, self.slots = parent, module, {}

    def find(self, name):
        if name in self.slots:
            return self.slots[name]
        if self.parent:
            return self.parent.find(name)
        raise Unsupported(f"Unknown symbol {name!r}; it may require an unimplemented library API")

    def get(self, name):
        return self.find(name).value

    def define(self, name, value, constant=False, constraint=None):
        if name in self.slots:
            raise RuntimeErrorFS(f"Duplicate declaration {name!r}")
        self.slots[name] = Slot(clone(value), constant, constraint)

    def capture(self):
        if self.module:
            return self
        env = Env(self.parent.capture() if self.parent else None)
        env.slots = {
            k: Slot(clone(v.value), v.constant, v.constraint) for k, v in self.slots.items()
        }
        return env


@dataclass
class Function:
    node: object
    closure: Env


@dataclass
class Overloads:
    functions: list


@dataclass
class Feature:
    function: Function
    defaults: dict


class Return(Exception):
    def __init__(self, value):
        self.value = value


class Break(Exception):
    pass


class Continue(Exception):
    pass


class PredicateFalse(Exception):
    pass


class Module:
    def __init__(self, engine, env, exports):
        self.engine, self.env, self.exports = engine, env, exports

    def call(self, name, *args):
        return self.engine.call(self.env.get(name), list(args))


class Engine:
    def __init__(self, *, max_steps=1_000_000, max_depth=128, imports=None):
        self.max_steps, self.max_depth = max_steps, max_depth
        self.steps, self.depth = 0, 0
        self.types = {
            k: "native"
            for k in (
                "LengthBoundSpec",
                "AngleBoundSpec",
                "IntegerBoundSpec",
                "RealBoundSpec",
                "Color",
                "CoordSystem",
                "Cylinder",
                "Cone",
                "Sphere",
                "Torus",
                "BSplineSurface",
                "ControlPointMatrix",
                "KnotArray",
            )
        }
        self.imports = imports or {}
        self.sources, self.warnings, self.output = [], [], []
        self.loading, self.modules = set(), {}
        self.base = Env(module=True)
        self.base.slots = {k: Slot(v, True) for k, v in self.builtins().items()}

    def tick(self, token):
        self.steps += 1
        if self.steps > self.max_steps:
            raise LimitExceeded(f"Execution exceeded {self.max_steps} AST steps", token)

    def is_type(self, value, name):
        base = untag(value)
        standard = {
            "undefined": value is None,
            "boolean": type(base) is bool,
            "number": type(base) in (int, float),
            "string": isinstance(base, str),
            "array": isinstance(base, (list, Vector, Id)),
            "map": isinstance(base, (dict, Quantity)),
            "box": isinstance(base, Box),
            "function": isinstance(base, (Function, Overloads, Feature)) or callable(base),
            "builtin": getattr(base, "fs_builtin", False),
            "Vector": isinstance(value, Vector),
            "Matrix": isinstance(value, Matrix),
            "Id": isinstance(value, Id),
            "ValueWithUnits": isinstance(value, Quantity),
        }
        if name in standard:
            return standard[name]
        if isinstance(value, Tagged) and value.tag == name:
            return True
        if name in ("Context", "Query", "Sketch", "Plane", "Transform", "Line", "CoordSystem"):
            return type(value).__name__ == name
        if name in self.types:
            return False
        # Builtin enum types are known via the enum map in base.
        if name in self.base.slots and isinstance(self.base.get(name), dict):
            return False
        raise Unsupported(f"Unknown type {name!r}")

    def require_type(self, value, constraint):
        if constraint and not self.is_type(value, constraint):
            raise RuntimeErrorFS(f"Expected {constraint}, got {display(value)}")

    def cast(self, value, name):
        if name == "Id":
            v = untag(value)
            if not isinstance(v, (list, Id)) or not all(isinstance(x, str) for x in v):
                raise RuntimeErrorFS("An Id must be an array of strings")
            return Id(v)
        if name == "Vector":
            return vector(*untag(value))
        if name in ("number", "string", "array", "map", "boolean", "box", "function", "undefined"):
            self.require_type(value, name)
            if isinstance(value, (Vector, Id)):
                return list(value)
            if isinstance(value, Quantity):
                raise Unsupported("Inspecting the underlying ValueWithUnits map is not implemented")
            return clone(untag(value))
        enum = self.types.get(name)
        if enum is None and name in self.base.slots:
            v = self.base.get(name)
            enum = list(v) if isinstance(v, dict) else None
        if isinstance(enum, list):
            if untag(value) not in enum:
                raise RuntimeErrorFS(f"Invalid value for enum {name}")
        elif name not in self.types:
            raise Unsupported(f"Unsupported type cast {name!r}")
        return Tagged(clone(untag(value)), name)

    def load(self, path):
        path = Path(path).resolve()
        if path in self.loading:
            raise Unsupported(f"Cyclic local imports at {path}")
        if path not in self.modules:
            self.loading.add(path)
            try:
                if path.suffix == ".json":
                    from .partstudio import load_snapshot

                    env = Env(self.base, module=True)
                    symbols = load_snapshot(path, self.sources)
                    for name, value in symbols.items():
                        env.define(name, value, True)
                    self.modules[path] = Module(self, env, set(symbols))
                else:
                    self.modules[path] = self.load_source(path.read_text(), str(path))
            finally:
                self.loading.remove(path)
        return self.modules[path]

    def load_source(self, source, filename="<source>"):
        nodes = parse(source, filename)
        env = Env(self.base, module=True)
        exports = set()
        self.sources.append(
            {"path": filename, "sha256": hashlib.sha256(source.encode()).hexdigest()}
        )
        # Hoist functions and types, allowing forward calls and mutual recursion.
        for n in nodes:
            if n.kind == "function_decl":
                name, fn = n.args
                if name not in env.slots:
                    env.define(name, Overloads([]), True)
                value = env.get(name)
                if not isinstance(value, Overloads):
                    raise RuntimeErrorFS(f"Conflicting declaration {name}", n.token)
                value.functions.append(Function(fn, env))
                if n.exported:
                    exports.add(name)
            elif n.kind == "enum":
                name, values = n.args
                if name in self.types or name in self.base.slots:
                    raise Unsupported(
                        f"Duplicate type name {name!r}; module-local type identity is not implemented",
                        n.token,
                    )
                self.types[name] = values
                env.define(name, {v: Tagged(v, name) for v in values}, True)
                if n.exported:
                    exports.add(name)
            elif n.kind == "type":
                if n.args[0] in self.types or n.args[0] in self.base.slots:
                    raise Unsupported(
                        f"Duplicate type name {n.args[0]!r}; module-local type identity is not implemented",
                        n.token,
                    )
                self.types[n.args[0]] = n.args[1]
        for n in nodes:
            if n.kind == "import":
                ns, fields = n.args
                fields = {k: self.eval(v, env) for k, v in fields.items()}
                path, version = fields.get("path"), fields.get("version")
                if not isinstance(path, str) or not isinstance(version, str):
                    raise RuntimeErrorFS("Imports need string path and version", n.token)
                if path.startswith("onshape/std/"):
                    supported = {
                        "common",
                        "geometry",
                        "math",
                        "vector",
                        "units",
                        "query",
                        "primitives",
                        "sketch",
                        "feature",
                        "containers",
                        "valueBounds",
                        "evaluate",
                        "boolean",
                        "transform",
                        "plane",
                        "topologyUtils",
                        "instantiator",
                    }
                    if Path(path).stem not in supported:
                        raise Unsupported(
                            f"Standard-library module {path!r} is not implemented", n.token
                        )
                    warning = (
                        "Standard-library imports use fsocct's subset, not Onshape version "
                        + version
                    )
                    if warning not in self.warnings:
                        self.warnings.append(warning)
                    symbols = {k: slot.value for k, slot in self.base.slots.items()}
                else:
                    target = self.imports.get(path + "@" + version, self.imports.get(path))
                    if target is None and path.startswith(("./", "../")):
                        target = Path(filename).parent / path
                    if target is None:
                        raise Unsupported(
                            f"Import {path!r} version {version!r} needs a local --imports mapping",
                            n.token,
                        )
                    mod = self.load(target)
                    symbols = {name: mod.env.get(name) for name in mod.exports}
                for k, value in symbols.items():
                    name = f"{ns}::{k}" if ns else k
                    if path.startswith("onshape/std/") and ns is None:
                        if n.exported:
                            exports.add(name)
                        continue
                    if name in env.slots:
                        raise Unsupported(f"Import conflicts with symbol {name!r}", n.token)
                    env.define(name, value, True)
                    if n.exported:
                        exports.add(name)
            elif n.kind == "declare":
                self.execute(n, env)
                if n.exported:
                    exports.add(n.args[0])
        return Module(self, env, exports)

    def eval(self, n, env):
        self.tick(n.token)
        try:
            return self._eval(n, env)
        except FSError as e:
            if e.token is None:
                e.token = n.token
            raise
        except (ValueError, TypeError, ZeroDivisionError, OverflowError, IndexError, KeyError) as e:
            raise RuntimeErrorFS(str(e), n.token) from e

    def _eval(self, n, env):
        k, a = n.kind, n.args
        if k == "literal":
            return a[0]
        if k == "name":
            return env.get(a[0])
        if k == "array":
            return FSArray(clone(self.eval(x, env)) for x in a[0])
        if k == "map":
            value = {}
            for key, expr in a[0]:
                key, v = self.eval(key, env), self.eval(expr, env)
                check_key(key)
                if v is not None:
                    value[key] = clone(v)
                else:
                    value.pop(key, None)
            return clone(value)
        if k == "box":
            return Box(clone(self.eval(a[0], env)))
        if k == "function":
            return Function(n, env.capture())
        if k == "unary":
            return unary(a[0], self.eval(a[1], env))
        if k == "binary":
            op, left, right = a
            l = self.eval(left, env)
            if op == "&&":
                return boolean(l) and boolean(self.eval(right, env))
            if op == "||":
                return boolean(l) or boolean(self.eval(right, env))
            if op == "??":
                return l if l is not None else self.eval(right, env)
            return binary(op, l, self.eval(right, env))
        if k == "conditional":
            return self.eval(a[1] if boolean(self.eval(a[0], env)) else a[2], env)
        if k == "type_expr":
            value = self.eval(a[1], env)
            return self.is_type(value, a[2]) if a[0] == "is" else self.cast(value, a[2])
        if k == "index":
            v = self.eval(a[0], env)
            if v is None and a[2]:
                return None
            key = self.eval(a[1], env) if a[1] else None
            return index_get(v, key)
        if k == "call":
            fn = self.eval(a[0], env)
            return self.call(fn, [self.eval(x, env) for x in a[1]])
        if k == "try_expr":
            try:
                return self.eval(a[0], env)
            except RuntimeErrorFS:
                return None
        raise Unsupported(f"Unsupported AST expression {k}", n.token)

    def lvalue(self, node, env):
        # Evaluate accessor expressions exactly once, left to right.
        if node.kind == "name":
            return env.find(node.args[0]), []
        if node.kind == "index" and not node.args[2]:
            slot, path = self.lvalue(node.args[0], env)
            key = self.eval(node.args[1], env) if node.args[1] else None
            return slot, path + [key]
        raise RuntimeErrorFS("Assignment needs a variable or container accessor", node.token)

    def assign(self, slot, path, value):
        def updated(current, keys):
            if not keys:
                return clone(value)
            key, *rest = keys
            return index_set(current, key, updated(index_get(current, key), rest))

        current = slot.value
        through_box = False
        for key in path:
            through_box |= isinstance(untag(current), Box) and key is None
            current = index_get(current, key)
        if slot.constant and not through_box:
            raise RuntimeErrorFS("Cannot assign to a constant")
        result = updated(clone(slot.value), path)
        self.require_type(result, slot.constraint)
        slot.value = result

    def execute(self, n, env, predicate=False):
        if n is None:
            return
        self.tick(n.token)
        try:
            self._execute(n, env, predicate)
        except FSError as e:
            if e.token is None:
                e.token = n.token
            raise
        except (ValueError, TypeError, ZeroDivisionError, OverflowError, IndexError, KeyError) as e:
            raise RuntimeErrorFS(str(e), n.token) from e
        except RecursionError as e:
            raise LimitExceeded("Host recursion budget exhausted", n.token) from e

    def _execute(self, n, env, pred):
        k, a = n.kind, n.args
        if k == "block":
            scope = Env(env)
            for child in a[0]:
                self.execute(child, scope, pred)
        elif k == "declare":
            if pred:
                raise Unsupported("Declarations in predicates are not supported", n.token)
            name, constraint, expr, const = a
            value = self.eval(expr, env) if expr else None
            self.require_type(value, constraint)
            env.define(name, value, const, constraint)
        elif k == "assign":
            if pred:
                raise RuntimeErrorFS("Assignment in a predicate")
            lhs, op, rhs = a
            slot, path = self.lvalue(lhs, env)
            old = slot.value
            for key in path:
                old = index_get(old, key)
            if op == "&&=" and not boolean(old) or op == "||=" and boolean(old):
                return
            if op == "??=" and old is not None:
                return
            value = self.eval(rhs, env)
            if op in ("&&=", "||="):
                value = boolean(value)
            elif op not in ("=", "??="):
                value = binary(op[:-1], old, value)
            self.assign(slot, path, value)
        elif k == "expression":
            value = self.eval(a[0], env)
            if pred and not boolean(value):
                raise PredicateFalse()
        elif k == "if":
            self.execute(a[1] if boolean(self.eval(a[0], env)) else a[2], env, pred)
        elif k in ("while", "for"):
            scope = Env(env)
            if k == "for":
                init, cond, step, body = a
                self.execute(init, scope, pred)
            else:
                cond, body = a
                step = None
            while boolean(self.eval(cond, scope)):
                try:
                    self.execute(body, Env(scope), pred)
                except Continue:
                    pass
                except Break:
                    break
                self.execute(step, scope, pred)
        elif k == "for_in":
            names, expr, body, declares = a
            container = clone(untag(self.eval(expr, env)))
            if isinstance(container, dict):
                items = sorted(container.items())
            elif isinstance(container, (list, Vector, Id)):
                items = list(enumerate(container))
            else:
                raise RuntimeErrorFS("for-in needs an array or map")
            for key, value in items:
                scope = Env(env)
                vals = (
                    [key, value]
                    if len(names) == 2
                    else [{"key": key, "value": value}]
                    if isinstance(container, dict)
                    else [value]
                )
                for name, v in zip(names, vals):
                    if declares:
                        scope.define(name, v)
                    else:
                        self.assign(env.find(name), [], v)
                try:
                    self.execute(body, scope, pred)
                except Continue:
                    pass
                except Break:
                    break
        elif k == "return":
            raise Return(clone(self.eval(a[0], env)) if a[0] else None)
        elif k == "break":
            raise Break()
        elif k == "continue":
            raise Continue()
        elif k == "throw":
            val = self.eval(a[0], env) if a[0] else None
            raise RuntimeErrorFS(display(val), n.token, val)
        elif k == "try":
            try:
                self.execute(a[0], env, pred)
            except RuntimeErrorFS as e:
                scope = Env(env)
                if a[1]:
                    scope.define(a[1], e.value)
                self.execute(a[2], scope, pred)
        elif k != "annotation":
            raise Unsupported(f"Unsupported statement {k}", n.token)

    def call(self, fn, args):
        if isinstance(fn, Feature):
            if len(args) != 3 or not isinstance(args[2], dict):
                raise RuntimeErrorFS("A feature needs (context, id, definition)")
            args = [args[0], args[1], {**clone(fn.defaults), **clone(args[2])}]
            fn = fn.function
        if isinstance(fn, Overloads):
            matches = []
            for f in fn.functions:
                params = f.node.args[0]
                if len(params) == len(args) and all(
                    c is None or self.is_type(v, c) for (_, c), v in zip(params, args)
                ):
                    ranks = tuple(
                        0
                        if c is None
                        else 1
                        if c
                        in (
                            "array",
                            "map",
                            "number",
                            "string",
                            "boolean",
                            "builtin",
                            "function",
                            "box",
                        )
                        else 2
                        for _, c in params
                    )
                    matches.append((ranks, f))
            winners = [
                f
                for ranks, f in matches
                if all(
                    all(x >= y for x, y in zip(ranks, other)) and ranks != other
                    for other, g in matches
                    if g is not f
                )
            ]
            if len(winners) != 1:
                raise RuntimeErrorFS("No unique matching function overload")
            fn = winners[0]
        if isinstance(fn, Function):
            params, ret, pre, body, kind = fn.node.args
            if len(args) != len(params):
                raise RuntimeErrorFS(f"Expected {len(params)} arguments, got {len(args)}")
            scope = Env(fn.closure)
            for (name, constraint), value in zip(params, args):
                self.require_type(value, constraint)
                scope.define(name, value, constraint=constraint)
            self.depth += 1
            if self.depth > self.max_depth:
                self.depth -= 1
                raise LimitExceeded(f"Call depth exceeded {self.max_depth}", fn.node.token)
            try:
                try:
                    self.execute(pre, scope, True)
                except PredicateFalse:
                    raise RuntimeErrorFS("Precondition failed", pre.token) from None
                try:
                    self.execute(body, scope, kind == "predicate")
                    value = True if kind == "predicate" else None
                except PredicateFalse:
                    value = False
                except Return as r:
                    value = r.value
                except (Break, Continue):
                    raise RuntimeErrorFS("break/continue outside a loop", fn.node.token) from None
                self.require_type(value, ret)
                return clone(value)
            finally:
                self.depth -= 1
        if callable(fn):
            try:
                return clone(fn(*[clone(a) for a in args]))
            except FSError:
                raise
            except Exception as e:
                raise RuntimeErrorFS(str(e)) from e
        raise RuntimeErrorFS(f"{display(fn)} is not callable")

    def builtins(self):
        from .kernel import bindings

        def feature(fn, defaults=None):
            if not isinstance(fn, Function):
                raise RuntimeErrorFS("defineFeature expects a function")
            return Feature(fn, defaults or {})

        def bound(value, bounds, dims=LENGTH):
            v = scalar(value, dims)
            bounds = untag(bounds)
            if isinstance(bounds, dict):
                if len(bounds) != 1:
                    raise Unsupported("Bounds currently need exactly one unit specification")
                unit, limits = next(iter(bounds.items()))
                factor = scalar(unit, dims)
                if not isinstance(limits, list) or len(limits) != 3:
                    raise RuntimeErrorFS("Bounds need [minimum, default, maximum]")
                low, default, high = [number(x) * factor for x in limits]
                if not low <= default <= high:
                    raise RuntimeErrorFS("Invalid bounds ordering")
                return low <= v <= high
            return bounds[0] <= v <= bounds[1]

        def append(a, v):
            if not isinstance(a, list):
                raise RuntimeErrorFS("append needs an array")
            return FSArray([*a, clone(v)])

        def extrema(op, args):
            vals = args[0] if len(args) == 1 and isinstance(args[0], list) else args
            if not vals:
                raise RuntimeErrorFS("Empty min/max")
            result = vals[0]
            for v in vals[1:]:
                if binary(op, v, result):
                    result = v
            return result

        def size(v):
            if not isinstance(v, (dict, list, Vector, Id, str)):
                raise RuntimeErrorFS("size needs a container")
            return len(v)

        def make_array(n, v=None):
            n = number(n)
            if not math.isfinite(n) or n != int(n) or n < 0:
                raise RuntimeErrorFS("makeArray size must be a non-negative integer")
            if n > self.max_steps:
                raise LimitExceeded("makeArray size exceeds execution budget")
            return [clone(v) for _ in range(int(n))]

        result = dict(UNITS)
        result.update(
            {
                "PI": math.pi,
                "matrix": matrix,
                "inf": math.inf,
                "vector": vector,
                "norm": norm,
                "normalize": normalize,
                "dot": dot,
                "cross": cross,
                "sqrt": lambda x: binary("^", x, 0.5),
                "abs": lambda x: (
                    unary("-", x)
                    if scalar(x, x.dims if isinstance(x, Quantity) else (0, 0)) < 0
                    else x
                ),
                "sin": lambda x: math.sin(scalar(x, ANGLE)),
                "cos": lambda x: math.cos(scalar(x, ANGLE)),
                "tan": lambda x: math.tan(scalar(x, ANGLE)),
                "asin": lambda x: Quantity(math.asin(number(x)), ANGLE),
                "acos": lambda x: Quantity(math.acos(number(x)), ANGLE),
                "atan": lambda x: Quantity(math.atan(number(x)), ANGLE),
                "atan2": lambda y, x: Quantity(math.atan2(number(y), number(x)), ANGLE),
                "floor": lambda x: math.floor(number(x)),
                "ceil": lambda x: math.ceil(number(x)),
                "round": lambda x: math.floor(number(x) + 0.5),
                "exp": lambda x: math.exp(number(x)),
                "log": lambda x: math.log(number(x)),
                "min": lambda *xs: extrema("<", xs),
                "max": lambda *xs: extrema(">", xs),
                "size": size,
                "append": append,
                "concatenateArrays": lambda xs: [clone(v) for a in xs for v in a],
                "makeArray": make_array,
                "keys": lambda d: sorted(d),
                "values": lambda d: [clone(d[k]) for k in sorted(d)],
                "isIn": lambda v, a: any(equal(v, x) for x in a),
                "toString": display,
                "println": lambda v: self.output.append(display(v)),
                "print": lambda v: self.output.append(display(v)),
                "defineFeature": feature,
                "regenError": lambda message, *args: message,
                "isLength": lambda v, b=(-500, 500): bound(v, b),
                "isAngle": lambda v, b=(-math.inf, math.inf): bound(v, b, ANGLE),
                "isInteger": lambda v, b=(-math.inf, math.inf): (
                    float(number(v)).is_integer() and bound(v, b, (0, 0))
                ),
                "isReal": lambda v, b=(-math.inf, math.inf): bound(v, b, (0, 0)),
                "LENGTH_BOUNDS": (-500, 500),
                "POSITIVE_LENGTH_BOUNDS": (1e-8, 500),
                "NONNEGATIVE_LENGTH_BOUNDS": (0, 500),
                "ANGLE_360_BOUNDS": (0, math.tau),
                "INTEGER_BOUNDS": (-1e9, 1e9),
                "POSITIVE_COUNT_BOUNDS": (1, 1e9),
                "ZERO_DEFAULT_TOLERANCE": Quantity(0),
            }
        )
        result.update(bindings())
        return result
