"""FeatureScript values. Quantities use SI; only the kernel boundary uses mm."""

import math
from dataclasses import dataclass

from .syntax import FSError, Unsupported


class RuntimeErrorFS(FSError):
    def __init__(self, message, token=None, value=None):
        super().__init__(message, token)
        self.value = message if value is None else value


SCALAR = (0, 0)
LENGTH = (1, 0)
ANGLE = (0, 1)


@dataclass(frozen=True)
class Quantity:
    value: float
    dims: tuple = LENGTH


class Vector(tuple):
    pass


class Matrix(tuple):
    pass


def immutable_mutation(*args, **kwargs):
    raise TypeError(
        "FeatureScript containers are immutable Python values; assign through the evaluator"
    )


class FSArray(list):
    """Persistent value: updates construct a new path; copies share unchanged data."""

    __setitem__ = __delitem__ = append = extend = insert = pop = remove = clear = immutable_mutation
    reverse = sort = __iadd__ = __imul__ = immutable_mutation


class FSMap(dict):
    __setitem__ = __delitem__ = update = setdefault = pop = popitem = clear = immutable_mutation
    __ior__ = immutable_mutation


def matrix(rows):
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], list) or not rows[0]:
        raise RuntimeErrorFS("matrix needs nonempty rectangular rows")
    size = len(rows[0])
    if any(not isinstance(row, list) or len(row) != size for row in rows):
        raise RuntimeErrorFS("Matrix rows must have equal length")
    return Matrix(tuple(number(v) for v in row) for row in rows)


class Id(tuple):
    pass


class UnstableIdComponent(str):
    """Locally unique ID segment; cross-regeneration matching is outside this runtime."""


@dataclass
class Box:
    value: object


@dataclass
class Tagged:
    value: object
    tag: str


def clone(value):
    if isinstance(value, (FSArray, FSMap)):
        return value
    if isinstance(value, Tagged):
        return Tagged(clone(value.value), value.tag)
    if isinstance(value, list):
        return FSArray(clone(v) for v in value)
    if isinstance(value, dict):
        return FSMap({k: clone(v) for k, v in value.items()})
    return value  # Builtins, boxes, immutable vectors/quantities/IDs, functions.


def untag(value):
    return value.value if isinstance(value, Tagged) else value


def number(value):
    if type(value) not in (int, float):
        raise RuntimeErrorFS(f"Expected a dimensionless number, got {display(value)}")
    if math.isnan(value):
        raise RuntimeErrorFS("NaN is not a FeatureScript number")
    return value


def boolean(value):
    if type(value) is not bool:
        raise RuntimeErrorFS("Condition must be boolean (no implicit truth conversion)")
    return value


def scalar(value, dims=SCALAR):
    if dims == SCALAR:
        return number(value)
    if not isinstance(value, Quantity) or value.dims != dims:
        raise RuntimeErrorFS(f"Expected dimensions {dims}, got {display(value)}")
    return value.value


def quantity(value, dims):
    if dims == SCALAR:
        return number(value)
    if not math.isfinite(value):
        raise RuntimeErrorFS("Non-finite quantity")
    return Quantity(value, dims)


def same_dimensions(a, b):
    if isinstance(a, Quantity) and isinstance(b, Quantity) and a.dims == b.dims:
        return a.value, b.value, a.dims
    if not isinstance(a, Quantity) and not isinstance(b, Quantity):
        return number(a), number(b), SCALAR
    raise RuntimeErrorFS("Incompatible units")


def equal(a, b):
    if isinstance(a, Tagged) or isinstance(b, Tagged):
        return (
            isinstance(a, Tagged)
            and isinstance(b, Tagged)
            and a.tag == b.tag
            and equal(a.value, b.value)
        )
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    same_container_kind = (
        isinstance(a, list) and isinstance(b, list) or isinstance(a, dict) and isinstance(b, dict)
    )
    if type(a) is not type(b) and not same_container_kind:
        return False
    if isinstance(a, (list, Vector, Id)):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, Box):
        return a is b
    return a == b


def binary(op, a, b):
    if op in ("==", "!="):
        result = equal(a, b)
        return result if op == "==" else not result
    if op == "~":
        return display(a) + display(b)
    if op == "+" and isinstance(a, Id) and isinstance(b, str):
        return Id((*a, b))
    if hasattr(type(a), "fs_binary"):
        return a.fs_binary(op, b)
    if isinstance(a, Matrix) or isinstance(b, Matrix):
        if isinstance(a, Matrix) and isinstance(b, Vector) and op == "*":
            return Vector(dot(Vector(row), b) for row in a)
        if isinstance(a, Matrix) and isinstance(b, Matrix):
            if op == "*":
                if len(a[0]) != len(b):
                    raise RuntimeErrorFS("Matrix dimensions do not match")
                return Matrix(tuple(dot(Vector(row), Vector(col)) for col in zip(*b)) for row in a)
            if op in ("+", "-") and len(a) == len(b) and len(a[0]) == len(b[0]):
                return Matrix(
                    tuple(binary(op, x, y) for x, y in zip(ra, rb)) for ra, rb in zip(a, b)
                )
            raise RuntimeErrorFS("Invalid matrix arithmetic")
        if op == "*":
            mat, value = (a, b) if isinstance(a, Matrix) else (b, a)
            number(value)
            return Matrix(tuple(binary("*", v, value) for v in row) for row in mat)
        raise Unsupported("Matrix operator is not implemented")
    if isinstance(a, Vector) or isinstance(b, Vector):
        if isinstance(a, Vector) and isinstance(b, Vector):
            if op not in ("+", "-") or len(a) != len(b):
                raise RuntimeErrorFS(
                    "Vector arithmetic needs equal sizes and + or -; use dot/cross"
                )
            return Vector(binary(op, x, y) for x, y in zip(a, b))
        if op not in ("*", "/") or (op == "/" and isinstance(b, Vector)):
            raise RuntimeErrorFS("Invalid scalar/vector operator")
        return (
            Vector(binary(op, x, b) for x in a)
            if isinstance(a, Vector)
            else Vector(binary(op, a, y) for y in b)
        )
    if op in ("<", ">", "<=", ">="):
        x, y, _ = same_dimensions(a, b)
        return {"<": x < y, ">": x > y, "<=": x <= y, ">=": x >= y}[op]
    if op in ("+", "-", "%"):
        x, y, dims = same_dimensions(a, b)
        return quantity({"+": lambda: x + y, "-": lambda: x - y, "%": lambda: x % y}[op](), dims)
    if op in ("*", "/"):
        x, dx = (a.value, a.dims) if isinstance(a, Quantity) else (number(a), SCALAR)
        y, dy = (b.value, b.dims) if isinstance(b, Quantity) else (number(b), SCALAR)
        dims = tuple(i + j if op == "*" else i - j for i, j in zip(dx, dy))
        return quantity(x * y if op == "*" else x / y, dims)
    if op == "^":
        power = number(b)
        x, dims = (a.value, a.dims) if isinstance(a, Quantity) else (number(a), SCALAR)
        value = x**power
        if isinstance(value, complex):
            raise RuntimeErrorFS("Complex numbers are not supported")
        return quantity(value, tuple(d * power for d in dims))
    raise Unsupported(f"Unsupported operator {op}")


def unary(op, value):
    if op == "!":
        return not boolean(value)
    if op in ("-", "+"):
        return binary("*", value, -1 if op == "-" else 1)
    raise Unsupported(f"Unsupported unary operator {op}")


def display(value):
    if value is None:
        return "undefined"
    if type(value) is bool:
        return str(value).lower()
    if type(value) in (int, float):
        return f"{value:g}"
    if isinstance(value, str):
        return value
    if isinstance(value, Id):
        return "/".join(value)
    if isinstance(value, Quantity):
        return f"{value.value:g} SI{value.dims}"
    if isinstance(value, Tagged):
        return display(value.value)
    if isinstance(value, (Vector, list)):
        return "[" + ", ".join(display(x) for x in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {display(v)}" for k, v in value.items()) + "}"
    return f"<{type(value).__name__}>"


def index_get(container, key):
    container = untag(container)
    if isinstance(container, Box) and key is None:
        return container.value
    if isinstance(container, dict):
        check_key(key)
        return container.get(key)
    if isinstance(container, (list, Vector, Id)):
        i = number(key)
        if int(i) != i or i < 0 or i >= len(container):
            raise RuntimeErrorFS(f"Array index {i} out of bounds")
        return container[int(i)]
    fields = getattr(type(container), "fs_fields", ())
    if fields and key in fields:
        return getattr(container, key)
    raise RuntimeErrorFS(f"Cannot index {display(container)}")


def check_key(key):
    # Prevent Python's bool == number and unhashable-key semantics from leaking in.
    if not isinstance(key, (str, Quantity)) and type(key) not in (int, float):
        raise Unsupported("Map keys currently support strings, numbers and unit quantities")


def index_set(container, key, value):
    if isinstance(container, Tagged):
        return Tagged(index_set(container.value, key, value), container.tag)
    if isinstance(container, Box) and key is None:
        container.value = clone(value)
        return container
    if isinstance(container, dict):
        check_key(key)
        container = dict(container)
        if value is None:
            container.pop(key, None)
        else:
            container[key] = clone(value)
        return FSMap(container)
    if isinstance(container, (list, Vector)):
        index_get(container, key)  # Bounds check before writing.
        values = list(container)
        values[int(key)] = clone(value)
        return Vector(values) if isinstance(container, Vector) else FSArray(values)
    raise RuntimeErrorFS("Not a mutable container")


def vector(*args):
    vals = args[0] if len(args) == 1 and isinstance(args[0], list) else args
    if len(vals) not in (2, 3):
        raise RuntimeErrorFS("vector needs two or three components")
    for val in vals:
        same_dimensions(vals[0], val)
    return Vector(vals)


def dot(a, b):
    if not isinstance(a, Vector) or not isinstance(b, Vector) or len(a) != len(b):
        raise RuntimeErrorFS("dot needs equally sized vectors")
    products = [binary("*", x, y) for x, y in zip(a, b)]
    total = products[0]
    for p in products[1:]:
        total = binary("+", total, p)
    return total


def norm(v):
    return binary("^", dot(v, v), 0.5)


def normalize(v):
    return binary("/", v, norm(v))


def cross(a, b):
    if len(a) != 3 or len(b) != 3:
        raise RuntimeErrorFS("cross needs 3D vectors")
    return Vector(
        binary("-", binary("*", a[i], b[j]), binary("*", a[j], b[i]))
        for i, j in ((1, 2), (2, 0), (0, 1))
    )


UNITS = {
    "unitless": 1,
    "meter": Quantity(1),
    "centimeter": Quantity(0.01),
    "millimeter": Quantity(0.001),
    "inch": Quantity(0.0254),
    "foot": Quantity(0.3048),
    "radian": Quantity(1, ANGLE),
    "degree": Quantity(math.pi / 180, ANGLE),
}
