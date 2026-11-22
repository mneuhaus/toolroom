"""Tests fuer fs_lint.py (Onshape-FeatureScript-Vorpruefer).

fs_lint.py lebt bewusst ausserhalb des pruefstand-Pakets
(`toolroom/skills/onshape-cad/scripts/fs_lint.py`), darum wird es hier per
Dateipfad geladen statt importiert. Kein Onshape-/Bridge-Zugriff -- reine
Textanalyse.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

FS_LINT_PATH = Path(__file__).resolve().parents[2] / "skills" / "onshape-cad" / "scripts" / "fs_lint.py"

spec = importlib.util.spec_from_file_location("fs_lint", FS_LINT_PATH)
fs_lint = importlib.util.module_from_spec(spec)
sys.modules["fs_lint"] = fs_lint  # dataclass() needs the module registered to resolve type hints
spec.loader.exec_module(fs_lint)

REAL_FILES_ROOT = Path("/Users/mneuhaus/Workspace/cad/step-feeder")

CORE_FS = REAL_FILES_ROOT / "single-step-r10" / "native" / "core.fs"
R6D_FS = REAL_FILES_ROOT / "rocking-photo-tray-r6d" / "native" / "r6d.fs"
DIRECT_DROP_FS = REAL_FILES_ROOT / "single-step-r10" / "designs" / "direct-drop" / "direct-drop.fs"
R10B_FS = REAL_FILES_ROOT / "single-step-r10" / "jobs" / "r10b" / "r10b.fs"


def lint(src: str):
    return fs_lint.lint_source("<test>", src)


def by_rule(findings, rule_id):
    return [f for f in findings if f.rule_id == rule_id]


HEADER_OK = 'FeatureScript 3044;\nimport(path:"onshape/std/geometry.fs",version:"3044.0");\n'


def wrap_feature(body: str, header: str = HEADER_OK) -> str:
    return (
        header
        + 'annotation {"Feature Type Name":"Test"}\n'
        + "export const testFeature=defineFeature(function(context is Context,id is Id,"
        + "definition is map) precondition {} {\n"
        + body
        + "\n});\n"
    )


# ---------------------------------------------------------------------
# FS001 -- header / import version consistency
# ---------------------------------------------------------------------

def test_fs001_mismatched_std_import_version_flagged():
    src = 'FeatureScript 3044;\nimport(path:"onshape/std/geometry.fs",version:"2909.0");\n'
    findings = by_rule(lint(src), "FS001")
    assert len(findings) == 1
    assert "2909.0" in findings[0].message


def test_fs001_matching_versions_clean():
    src = HEADER_OK
    assert by_rule(lint(src), "FS001") == []


def test_fs001_missing_header_is_error():
    findings = by_rule(lint("import(path:\"onshape/std/geometry.fs\",version:\"3044.0\");\n"), "FS001")
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"


# ---------------------------------------------------------------------
# FS002 -- duplicate op-id within a body
# ---------------------------------------------------------------------

def test_fs002_duplicate_id_in_same_feature_flagged():
    src = wrap_feature('opExtrude(context, id + "cut", {});\nopExtrude(context, id + "cut", {});')
    findings = by_rule(lint(src), "FS002")
    assert len(findings) == 1
    assert "cut" in findings[0].message


def test_fs002_distinct_ids_are_clean():
    src = wrap_feature('opExtrude(context, id + "cut1", {});\nopExtrude(context, id + "cut2", {});')
    assert by_rule(lint(src), "FS002") == []


def test_fs002_same_suffix_in_different_helper_functions_is_not_duplicate():
    # A helper's `id` argument is unique per call site, so reusing "a"/"b"
    # inside two independent helper bodies must not be flagged.
    src = (
        HEADER_OK
        + 'function helperOne(context is Context, id is Id) { opExtrude(context, id + "a", {}); }\n'
        + 'function helperTwo(context is Context, id is Id) { opExtrude(context, id + "a", {}); }\n'
    )
    assert by_rule(lint(src), "FS002") == []


# ---------------------------------------------------------------------
# FS003 -- loop id without index
# ---------------------------------------------------------------------

def test_fs003_loop_without_index_flagged():
    src = wrap_feature('for (var i in range) {\n  opExtrude(context, id + "hole", {});\n}')
    findings = by_rule(lint(src), "FS003")
    assert len(findings) == 1
    assert findings[0].severity == "WARN"


def test_fs003_loop_with_index_concatenation_is_clean():
    src = wrap_feature('for (var i in range) {\n  opExtrude(context, id + ("hole" ~ i), {});\n}')
    assert by_rule(lint(src), "FS003") == []


# ---------------------------------------------------------------------
# FS004 -- bare numeric literal in a length-vector call
# ---------------------------------------------------------------------

def test_fs004_bare_number_vector_in_opTranslate_flagged():
    src = wrap_feature('opTranslate(context, id + "t", {"vector": vector(10, 20, 30)});')
    findings = by_rule(lint(src), "FS004")
    assert len(findings) == 1


def test_fs004_unit_scaled_vector_is_clean():
    src = wrap_feature('opTranslate(context, id + "t", {"vector": vector(10, 20, 30) * millimeter});')
    assert by_rule(lint(src), "FS004") == []


def test_fs004_direction_vector_of_zeros_and_ones_is_clean():
    src = wrap_feature('opTranslate(context, id + "t", {"direction": vector(0, 0, 1)});')
    assert by_rule(lint(src), "FS004") == []


# ---------------------------------------------------------------------
# FS005 -- inverted min/max in a local box/block helper
# ---------------------------------------------------------------------

def test_fs005_inverted_corners_in_local_box_helper_flagged():
    src = (
        HEADER_OK
        + 'function box(context is Context, id is Id, a is Vector, b is Vector) { }\n'
        + wrap_feature('box(context, id + "b", vector(10, 0, 0), vector(-5, 10, 10));')
    )
    findings = by_rule(lint(src), "FS005")
    assert len(findings) == 1


def test_fs005_ordered_corners_are_clean():
    src = (
        HEADER_OK
        + 'function box(context is Context, id is Id, a is Vector, b is Vector) { }\n'
        + wrap_feature('box(context, id + "b", vector(-5, 0, 0), vector(10, 10, 10));')
    )
    assert by_rule(lint(src), "FS005") == []


def test_fs005_std_block_not_locally_defined_is_ignored():
    # No local `function box(...)` in this source -> std block(), not our helper.
    src = wrap_feature('block(context, id + "b", vector(10, 0, 0), vector(-5, 10, 10));')
    assert by_rule(lint(src), "FS005") == []


# ---------------------------------------------------------------------
# FS006 -- non-normalized plane normal/x-axis
# ---------------------------------------------------------------------

def test_fs006_non_unit_normal_flagged():
    src = wrap_feature('var p = plane(vector(0, 0, 0), vector(0, 0, 2), vector(1, 0, 0));')
    findings = by_rule(lint(src), "FS006")
    assert len(findings) == 1


def test_fs006_unit_normal_is_clean():
    src = wrap_feature('var p = plane(vector(0, 0, 0), vector(0, 0, 1), vector(1, 0, 0));')
    assert by_rule(lint(src), "FS006") == []


# ---------------------------------------------------------------------
# FS007 -- stale query reused after opBoolean
# ---------------------------------------------------------------------

def test_fs007_reuse_without_requery_flagged():
    src = wrap_feature(
        'opBoolean(context, id + "op", {"targets": body, "tools": tool});\n'
        'opExtrude(context, id + "next", {"entities": body});'
    )
    findings = by_rule(lint(src), "FS007")
    assert len(findings) == 1


def test_fs007_requery_before_reuse_is_clean():
    src = wrap_feature(
        'opBoolean(context, id + "op", {"targets": body, "tools": tool});\n'
        'body = qCreatedBy(id + "op", EntityType.BODY);\n'
        'opExtrude(context, id + "next", {"entities": body});'
    )
    assert by_rule(lint(src), "FS007") == []


# ---------------------------------------------------------------------
# FS008 -- rib() call review (INFO only)
# ---------------------------------------------------------------------

def test_fs008_rib_call_flagged_as_info():
    src = wrap_feature('rib(context, id + "r", {});')
    findings = by_rule(lint(src), "FS008")
    assert len(findings) == 1
    assert findings[0].severity == "INFO"


def test_fs008_no_rib_call_is_clean():
    src = wrap_feature('opExtrude(context, id + "e", {});')
    assert by_rule(lint(src), "FS008") == []


# ---------------------------------------------------------------------
# FS009 -- empty tools query in opBoolean
# ---------------------------------------------------------------------

def test_fs009_empty_array_tools_flagged():
    src = wrap_feature('opBoolean(context, id + "op", {"targets": body, "tools": []});')
    findings = by_rule(lint(src), "FS009")
    assert len(findings) == 1


def test_fs009_empty_qunion_tools_flagged():
    src = wrap_feature('opBoolean(context, id + "op", {"targets": body, "tools": qUnion([])});')
    findings = by_rule(lint(src), "FS009")
    assert len(findings) == 1


def test_fs009_nonempty_tools_is_clean():
    src = wrap_feature('opBoolean(context, id + "op", {"targets": body, "tools": tool});')
    assert by_rule(lint(src), "FS009") == []


# ---------------------------------------------------------------------
# FS010 -- opExtrude without endBound
# ---------------------------------------------------------------------

def test_fs010_missing_endbound_flagged():
    src = wrap_feature('opExtrude(context, id + "e", {"entities": region});')
    findings = by_rule(lint(src), "FS010")
    assert len(findings) == 1


def test_fs010_explicit_endbound_is_clean():
    src = wrap_feature(
        'opExtrude(context, id + "e", {"entities": region, "endBound": BoundingType.BLIND});'
    )
    assert by_rule(lint(src), "FS010") == []


# ---------------------------------------------------------------------
# FS011 -- defineFeature / annotation structure
# ---------------------------------------------------------------------

def test_fs011_missing_annotation_flagged():
    src = (
        HEADER_OK
        + "export const testFeature=defineFeature(function(context is Context,id is Id,"
        + "definition is map) precondition {} {\nopExtrude(context, id + \"e\", {});\n});\n"
    )
    findings = by_rule(lint(src), "FS011")
    assert len(findings) == 1


def test_fs011_with_annotation_is_clean():
    src = wrap_feature('opExtrude(context, id + "e", {});')
    assert by_rule(lint(src), "FS011") == []


def test_fs011_library_without_definefeature_is_valid():
    assert by_rule(lint(HEADER_OK + "export function helper() {}"), "FS011") == []


# ---------------------------------------------------------------------
# FS012 -- unbalanced brackets
# ---------------------------------------------------------------------

def test_fs012_unclosed_paren_flagged():
    src = wrap_feature('opExtrude(context, id + "e", {});\nvar x = (1 + 2;')
    findings = by_rule(lint(src), "FS012")
    assert len(findings) == 1


def test_fs012_balanced_source_is_clean():
    src = wrap_feature('opExtrude(context, id + "e", {"a": (1 + 2)});')
    assert by_rule(lint(src), "FS012") == []


def test_fs012_string_containing_bracket_does_not_confuse_balance():
    src = wrap_feature('var s = "unbalanced ( paren in a string";\nopExtrude(context, id + "e", {});')
    assert by_rule(lint(src), "FS012") == []


# ---------------------------------------------------------------------
# FS013 -- tabs and smart quotes
# ---------------------------------------------------------------------

def test_fs013_tab_indentation_flagged_as_warn():
    src = wrap_feature('\topExtrude(context, id + "e", {});')
    findings = by_rule(lint(src), "FS013")
    warns = [f for f in findings if f.severity == "WARN"]
    assert len(warns) == 1


def test_fs013_smart_quote_outside_string_flagged_as_error():
    src = wrap_feature('var s = “oops”;')
    findings = by_rule(lint(src), "FS013")
    errors = [f for f in findings if f.severity == "ERROR"]
    assert len(errors) >= 1


def test_fs013_clean_ascii_source_has_no_findings():
    src = wrap_feature('opExtrude(context, id + "e", {});')
    assert by_rule(lint(src), "FS013") == []


# ---------------------------------------------------------------------
# FS014 -- size / op-count budget
# ---------------------------------------------------------------------

def test_fs014_large_op_count_flagged():
    body = "\n".join(f'opExtrude(context, id + "e{i}", {{}});' for i in range(5001))
    src = wrap_feature(body)
    findings = by_rule(lint(src), "FS014")
    assert any("Operationsaufrufe" in f.message for f in findings)


def test_fs014_small_file_is_clean():
    src = wrap_feature('opExtrude(context, id + "e", {});')
    assert by_rule(lint(src), "FS014") == []


# ---------------------------------------------------------------------
# FS015 -- unknown function call
# ---------------------------------------------------------------------

def test_fs015_unknown_function_flagged():
    src = wrap_feature('totallyMadeUpHelper(context, id + "x", {});')
    findings = by_rule(lint(src), "FS015")
    assert len(findings) == 1
    assert "totallyMadeUpHelper" in findings[0].message


def test_fs015_known_std_function_is_clean():
    src = wrap_feature('opExtrude(context, id + "e", {});')
    assert by_rule(lint(src), "FS015") == []


def test_fs015_locally_defined_function_is_clean():
    src = (
        HEADER_OK
        + 'function myHelper(context is Context, id is Id) { }\n'
        + wrap_feature('myHelper(context, id + "x");')
    )
    assert by_rule(lint(src), "FS015") == []


def test_fs015_namespaced_call_is_not_flagged():
    src = wrap_feature('Frame::attach(context, id + "x", {});')
    assert by_rule(lint(src), "FS015") == []


# ---------------------------------------------------------------------
# Real project files: known-good sources must compile clean of ERROR;
# a file "in progress" is only reported, not asserted clean.
# ---------------------------------------------------------------------

REAL_GOOD_FILES = [CORE_FS, R6D_FS, DIRECT_DROP_FS]


@pytest.mark.parametrize("path", REAL_GOOD_FILES, ids=lambda p: p.name)
def test_real_compiled_file_has_zero_errors(path):
    if not path.exists():
        pytest.skip(f"Beispieldatei nicht vorhanden: {path}")
    findings = fs_lint.lint_file(path)
    errors = [f for f in findings if f.severity == "ERROR"]
    assert errors == [], "\n".join(f.format() for f in errors)


def test_real_in_progress_file_runs_without_crashing():
    if not R10B_FS.exists():
        pytest.skip(f"Beispieldatei nicht vorhanden: {R10B_FS}")
    findings = fs_lint.lint_file(R10B_FS)
    assert isinstance(findings, list)


# ---------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------

def test_cli_exit_code_2_on_error(tmp_path):
    f = tmp_path / "broken.fs"
    f.write_text('FeatureScript 3044;\nvar x = (1 + 2;\n')
    result = subprocess.run(
        [sys.executable, str(FS_LINT_PATH), str(f)],
        capture_output=True, text=True,
    )
    assert result.returncode == 2


def test_cli_exit_code_0_on_clean_file(tmp_path):
    f = tmp_path / "clean.fs"
    f.write_text(wrap_feature('opExtrude(context, id + "e", {"entities": region, "endBound": BoundingType.BLIND});'))
    result = subprocess.run(
        [sys.executable, str(FS_LINT_PATH), str(f)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_cli_rules_flag_lists_all_registered_rules():
    result = subprocess.run(
        [sys.executable, str(FS_LINT_PATH), "--rules"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    for rule_id in ("FS001", "FS005", "FS011", "FS015"):
        assert rule_id in result.stdout


def test_cli_json_output_is_valid_json(tmp_path):
    import json
    f = tmp_path / "clean.fs"
    f.write_text(wrap_feature('opExtrude(context, id + "e", {"entities": region, "endBound": BoundingType.BLIND});'))
    result = subprocess.run(
        [sys.executable, str(FS_LINT_PATH), str(f), "--json"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["findings"] == []

# Lexer/parser regressions: strings, comments, scope and full expressions.
@pytest.mark.parametrize("body", [
    'println("unknownCall( opBoolean( )");',
    '/* opBoolean(context,id+"x",{"tools": []}); */',
    '// totallyMadeUpHelper(context, id);\n',
])
def test_code_inside_strings_and_comments_is_not_executed(body):
    assert not [f for f in lint(wrap_feature(body)) if f.rule_id in {"FS009", "FS015", "FS017"}]


def test_fs001_header_must_be_first_statement():
    assert by_rule(lint('var x=1;\n' + HEADER_OK), "FS001")[0].severity == "ERROR"


def test_fs001_reordered_import_keys_and_comment():
    fs = 'FeatureScript 3044; import(version:"2909.0", /* ) */ path:"onshape/std/geometry.fs");'
    assert by_rule(lint(fs), "FS001")[0].severity == "WARN"


def test_fs002_string_braces_do_not_truncate_body():
    body = 'println("}"); opExtrude(context,id+"x",{}); opExtrude(context,id+"x",{});'
    assert len(by_rule(lint(wrap_feature(body)), "FS002")) == 1


@pytest.mark.parametrize("body", [
    'opExtrude(context,id+"x"+"a",{}); opExtrude(context,id+"x"+"b",{});',
    'opExtrude(context,id+"x",{}); qCreatedBy((id+"x"),EntityType.BODY);',
    'if (a) {opExtrude(context,id+"x",{});} else {opExtrude(context,id+"x",{});}',
])
def test_fs002_noncolliding_id_expressions(body):
    assert by_rule(lint(wrap_feature(body)), "FS002") == []


def test_fs002_assigned_anonymous_helper():
    src = HEADER_OK + 'const make=function(c is Context,id is Id){opExtrude(c,id+"x",{});opExtrude(c,id+"x",{});};'
    assert len(by_rule(lint(src), "FS002")) == 1


def test_fs003_size_loop_and_while_are_parsed():
    for header in ('for(var i=0;i<size(xs);i+=1)', 'while (condition())'):
        src = wrap_feature(header + '{opExtrude(context,id+"hole",{});}')
        assert len(by_rule(lint(src), "FS003")) == 1


def test_fs003_dynamic_ids_and_readonly_queries_are_clean():
    src = wrap_feature('for(var i=0;i<size(xs);i+=1){opExtrude(context,id+"x"+i,{});qCreatedBy(id+"base",EntityType.BODY);}')
    assert by_rule(lint(src), "FS003") == []


@pytest.mark.parametrize("expression, expected", [
    ('transform(vector(1,1,1))', True),
    ('transform((ROT*vector(0,0,-3.2))*millimeter)', False),
    ('transform(vector(10,20,30)*millimeter /* vector(5,6,7) */)', False),
    ('transform(matrix([[1,0,0],[0,1,0],[0,0,1]]), vector(3,4,5))', True),
])
def test_fs004_transform_translation_units(expression, expected):
    assert bool(by_rule(lint(wrap_feature(expression+';')), "FS004")) == expected


def test_fs005_degenerate_corner_is_advisory():
    src = HEADER_OK + 'function box(c is Context,id is Id,a is Vector,b is Vector){}\n' + wrap_feature('box(context,id+"b",vector(0,0,0),vector(0,10,10));')
    assert by_rule(lint(src), "FS005")[0].severity == "WARN"


@pytest.mark.parametrize("expression, expected", [
    ('plane(vector(0,0,0)*millimeter,vector(0,0,2))', True),
    ('plane(vector(0,0,0)*millimeter,vector(0,0,2)/2)', False),
    ('plane(vector(0,0,0)*millimeter,vector(.1,.1,.1))', True),
    ('opPlane(context,id+"p",{"plane":plane(vector(0,0,0)*millimeter,vector(0,0,1))})', False),
])
def test_fs006_two_argument_and_opplane(expression, expected):
    assert bool(by_rule(lint(wrap_feature(expression+';')), "FS006")) == expected


def test_fs007_scope_and_any_reassignment():
    src = HEADER_OK + 'function a(c is Context,id is Id,b is Query){opBoolean(c,id+"x",{"targets":b,"tools":t});}\nfunction other(b is Query){return b;}'
    assert by_rule(lint(src), "FS007") == []
    src = wrap_feature('opBoolean(context,id+"b",{"tools":tool}); tool=qNothing(); println(tool);')
    assert by_rule(lint(src), "FS007") == []


def test_fs007_keep_tools_and_strings():
    src = wrap_feature('opBoolean(context,id+"b",{"tools":tool,"keepTools":true}); println(tool); println("tool");')
    assert by_rule(lint(src), "FS007") == []


def test_fs009_qnothing():
    assert by_rule(lint(wrap_feature('opBoolean(context,id+"b",{"tools":qNothing()});')), "FS009")


def test_fs010_endbound_id_string_does_not_supply_map_key():
    assert by_rule(lint(wrap_feature('opExtrude(context,"endBound",{});')), "FS010")


def test_fs010_computed_map_is_unknown_not_missing():
    assert by_rule(lint(wrap_feature('opExtrude(context,id+"e",options);')), "FS010") == []


def test_fs011_parameter_names_do_not_matter():
    src = HEADER_OK+'annotation {"Feature Type Name":"A"} export const f=defineFeature(function(c is Context,i is Id,d is map) precondition {} {});'
    assert by_rule(lint(src), "FS011") == []


def test_fs011_unrelated_annotation_after_feature_cannot_hide_error():
    src = HEADER_OK+'export const f=defineFeature(function(c is Context,i is Id,d is map) precondition {} {}); annotation {"Feature Type Name":"A"}'
    assert by_rule(lint(src), "FS011")


@pytest.mark.parametrize("tail", ['var x="unfinished', '/* unfinished'])
def test_fs012_unterminated_lexemes(tail):
    assert by_rule(lint(HEADER_OK+tail), "FS012")[0].severity == "ERROR"


def test_fs012_escaped_quote_and_backslash_are_balanced():
    assert by_rule(lint(wrap_feature(r'println("quote: \" slash: \\");')), "FS012") == []


def test_fs013_tabs_inside_string_or_comment_are_not_indentation():
    assert by_rule(lint(wrap_feature('println("a\tb"); // \t\n')), "FS013") == []


def test_fs015_string_cannot_declare_function():
    src = wrap_feature('println("function bogus("); bogus();')
    assert any('bogus' in f.message for f in by_rule(lint(src), "FS015"))


def test_fs015_anonymous_local_function_and_member_call():
    assert by_rule(lint(wrap_feature('const f=function(x){return x;}; f(1); obj.callback(2);')), "FS015") == []


# Semantic rules: positive and negative cases, one independently named test
# per rule for stable lesson references.
def test_fs016_helper_id_namespace():
    helper = HEADER_OK+'function h(c is Context,id is Id) {opExtrude(c,id+"x",{});}'
    assert by_rule(lint(helper+wrap_feature('h(context,id);h(context,id);')), "FS016")
    assert by_rule(lint(helper+wrap_feature('h(context,id+"a");h(context,id+"b");')), "FS016") == []


@pytest.mark.parametrize("operation, severity", [('SUBTRACTION','ERROR'), ('UNION','WARN')])
def test_fs017_same_boolean_query(operation, severity):
    src = wrap_feature('opBoolean(context,id+"b",{"targets":qUnion([a,b]),"tools":qUnion([a, b]),"operationType":BooleanOperationType.'+operation+'});')
    assert by_rule(lint(src), "FS017")[0].severity == severity
    assert by_rule(lint(src.replace('"tools":qUnion([a, b])','"tools":c')), "FS017") == []


def test_fs017_string_whitespace_is_significant():
    src = wrap_feature('opBoolean(context,id+"b",{"targets":qCreatedBy(id+"a b",EntityType.BODY),"tools":qCreatedBy(id+"ab",EntityType.BODY),"operationType":BooleanOperationType.SUBTRACTION});')
    assert by_rule(lint(src), "FS017") == []


def test_fs018_deleted_query_reuse():
    body = 'opDeleteBodies(context,id+"del",{"entities":b}); '
    assert by_rule(lint(wrap_feature(body+'println(b);')), "FS018")
    assert by_rule(lint(wrap_feature(body+'b=qNothing(); println(b);')), "FS018") == []
    assert by_rule(lint(wrap_feature(body+'println("b");')), "FS018") == []


def test_fs019_unknown_creation_id():
    src = wrap_feature('opExtrude(context,id+"x",{}); qCreatedBy(id+"typo",EntityType.BODY);')
    assert by_rule(lint(src), "FS019")
    assert by_rule(lint(src.replace('"typo"','"x"')), "FS019") == []
    assert by_rule(lint(wrap_feature('qCreatedBy(dynamicId,EntityType.BODY);')), "FS019") == []


def test_fs020_optional_entity_type():
    assert by_rule(lint(wrap_feature('qCreatedBy(id);')), "FS020")[0].severity == "INFO"
    assert by_rule(lint(wrap_feature('qCreatedBy(id,EntityType.BODY);')), "FS020") == []


@pytest.mark.parametrize("body, expected", [
    ('opLoft(context,id+"x",{"profileSubqueries":[a]});', True),
    ('opLoft(context,id+"x",{"profileSubqueries":[qUnion([a,b]),qUnion([c,d])]});', False),
    ('opLoft(context,id+"x",{"profileSubqueries":profiles});', False),
    ('opSweep(context,id+"x",{"profiles":qNothing(),"path":path});', True),
    ('opSweep(context,id+"x",{"profiles":profile,"path":path});', False),
    ('opSweep(context,id+"x",{"profiles":profile});', True),
    ('opSweep(context,id+"x",{"profiles":profile,"path":qNothing()});', True),
])
def test_fs021_profiles_and_path(body, expected):
    assert bool(by_rule(lint(wrap_feature(body)), "FS021")) == expected


def test_fs022_precondition_units():
    src = wrap_feature('const offset=definition.width*millimeter;').replace('precondition {}','precondition {annotation {"Name":"Width"} isLength(definition.width,LENGTH_BOUNDS);}')
    assert by_rule(lint(src), "FS022")
    assert by_rule(lint(src.replace('definition.width*millimeter','definition.width')), "FS022") == []


def test_fs023_parameter_annotation():
    src = wrap_feature('').replace('precondition {}','precondition {isAngle(definition.angle,ANGLE_BOUNDS);}')
    assert by_rule(lint(src), "FS023")
    assert by_rule(lint(src.replace('isAngle(', 'annotation {"Name":"Angle"} isAngle(')), "FS023") == []


@pytest.mark.parametrize("argument, expected", [('""', True), ('"   "', True), ('', True), ('"Cannot create body"', False), ('ErrorStringEnum.INVALID_INPUT', False)])
def test_fs024_regenerror_strings(argument, expected):
    assert bool(by_rule(lint(wrap_feature('throw regenError('+argument+');')), "FS024")) == expected


def test_fs025_catch_without_rethrow():
    src=wrap_feature('try {opExtrude(context,id+"x",{});} catch (e) {println(e);}')
    assert by_rule(lint(src), "FS025")
    assert by_rule(lint(src.replace('println(e);','throw e;')), "FS025") == []


def test_fs026_size_loop_bounds():
    src=wrap_feature('for(var i=0;i<=size(xs);i+=1){println(xs[i]);}')
    assert by_rule(lint(src), "FS026")
    assert by_rule(lint(src.replace('i<=size','i<size')), "FS026") == []


def test_fs027_unused_local_variable():
    assert by_rule(lint(wrap_feature('const unused=1;')), "FS027")[0].severity == "INFO"
    assert by_rule(lint(wrap_feature('const used=1; println(used);')), "FS027") == []
    assert by_rule(lint(HEADER_OK+'export const GLOBAL=1;'), "FS027") == []


@pytest.mark.parametrize("name", ['yz', 'lb', 'prism'])
def test_fs028_local_helper_arity(name):
    helper=HEADER_OK+f'function {name}(a is number,b is number){{}}'
    assert by_rule(lint(helper+wrap_feature(f'{name}(1);')), "FS028")[0].severity == "ERROR"
    assert by_rule(lint(helper+wrap_feature(f'{name}(1,2);')), "FS028") == []


def test_fs028_overloads_and_nested_commas():
    src=HEADER_OK+'function yz(a){} function yz(a,b){}'+wrap_feature('yz(vector(1,2,3)); yz(1,2); Ns::yz(1,2,3);')
    assert by_rule(lint(src), "FS028") == []


def test_fs029_std_name_collision():
    assert by_rule(lint(HEADER_OK+'function plane(a,b){}'), "FS029")[0].severity == "INFO"
    assert by_rule(lint(HEADER_OK+'function myPlane(a,b){}'), "FS029") == []


def test_fs030_addinstance_raw_ids():
    src=wrap_feature('addInstance(inst,{"documentId":"d","elementId":"e","version":"v"},{});')
    assert by_rule(lint(src), "FS030")
    assert by_rule(lint(wrap_feature('addInstance(inst,Imported::build,{"configuration":{}});')), "FS030") == []
    assert by_rule(lint(wrap_feature('const loadedContext=Imported::build({}); addInstance(inst,partStudioData,{});')), "FS030") == []


def test_cli_json_schema_and_rules_catalog(tmp_path):
    import json
    source=tmp_path/'source.fs'
    source.write_text(wrap_feature('const unused=1;'))
    args=[sys.executable,str(FS_LINT_PATH),str(source),'--json','--strict']
    first=subprocess.run(args,capture_output=True,text=True)
    second=subprocess.run(args,capture_output=True,text=True)
    assert first.returncode == 1
    assert first.stdout == second.stdout
    data=json.loads(first.stdout)
    assert set(data) == {'schema_version','path','counts','findings'}
    assert data['schema_version'] == 1
    assert data['counts'] == {'ERROR':0,'WARN':0,'INFO':1}
    assert set(data['findings'][0]) == {'rule_id','line','severity','message'}
    rules=json.loads(subprocess.run([sys.executable,str(FS_LINT_PATH),'--rules','--json'],capture_output=True,text=True).stdout)
    assert [r['id'] for r in rules['rules']] == [f'FS{i:03}' for i in range(1,33)]
    assert all(set(r)=={'id','severity','lesson'} for r in rules['rules'])


@pytest.mark.parametrize('kind',['missing','directory','invalid_utf8'])
def test_cli_input_failure_still_returns_json(tmp_path, kind):
    import json
    path=tmp_path/'input.fs'
    if kind=='directory': path.mkdir()
    if kind=='invalid_utf8': path.write_bytes(b'\xff')
    result=subprocess.run([sys.executable,str(FS_LINT_PATH),str(path),'--json'],capture_output=True,text=True)
    assert result.returncode==2
    data=json.loads(result.stdout)
    assert data['schema_version']==1
    assert data['error']['kind']=='input_error'
    assert data['findings']==[]


def test_250kb_source_retains_line_numbers_and_completes():
    # No wall-clock threshold in CI: verify scale + positions without flaky timing.
    filler='println("a { [ ( comma, escaped \\\" text");\n'*6000
    src=wrap_feature(filler+'opBoolean(context,id+"b",{"tools":qNothing()});')
    assert len(src.encode())>=250_000
    findings=by_rule(lint(src),'FS009')
    assert len(findings)==1
    assert findings[0].line==src[:src.index('opBoolean')].count('\n')+1


def test_fs003_loop_local_unstable_id_component_is_not_constant():
    src=wrap_feature('for(var x in xs){var sid=id+unstableIdComponent(x); opExtrude(context,sid+"e",{});}')
    assert by_rule(lint(src), "FS003") == []
    assert by_rule(lint(src), "FS015") == []


def test_fs007_query_composition_is_not_a_geometry_read():
    src=wrap_feature('opBoolean(context,id+"b",{"targets":b,"tools":t}); return qUnion([b,qCreatedBy(id+"b",EntityType.BODY)]);')
    assert by_rule(lint(src), "FS007") == []


def test_fs008_declaration_is_not_a_call():
    assert by_rule(lint(HEADER_OK+'function rib(c is Context,id is Id){}'), "FS008") == []


@pytest.mark.parametrize("operation", ["opLoft", "opSweep"])
def test_fs021_empty_map_has_missing_profiles(operation):
    assert by_rule(lint(wrap_feature(operation+'(context,id+"x",{});')), "FS021")


def test_every_rule_has_documented_symptom_cause_and_test_reference():
    lessons=(FS_LINT_PATH.parents[3]/"knowledge"/"onshape"/"featurescript-lessons.md").read_text()
    for rule in fs_lint.RULES:
        section=lessons.split('### '+rule['id']+' -- ',1)[1].split('\n### ',1)[0]
        assert '**Symptom' in section
        assert '**Ursache:**' in section
        assert '**Lint-Regel:**' in section
        assert '**Testreferenz:**' in section


def test_fs016_numeric_second_argument_is_not_an_id():
    helper=HEADER_OK+'function curve(points is array,sign is number,t is number){}'
    src=helper+wrap_feature('curve(points,sign,0);curve(points,sign,1);')
    assert by_rule(lint(src), "FS016") == []


def test_fs003_loop_rebased_string_id_is_dynamic():
    src=wrap_feature('for(var k in ks){var holeId=id+("Mount" ~ k);opExtrude(context,holeId+"Bore",{});}')
    assert by_rule(lint(src), "FS003") == []


def test_fs001_explicit_functions_only_fragment_is_valid():
    src='// Functions-only fragment. Requires common.fs\nfunction helper(){}'
    assert by_rule(lint(src), "FS001") == []


@pytest.mark.parametrize("declarations", [
    'function local(c is Context,id is Id,b is Query){} function local(c is Context,id is Id,b is Query){}',
    'export function buildR10bTray(c is Context,id is Id,definition is map) returns Query {} export function buildR10bTray(context is Context,opId is Id,d is map) returns Query {}',
    'enum R10bEdgeAngle { A, B } enum R10bEdgeAngle { C, D }',
    'const R10B_TRAY_TMAX=1*radian; const R10B_TRAY_TMAX=2*radian;',
    'export const feature=defineFeature(function(c,id,d){}); export const feature=defineFeature(function(c,id,d){});',
    'const name=1; enum name { A }',
    'function local(x){} function local(y){}',
    'function local(x is number) returns number {} function local(y is number) returns Vector {}',
])
def test_fs031_duplicate_studio_definitions(declarations):
    assert len(by_rule(lint(HEADER_OK+declarations), "FS031")) == 1
    assert by_rule(lint(HEADER_OK+declarations), "FS031")[0].severity == "ERROR"


@pytest.mark.parametrize("declarations", [
    'function local(x is number){} function local(x is Vector){}',
    'function local(x){} function local(x,y){}',
    'function a(){var b=1;} function c(){var b=2;}',
    'function a(){if(true){var b=1;}else{var b=2;}}',
    'const a=1; /* const a=2; */ const text="function a(x){}";',
    'enum First { SAME } enum Second { SAME }',
])
def test_fs031_distinct_overloads_and_local_scopes_are_valid(declarations):
    assert by_rule(lint(HEADER_OK+declarations), "FS031") == []


@pytest.mark.parametrize("body", [
    'const box = evBox3d(context, {"topology" : qEverything(EntityType.BODY)});',
    'var box = 1;',
    'for (var box in [1, 2]) {}',
])
def test_fs032_box_as_name_flagged(body):
    result = by_rule(lint(wrap_feature(body)), "FS032")
    assert len(result) == 1 and result[0].severity == "ERROR"


def test_fs032_box_in_other_names_strings_and_comments_is_clean():
    src = wrap_feature('const bounds = evBox3d(context, {"topology" : qEverything(EntityType.BODY)});\n'
                       'const bbox = bounds; // const box = 1\nprintln("var box = 2");')
    assert by_rule(lint(src), "FS032") == []


def test_fs031_duplicate_reports_both_line_numbers():
    src=HEADER_OK+'function helper(x is number){}\nfunction helper(y is number){}'
    result=by_rule(lint(src), "FS031")[0]
    assert result.line == 4
    assert "Zeile 3" in result.message


@pytest.mark.parametrize("name, severity", [('cylinder','WARN'), ('block','WARN'), ('frustum','ERROR'), ('m3HybridTool','ERROR'), ('m3ClearanceTool','ERROR')])
def test_fs028_checks_helper_names_even_with_std_overload(name, severity):
    src=HEADER_OK+f'function {name}(c is Context,id is Id,a,b){{}}'+wrap_feature(f'{name}(context,id+"x",1);')
    assert by_rule(lint(src), "FS028")[0].severity == severity
