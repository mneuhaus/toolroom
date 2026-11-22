import math

import pytest

from fsocct.api import expression
from fsocct.runtime import Engine
from fsocct.syntax import FSError, LimitExceeded, Unsupported, parse
from fsocct.values import Quantity, RuntimeErrorFS, Vector


def evaluate(body, *, max_steps=10000):
    return (
        Engine(max_steps=max_steps)
        .load_source("export function test() {" + body + "}")
        .call("test")
    )


@pytest.mark.parametrize(
    "expr, expected",
    [
        ("2 + 3 * 4", 14),
        ("2 ^ 3 ^ 2", 512),
        ("-2 ^ 2", -4),
        ("false && missing()", False),
        ("true || missing()", True),
        ("true ? 7 : missing()", 7),
        ("undefined ?? 5", 5),
        ("(2 * inch) / millimeter", 50.8),
        ("sin(90 * degree)", 1),
        ("1 is number", True),
        ("true == 1", False),
        ("vector(1, 2) * 3", Vector((3, 6))),
        ("norm(vector(3, 4) * millimeter) / millimeter", 5),
        ("dot(vector(1, 2, 3), vector(4, 5, 6))", 32),
        ("'a' ~ 2", "a2"),
        ("undefined?.a", None),
        ("{a: 1, b: undefined}.b", None),
        ("-5 % 3", 1),
    ],
)
def test_expressions(expr, expected):
    result = evaluate(f"return {expr};")
    if isinstance(expected, float):
        assert result == pytest.approx(expected)
    else:
        assert result == expected


def test_unitless_bound_maps_and_typed_color():
    assert evaluate("""
        var bounds={ (unitless):[1,4,8] } as IntegerBoundSpec;
        var c=color(0.2,0.4,0.8);
        return [unitless==1,isInteger(4,bounds),isInteger(9,bounds),isInteger(4.5,bounds),c is Color,c.blue];
    """) == [True, True, False, False, True, 0.8]


def test_copies_arguments_and_returns():
    m = Engine().load_source("""
        function mutate(a) { a[0].v = 9; return a; }
        export function test() {
            var a = [{v: 1}]; var b = a; b[0].v = 2;
            var c = mutate(a);
            return [a[0].v, b[0].v, c[0].v];
        }
    """)
    assert m.call("test") == [1, 2, 9]


def test_const_boxes_and_closure_snapshot():
    assert evaluate("""
        const b = new box(0);
        var x = 2;
        const f = function() { b[] += 1; return x; };
        x = 99;
        const y = f(); const z = f();
        return [y, z, b[]];
    """) == [2, 2, 2]


def test_loops_control_flow_and_map_iteration():
    assert evaluate("""
        var n = 0;
        for (var i = 0; i < 10; i += 1) {
            if (i == 3) continue;
            if (i == 5) break;
            n += i;
        }
        var x = [];
        for (var k, v in { b: 2, a: 1 }) x = append(x, k ~ v);
        for (var entry in {a: 4}) n += entry.value;
        while (n < 12) n += 1;
        return [n, x];
    """) == [12, ["a1", "b2"]]


def test_accessor_side_effect_once():
    assert evaluate("""
        const b = new box(0);
        var a = [1];
        const key = function() { b[] += 1; return 0; };
        a[key()] += 10;
        return [a[0], b[]];
    """) == [11, 1]


def test_overloads_predicates_and_return_types():
    m = Engine().load_source("""
        enum Mode { A, B }
        function f(x) { return 0; }
        function f(x is number) returns number { return 1; }
        function f(x is Mode) returns number { return 2; }
        predicate positive(x) { x is number; x > 0; }
        export function test() { return [f(true), f(4), f(Mode.A), positive(1), positive(-2)]; }
    """)
    assert m.call("test") == [0, 1, 2, True, False]


def test_precondition_enforced():
    m = Engine().load_source("""
        export function f(x is number) precondition x > 0; { return x; }
    """)
    with pytest.raises(RuntimeErrorFS, match="Precondition failed"):
        m.call("f", -1)


def test_arrow_functions_pipeline_and_forward_calls():
    m = Engine().load_source("""
        export function test() { return apply(x => x^2, 5)->plus(1); }
        function apply(f is function, x) { return f(x); }
        function plus(x, y) { return x + y; }
    """)
    assert m.call("test") == 26
    assert evaluate("const f = (a is number, b) returns number => a + b; return f(2, 3);") == 5


def test_exceptions_and_undefined():
    assert evaluate("""
        var a = try silent (1 / 0);
        try { throw {message: "problem"}; } catch (e) { return [a, e.message]; }
    """) == [None, "problem"]


@pytest.mark.parametrize(
    "body, message",
    [
        ("return 1 * millimeter + 1;", "Incompatible units"),
        ("if (1) return 1;", "boolean"),
        ("var a = [1]; return a[-1];", "out of bounds"),
        ("var a = [1]; a[1] = 2;", "out of bounds"),
        ("const a = {x: 1}; a.x = 2;", "constant"),
        ("var a is number = 2; a = true;", "Expected number"),
        ("return sqrt(-1);", "Complex"),
        ("return 1 as string;", "Expected string"),
        ("var n = 1; n /= 0;", "division by zero"),
        ("return makeArray(1.5);", "non-negative integer"),
    ],
)
def test_runtime_errors_have_source_locations(body, message):
    with pytest.raises(RuntimeErrorFS, match=message) as e:
        evaluate(body)
    assert "<source>:1:" in str(e.value)


def test_unsupported_cannot_be_swallowed():
    with pytest.raises(Unsupported, match="skConstraint"):
        evaluate("try silent { skConstraint(1); } return 7;")
    with pytest.raises(Unsupported, match="Map keys"):
        evaluate("return {(true): 2};")


def test_limits_cannot_be_swallowed():
    with pytest.raises(LimitExceeded):
        evaluate("try { while (true) {} } catch { return 1; }", max_steps=100)
    e = Engine(max_depth=8)
    m = e.load_source("export function f() { return f(); }")
    with pytest.raises(LimitExceeded, match="depth"):
        m.call("f")


def test_module_exports_and_namespaces(tmp_path):
    (tmp_path / "helper.fs").write_text("export function twice(x) { return x*2; } const secret=9;")
    main = tmp_path / "main.fs"
    main.write_text(
        'h::import(path:"helperTab",version:"v1"); export function test() {return h::twice(3);}'
    )
    engine = Engine(imports={"helperTab@v1": str(tmp_path / "helper.fs")})
    assert engine.load(main).call("test") == 6
    assert len(engine.sources) == 2
    with pytest.raises(Unsupported, match="secret"):
        engine.load(main).env.get("h::secret")


def test_multiple_std_imports_and_parameter_parser():
    Engine().load_source(
        'import(path:"onshape/std/common.fs",version:"3044.0"); import(path:"onshape/std/math.fs",version:"3044.0");'
    )
    assert expression(Engine(), "5 * millimeter") == Quantity(0.005)
    with pytest.raises(FSError):
        expression(Engine(), "1; const extra=2")


def test_unterminated_comment_and_string():
    with pytest.raises(FSError):
        parse('const a = "unterminated;')
    with pytest.raises(FSError):
        parse("/* unterminated")


def test_map_deletion_and_unicode():
    assert evaluate('var a = {one:1}; a.one = undefined; return [size(a), "Grüezi 🌍"];') == [
        0,
        "Grüezi 🌍",
    ]
    assert evaluate("return atan2(1,1) / degree;") == pytest.approx(45)
    assert math.isclose(evaluate("return 2 * PI;"), math.tau)


def test_matrix_rotation_and_dimension_errors():
    assert evaluate("""
        const r=matrix([[0,-1,0],[1,0,0],[0,0,1]]);
        return (r*r)*vector(2,3,4);
    """) == Vector((-2, -3, 4))
    assert evaluate("return matrix([[2,0],[0,3]])*(vector(4,5)*millimeter);") == Vector(
        (Quantity(0.008), Quantity(0.015))
    )
    with pytest.raises(RuntimeErrorFS, match="equal length"):
        evaluate("return matrix([[1],[2,3]]);")
    with pytest.raises(RuntimeErrorFS):
        evaluate("return matrix([[1,2]])*vector(1,2,3);")


def test_annotated_enum_and_unit_bound_spec():
    engine = Engine()
    module = engine.load_source("""
        export enum Mode { annotation {"Name":"First"} A, B }
        export function accepts(v) {
            return isLength(v,{(millimeter):[3,4,6]} as LengthBoundSpec);
        }
    """)
    assert expression(engine, "Mode.A", module.env).tag == "Mode"
    assert module.call("accepts", Quantity(0.004))
    assert not module.call("accepts", Quantity(0.007))


def test_persistent_values_preserve_nested_aliases_and_shared_boxes():
    assert evaluate("""
        var a=[{xs:[1], count:new box(0)}];
        var b=a;
        b[0].xs=append(b[0].xs,2);
        b[0].count[]+=1;
        b=append(b,{xs:[3]});
        return [a[0].xs,b[0].xs,size(a),size(b),a[0].count[]];
    """) == [[1], [1, 2], 1, 2, 1]
