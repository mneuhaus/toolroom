#!/usr/bin/env python3
"""fs_lint.py -- wachsendes Vorpruef-Werkzeug (Linter) fuer Onshape-FeatureScript-Dateien.

Laeuft LOKAL, VOR dem Upload einer .fs-Quelldatei in Onshape. Keine Onshape-/
Bridge-Aufrufe, keine Netzwerkzugriffe. Prueft rein den Quelltext gegen eine
wachsende Liste bekannter Fallen, dokumentiert in
`toolroom/knowledge/onshape/featurescript-lessons.md`.

Aufruf (nur ueber uv, bare python/python3 ist in diesem Repo gesperrt):

    uv run --project /Users/mneuhaus/Workspace/cad/toolroom/pruefstand \
        python /Users/mneuhaus/Workspace/cad/toolroom/skills/onshape-cad/scripts/fs_lint.py \
        <file.fs> [--json] [--strict]

    ... fs_lint.py --rules      # alle Regeln + Lektion auflisten

Exit-Codes:
    0 -- keine ERROR-Befunde; ohne --strict sind WARN/INFO erlaubt
    1 -- nur WARN/INFO-Befunde, und --strict wurde gesetzt
    2 -- mindestens ein ERROR-Befund

### Wie eine neue Regel dazukommt

1. Ein FS-Upload scheitert in Onshape oder ein stiller Fehler faellt auf
   (leere Extrude, doppelte Feature, 0 Teile im Part Studio, ...).
2. Fehlertext/Symptom notieren -> Ursache klaeren (siehe
   `revision-workflow.md`, `field-notes.md`) -> Eintrag in
   `featurescript-lessons.md` ergaenzen: Symptom in Onshape, Ursache,
   Regel-ID.
3. Hier eine kleine reine Funktion `_rule_fsNNN(ctx: LintContext) ->
   list[Finding]` ergaenzen und mit `@rule("FSNNN", severity, "Lektion in
   einem Satz")` dekorieren. Keine globalen Seiteneffekte, keine
   Onshape-Aufrufe -- die Funktion bekommt nur den geparsten Quelltext.
4. In `test_fs_lint.py` mindestens einen positiven (Befund erwartet) und
   einen negativen Testfall (kein Befund) ergaenzen.
5. `--rules` zieht die Regel-Liste automatisch aus dem `@rule`-Registry --
   nichts doppelt pflegen.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Kern-Datentypen
# --------------------------------------------------------------------------

SEVERITY_ORDER = {"ERROR": 2, "WARN": 1, "INFO": 0}


@dataclass
class Finding:
    rule_id: str
    line: int
    severity: str  # ERROR / WARN / INFO
    message: str

    def format(self) -> str:
        return f"{self.severity:5} {self.rule_id:6} L{self.line}: {self.message}"


@dataclass
class StringLit:
    start: int
    end: int
    line: int
    content: str


@dataclass
class LintContext:
    path: str
    source: str
    lines: list  # 1-indexed access via lines[n-1]
    masked_all: str          # strings AND comments blanked (length-preserving)
    masked_comments: str     # only comments blanked, string bodies kept intact
    strings: list            # list[StringLit], in source order
    local_functions: set = field(default_factory=set)
    id_helpers: set = field(default_factory=set)

    line_starts: list[int] = field(default_factory=list)
    pairs: dict[int, int] = field(default_factory=dict)
    calls: list = field(default_factory=list)
    bodies: list = field(default_factory=list)
    brace_depth: list[int] = field(default_factory=list)
    lexical_errors: list = field(default_factory=list)

    def line_at(self, index: int) -> int:
        """1-based line number for a character offset into `source`."""
        return bisect_right(self.line_starts, index)


# --------------------------------------------------------------------------
# Lexing helper: blank out comments and/or string bodies, length-preserving
# so every downstream regex offset still maps back to real line numbers.
# --------------------------------------------------------------------------

def _scan(source: str):
    """Scan source; return masked_all, masked_comments, strings, lexical_errors.

    masked_all      -- comments AND string bodies replaced with spaces
                        (delimiters too); safe for bracket-balance and
                        "does this identifier appear in real code" checks.
    masked_comments -- only comments replaced with spaces; string bodies
                        (and their quotes) are kept verbatim so rules that
                        need the literal text of `id + "suffix"` can read it.
    strings         -- every "..." literal found outside comments, with its
                        span and content, for rules that want to inspect
                        specific string arguments (e.g. import versions).
    """
    n = len(source)
    all_buf = []
    com_buf = []
    strings = []
    lexical_errors = []
    i = 0
    in_string = False
    str_start = 0
    str_line = 1
    str_content = []

    line_starts = [0] + [m.end() for m in re.finditer("\n", source)]

    def cur_line(pos: int) -> int:
        return bisect_right(line_starts, pos)

    while i < n:
        c = source[i]
        if in_string:
            if c == "\\" and i + 1 < n:
                all_buf.append("".join("\n" if ch == "\n" else " " for ch in source[i:i + 2]))
                com_buf.append(source[i:i + 2])
                str_content.append(source[i:i + 2])
                i += 2
                continue
            if c == '"':
                in_string = False
                strings.append(StringLit(str_start, i + 1, str_line, "".join(str_content)))
                all_buf.append(" ")
                com_buf.append('"')
                i += 1
                continue
            all_buf.append(" " if c != "\n" else "\n")
            com_buf.append(c)
            str_content.append(c)
            i += 1
            continue

        if c == "/" and i + 1 < n and source[i + 1] == "/":
            j = i
            while j < n and source[j] != "\n":
                j += 1
            all_buf.append(" " * (j - i))
            com_buf.append(" " * (j - i))
            i = j
            continue

        if c == "/" and i + 1 < n and source[i + 1] == "*":
            j = i + 2
            while j < n and not (source[j] == "*" and j + 1 < n and source[j + 1] == "/"):
                j += 1
            if j >= n:
                lexical_errors.append((i, "Nicht geschlossener Blockkommentar."))
            end = min(j + 2, n)
            chunk = source[i:end]
            blanked = "".join(ch if ch == "\n" else " " for ch in chunk)
            all_buf.append(blanked)
            com_buf.append(blanked)
            i = end
            continue

        if c == '"':
            in_string = True
            str_start = i
            str_line = cur_line(i)
            str_content = ['"']
            all_buf.append(" ")
            com_buf.append('"')
            i += 1
            continue

        all_buf.append(c)
        com_buf.append(c)
        i += 1

    if in_string:
        lexical_errors.append((str_start, "Nicht geschlossener String."))
    return "".join(all_buf), "".join(com_buf), strings, lexical_errors


def _find_matching(text: str, open_pos: int, open_ch: str = "(", close_ch: str = ")") -> int:
    """Given `text[open_pos] == open_ch`, return index of the matching close."""
    depth = 0
    for i in range(open_pos, len(text)):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_top_level(text: str) -> list:
    """Split a comma-separated argument string on top-level commas only."""
    parts = []
    depth = 0
    cur = []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p for p in parts]


def build_context(path: str, source: str) -> LintContext:
    masked_all, masked_comments, strings, lexical_errors = _scan(source)
    lines = source.split("\n")
    ctx = LintContext(
        path=path,
        source=source,
        lines=lines,
        masked_all=masked_all,
        masked_comments=masked_comments,
        strings=strings,
    )
    ctx.local_functions = set(re.findall(r"\bfunction\s+(\w+)\s*\(", masked_all))
    ctx.local_functions.update(re.findall(r"\b(?:const|var)\s+(\w+)\s*=\s*function\s*\(", masked_all))
    ctx.id_helpers = set(re.findall(
        r"\bfunction\s+(\w+)\s*\(\s*\w+\s+is\s+Context\s*,\s*\w+\s+is\s+Id\b",
        masked_all))
    ctx.line_starts = [0] + [m.end() for m in re.finditer("\n", source)]
    ctx.lexical_errors = lexical_errors
    stack = []
    depth = 0
    for pos, ch in enumerate(masked_all):
        ctx.brace_depth.append(depth)
        depth += (ch == "{") - (ch == "}")
        if ch in "([{":
            stack.append((ch, pos))
        elif ch in ")]}":
            if stack and stack[-1][0] == {")": "(", "]": "[", "}": "{"}[ch]:
                _, opening = stack.pop()
                ctx.pairs[opening] = pos
    ctx.brace_depth.append(depth)
    for m in re.finditer(r"(?<![\w:.])([A-Za-z_]\w*)\s*\(", masked_all):
        opening = m.end() - 1
        if opening not in ctx.pairs:
            continue
        # Declarations are not invocations.
        if re.search(r"\bfunction\s*$", masked_all[max(0, m.start()-30):m.start()]):
            continue
        ctx.calls.append(Call(m.group(1), m.start(), opening, ctx.pairs[opening],
                              _argument_spans(masked_all, opening, ctx.pairs[opening], ctx.pairs, masked_comments)))
    ctx.bodies = list(_iter_bodies(ctx))
    return ctx


@dataclass(frozen=True)
class Call:
    name: str
    start: int
    opening: int
    end: int
    args: list[tuple[int, int]]


def _argument_spans(text, opening, end, pairs, content=None):
    """Split using masked delimiters; preserve original expression offsets."""
    spans = []
    start = pos = opening + 1
    while pos < end:
        if pos in pairs:
            pos = pairs[pos] + 1
            continue
        if text[pos] == ",":
            spans.append((start, pos))
            start = pos + 1
        pos += 1
    if (content if content is not None else text)[start:end].strip() or spans:
        spans.append((start, end))
    return spans


def _expr(ctx, span):
    return ctx.masked_comments[span[0]:span[1]].strip()


def _map_fields(ctx, call, index=2):
    """Only inspect literal top-level maps, not strings/nested option maps."""
    if index >= len(call.args):
        return {}
    start, end = call.args[index]
    while start < end and ctx.masked_comments[start].isspace():
        start += 1
    if ctx.masked_all[start:start+1] != "{" or ctx.pairs.get(start, end) >= end:
        return {}
    if ctx.masked_comments[ctx.pairs[start]+1:end].strip():
        return {}  # e.g. mergeMaps/map member expression, not a literal map
    close = ctx.pairs[start]
    fields = {}
    for a, b in _argument_spans(ctx.masked_all, start, close, ctx.pairs):
        m = re.match(r'\s*"([A-Za-z_]\w*)"\s*:', ctx.masked_comments[a:b])
        if m:
            fields[m.group(1)] = (a + m.end(), b)
    return fields


def _scope(ctx, position):
    candidates = [(start, end) for _, start, end in ctx.bodies if start <= position < end]
    return min(candidates, key=lambda span: span[1]-span[0], default=(0, len(ctx.source)))


def _creation_calls(ctx):
    for call in ctx.calls:
        if len(call.args) >= 2 and (call.name.startswith("op") or
                call.name in ctx.id_helpers or call.name in {"newSketch", "newSketchOnPlane"}):
            yield call


def _literal_id(expression):
    # No prefix-only matching: id + "part" + i is a different, dynamic id.
    m = re.fullmatch(r'(\w+)\s*\+\s*("(?:[^"\\]|\\.)*")', expression)
    return (m.group(1), m.group(2)) if m else None


# --------------------------------------------------------------------------
# Rule registry
# --------------------------------------------------------------------------

RULES = []  # list[dict(id, severity, lesson, func)]


def rule(rule_id: str, default_severity: str, lesson: str):
    def deco(func):
        RULES.append({
            "id": rule_id,
            "severity": default_severity,
            "lesson": lesson,
            "func": func,
        })
        return func
    return deco


# --------------------------------------------------------------------------
# FS001 -- header / import version consistency
# --------------------------------------------------------------------------

@rule("FS001", "ERROR",
      'FeatureScript-Kopf als erste Anweisung erforderlich (ERROR); abweichende std-Importversionen pruefen (WARN).')
def _rule_fs001(ctx: LintContext) -> list:
    findings = []
    m = re.match(r"\s*FeatureScript\s+(\d+)\s*;", ctx.masked_all)
    if not m:
        if re.match(r"\s*//\s*Functions-only fragment\b", ctx.source):
            return []
        return [Finding("FS001", 1, "ERROR", "FeatureScript <N>; fehlt als erste Anweisung.")]
    version = int(m.group(1))
    for call in ctx.calls:
        if call.name != "import":
            continue
        fields = {}
        for span in call.args:
            match = re.fullmatch(r'\s*(path|version)\s*:\s*"([^"\\]*)"\s*', _expr(ctx, span))
            if match:
                fields[match.group(1)] = match.group(2)
        if fields.get("path", "").startswith("onshape/std/"):
            imported = fields.get("version", "")
            if re.fullmatch(r"\d+\.\d+", imported) and int(imported.split(".")[0]) != version:
                findings.append(Finding("FS001", ctx.line_at(call.start), "WARN",
                    f"std-import version {imported} weicht vom FeatureScript-Kopf {version} ab; Versionsabsicht pruefen (kein sicherer Compilerfehler)."))
    return findings


# --------------------------------------------------------------------------
# FS002 / FS003 -- op-id hygiene inside a function/feature body
# --------------------------------------------------------------------------

def _iter_bodies(ctx: LintContext):
    """Named functions and anonymous closures, balanced on masked syntax only."""
    for m in re.finditer(r"\bfunction\s*(\w+)?\s*\(", ctx.masked_all):
        opening = m.end() - 1
        close = ctx.pairs.get(opening)
        if close is None:
            continue
        pos = close + 1
        # Return types may occur before the precondition/body.
        ret = re.match(r"\s*(?:returns\s+\w+\s*)?", ctx.masked_all[pos:])
        pos += ret.end()
        pre = re.match(r"precondition\s*\{", ctx.masked_all[pos:])
        if pre:
            brace = pos + pre.end() - 1
            if brace not in ctx.pairs:
                continue
            pos = ctx.pairs[brace] + 1
            while pos < len(ctx.source) and ctx.masked_all[pos].isspace():
                pos += 1
        if ctx.masked_all[pos:pos+1] == "{" and pos in ctx.pairs:
            yield (m.group(1) or "anonymous function", pos + 1, ctx.pairs[pos])


@rule("FS002", "ERROR",
      'Wiederholte vollstaendige literale Erzeuger-Id im geradlinigen Funktionskoerper kollidiert; Query-Lesezugriffe sind erlaubt.')
def _rule_fs002(ctx: LintContext) -> list:
    findings = []
    seen = {}
    for call in _creation_calls(ctx):
        key = _literal_id(_expr(ctx, call.args[1]))
        if key is None:
            continue
        scope = _scope(ctx, call.start)
        # Alternative branches/loops need control-flow analysis; warn elsewhere.
        depth = ctx.brace_depth[call.start] - ctx.brace_depth[scope[0]]
        if depth:
            continue
        scope_key = (scope, key)
        if scope_key in seen:
            findings.append(Finding("FS002", ctx.line_at(call.start), "ERROR",
                f"Doppelte Op-Id `{_expr(ctx, call.args[1])}` (erstes Vorkommen Zeile {seen[scope_key]})."))
        seen[scope_key] = ctx.line_at(call.start)
    return findings


@rule("FS003", "WARN",
      'Konstante Erzeuger-Id in for/while ohne dynamisches Iterationssuffix pruefen; Query-Lesezugriffe sind erlaubt.')
def _rule_fs003(ctx: LintContext) -> list:
    findings = []
    creations = list(_creation_calls(ctx))
    for loop in (call for call in ctx.calls if call.name in {"for", "while"}):
        brace = loop.end + 1
        while brace < len(ctx.source) and ctx.masked_all[brace].isspace():
            brace += 1
        end = ctx.pairs.get(brace)
        if end is None or ctx.masked_all[brace] != "{":
            continue
        for call in creations:
            key = _literal_id(_expr(ctx, call.args[1]))
            if brace < call.start < end and key:
                # Locally rebased IDs are common in generated features. Dynamic
                # suffix analysis remains advisory, not a uniqueness proof.
                assigned = re.search(r"\b(?:var|const)\s+" + re.escape(key[0]) +
                    r"\s*=([^;]+);", ctx.masked_all[brace:call.start])
                if assigned and re.search(r"\bunstableIdComponent\s*\(|~\s*\w+", assigned.group(1)):
                    continue
                findings.append(Finding("FS003", ctx.line_at(call.start), "WARN",
                    f"Konstante Op-Id `{_expr(ctx, call.args[1])}` in Schleife; Iterationssuffix pruefen."))
    return findings


# --------------------------------------------------------------------------
# FS004 -- bare numeric literals fed to geometry calls that expect lengths
# --------------------------------------------------------------------------

_LENGTH_CALL_NAMES = ("block", "cylinder", "opTranslate", "transform")
_BARE_NUMBER_RE = re.compile(r"^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*$")


@rule("FS004", "WARN",
      'Numerische Translationsvektoren brauchen Laengeneinheiten; aeussere Skalierung und lokale Helfer beachten.')
def _rule_fs004(ctx: LintContext) -> list:
    findings = []
    units = r"\b(?:millimeter|centimeter|meter|inch|foot|yard)\b"
    for call in ctx.calls:
        if call.name not in _LENGTH_CALL_NAMES or call.name in ctx.local_functions:
            continue
        if call.name == "transform":
            # transform(translation), transform(matrix, translation); other overloads
            # (coordinate systems / rotations) cannot be inferred statically here.
            spans = call.args[-1:] if len(call.args) in (1, 2) else []
        elif call.name == "opTranslate":
            field = _map_fields(ctx, call).get("vector")
            spans = [field] if field else []
        else:
            spans = call.args
        for start, end in spans:
            text = ctx.masked_all[start:end]
            if re.search(units, text):
                continue  # Outer grouping/matrix products may carry the unit.
            for vm in re.finditer(r"\bvector\s*\(", text):
                opening = start + vm.end() - 1
                close = ctx.pairs.get(opening)
                if close is None:
                    continue
                comps = _split_top_level(ctx.masked_all[opening+1:close])
                if len(comps) < 2 or not all(_BARE_NUMBER_RE.fullmatch(c) for c in comps):
                    continue
                values = [float(c) for c in comps]
                if call.name not in {"transform", "opTranslate"} and all(v in (-1, 0, 1) for v in values):
                    continue
                findings.append(Finding("FS004", ctx.line_at(opening), "WARN",
                    f"vector({', '.join(comps)}) ohne Laengeneinheit als Argument von {call.name}(...)."))
    return findings


# --------------------------------------------------------------------------
# FS005 -- local box/block helper called with inverted min/max corners
# --------------------------------------------------------------------------

@rule("FS005", "WARN",
      'Lokale box/block-Helfer mit vertauschten oder degenerierten literalen Ecken pruefen; unbekannter Helfervertrag ist nur WARN.')
def _rule_fs005(ctx: LintContext) -> list:
    findings = []
    text_all = ctx.masked_all
    for name in ("box", "block"):
        if name not in ctx.local_functions:
            continue  # only check locally-defined helpers, not the std block()
        for m in re.finditer(r"\b" + name + r"\s*\(", text_all):
            open_pos = m.end() - 1
            close_pos = _find_matching(text_all, open_pos, "(", ")")
            if close_pos == -1:
                continue
            args_src = ctx.masked_all[open_pos + 1:close_pos]
            vectors = []
            for vm in re.finditer(r"vector\s*\(", args_src):
                v_open = vm.end() - 1
                v_close = _find_matching(args_src, v_open, "(", ")")
                if v_close == -1:
                    continue
                comps = _split_top_level(args_src[v_open + 1:v_close])
                nums = []
                ok = True
                for c in comps:
                    cm = _BARE_NUMBER_RE.match(c)
                    if not cm:
                        ok = False
                        break
                    nums.append(float(c.strip()))
                if ok and nums:
                    vectors.append((v_open, nums))
            if len(vectors) < 2:
                continue
            (_, a), (v_open_b, b) = vectors[0], vectors[1]
            if len(a) == len(b) and any(x >= y for x, y in zip(a, b)):
                abs_pos = open_pos + 1 + v_open_b
                findings.append(Finding(
                    "FS005", ctx.line_at(abs_pos), "WARN",
                    f"{name}(vector{tuple(a)}, vector{tuple(b)}, ...): erste Ecke hat eine "
                    "Komponente >= zweite Ecke -- min/max vertauscht oder Nullstaerke?"
                ))
    return findings


# --------------------------------------------------------------------------
# FS006 -- normal / axis vectors passed to plane() should be unit length
# --------------------------------------------------------------------------

@rule("FS006", "WARN",
      'Literale plane-Normalen/x-Achsen mit Betrag ausserhalb 1 +/- 0.01 pruefen; zwei und drei Argumente werden erkannt.')
def _rule_fs006(ctx: LintContext) -> list:
    if "plane" in ctx.local_functions:
        return []  # Custom helper contracts are unknown.
    findings = []
    text_all = ctx.masked_all
    for m in re.finditer(r"\bplane\s*\(", text_all):
        open_pos = m.end() - 1
        close_pos = _find_matching(text_all, open_pos, "(", ")")
        if close_pos == -1:
            continue
        args_src = ctx.masked_all[open_pos + 1:close_pos]
        args = _split_top_level(args_src)
        if len(args) not in (2, 3):
            continue
        for idx, label in ((1, "normal"), (2, "x-Achse")):
            if idx >= len(args):
                continue
            arg = args[idx]
            vm = re.match(r"\s*vector\s*\(", arg)
            if not vm:
                continue
            v_open = vm.end() - 1
            v_close = _find_matching(arg, v_open, "(", ")")
            if v_close == -1:
                continue
            if arg[v_close + 1:].strip():
                continue  # e.g. vector(0,0,2)/2 is not a bare numeric vector.
            comps = _split_top_level(arg[v_open + 1:v_close])
            nums = []
            ok = True
            for c in comps:
                cm = _BARE_NUMBER_RE.match(c)
                if not cm:
                    ok = False
                    break
                nums.append(float(c.strip()))
            if not ok or not nums:
                continue
            mag = sum(v * v for v in nums) ** 0.5
            if abs(mag - 1.0) > 0.01:
                abs_pos = open_pos + 1 + sum(len(a) + 1 for a in args[:idx])
                findings.append(Finding(
                    "FS006", ctx.line_at(abs_pos), "WARN",
                    f"plane(...) {label}-Vektor hat Betrag {mag:.6f}, erwartet 1.0 "
                    "(Einheitsvektor)."
                ))
    return findings


# --------------------------------------------------------------------------
# FS007 -- variable reused after an opBoolean without re-resolving the query
# --------------------------------------------------------------------------

@rule("FS007", "WARN",
      'Direkte Geometrie-Nutzung einer Boolean-Query ohne Neuzuweisung pruefen; Query-Komposition und keepTools sind erlaubt.')
def _rule_fs007(ctx: LintContext) -> list:
    findings = []
    for call in ctx.calls:
        if call.name != "opBoolean":
            continue
        fields = _map_fields(ctx, call)
        for key in ("targets", "tools"):
            if key == "tools" and "keepTools" in fields and _expr(ctx, fields["keepTools"]) == "true":
                continue
            span = fields.get(key)
            ident = _expr(ctx, span) if span else ""
            if not re.fullmatch(r"[A-Za-z_]\w*", ident):
                continue
            pos = _use_after(ctx, call, ident)
            if pos is not None:
                findings.append(Finding("FS007", ctx.line_at(pos), "WARN",
                    f"`{ident}` wird nach opBoolean (Zeile {ctx.line_at(call.start)}) gelesen; Query-Gueltigkeit pruefen (Targets koennen erhalten bleiben)."))
    return findings


# --------------------------------------------------------------------------
# FS008 -- calls to a `rib` helper: manual overlap review
# --------------------------------------------------------------------------

@rule("FS008", "INFO",
      'rib-Aufrufe zur manuellen Pruefung von Ueberlapp und Parameterreihenfolge markieren.')
def _rule_fs008(ctx: LintContext) -> list:
    return [Finding("FS008", ctx.line_at(call.start), "INFO",
                    "rib-Helfer: Ueberlapp und Parameterreihenfolge manuell pruefen.")
            for call in ctx.calls if call.name == "rib"]


# --------------------------------------------------------------------------
# FS009 -- opBoolean with an empty tools query
# --------------------------------------------------------------------------

@rule("FS009", "ERROR",
      'opBoolean mit literal leerem tools-Feld ([], qUnion([]), qNothing()) kann nicht arbeiten.')
def _rule_fs009(ctx: LintContext) -> list:
    findings = []
    for call in ctx.calls:
        if call.name != "opBoolean":
            continue
        tools = _map_fields(ctx, call).get("tools")
        if tools and re.fullmatch(r"\[\s*\]|qUnion\s*\(\s*\[\s*\]\s*\)|qNothing\s*\(\s*\)", _expr(ctx, tools)):
            findings.append(Finding("FS009", ctx.line_at(call.start), "ERROR",
                                    "opBoolean(...) hat eine leer-literale `tools`-Query."))
    return findings


# --------------------------------------------------------------------------
# FS010 -- opExtrude without an explicit endBound
# --------------------------------------------------------------------------

@rule("FS010", "WARN",
      'opExtrude mit literaler Optionsmap ohne explizites endBound pruefen; berechnete Maps bleiben unbekannt.')
def _rule_fs010(ctx: LintContext) -> list:
    findings = []
    for call in ctx.calls:
        if call.name == "opExtrude" and len(call.args) == 3:
            fields = _map_fields(ctx, call)
            if _expr(ctx, call.args[2]).startswith("{") and "endBound" not in fields:
                findings.append(Finding("FS010", ctx.line_at(call.start), "WARN",
                                        "opExtrude(...) ohne explizites `endBound`."))
    return findings


# --------------------------------------------------------------------------
# FS011 -- overall feature structure: defineFeature + matching annotation
# --------------------------------------------------------------------------

@rule("FS011", "ERROR",
      'Direkt deklarierte defineFeature-Konstanten brauchen eine zugeordnete Feature Type Name-Annotation; Bibliotheksmodule sind erlaubt.')
def _rule_fs011(ctx: LintContext) -> list:
    findings = []
    for call in ctx.calls:
        if call.name != "defineFeature":
            continue
        prefix = ctx.masked_all[:call.start]
        declaration = re.search(r"(?:export\s+)?const\s+\w+\s*=\s*$", prefix)
        if not declaration:
            continue  # Wrapper/factory expression cannot be associated statically.
        before = prefix[:declaration.start()].rstrip()
        annotation_start = None
        if before.endswith("}"):
            end = len(before)-1
            annotation_start = next((a for a, b in ctx.pairs.items() if b == end and
                                     re.search(r"\bannotation\s*$", ctx.masked_all[:a])), None)
        if annotation_start is None or not re.search(r'"Feature Type Name"\s*:',
                ctx.masked_comments[annotation_start:len(before)]):
            findings.append(Finding("FS011", ctx.line_at(call.start), "ERROR",
                'defineFeature ohne direkt vorausgehende annotation { "Feature Type Name": ... }.'))
    return findings


# --------------------------------------------------------------------------
# FS012 -- balanced delimiters
# --------------------------------------------------------------------------

@rule("FS012", "ERROR",
      'Unpassende Klammern und nicht geschlossene Strings/Blockkommentare verhindern erfolgreiches Parsen.')
def _rule_fs012(ctx: LintContext) -> list:
    if ctx.lexical_errors:
        return [Finding("FS012", ctx.line_at(pos), "ERROR", message)
                for pos, message in ctx.lexical_errors]
    pairs = {")": "(", "}": "{", "]": "["}
    opens = set(pairs.values())
    stack = []
    for i, ch in enumerate(ctx.masked_all):
        if ch in opens:
            stack.append((ch, i))
        elif ch in pairs:
            if not stack or stack[-1][0] != pairs[ch]:
                return [Finding(
                    "FS012", ctx.line_at(i), "ERROR",
                    f"Unpassende schliessende Klammer `{ch}` (kein offenes `{pairs[ch]}` "
                    "davor)."
                )]
            stack.pop()
    if stack:
        ch, pos = stack[-1]
        return [Finding(
            "FS012", ctx.line_at(pos), "ERROR",
            f"Nicht geschlossene Klammer `{ch}` (kein passendes Ende gefunden)."
        )]
    return []


# --------------------------------------------------------------------------
# FS013 -- tabs and stray typographic quotes outside string literals
# --------------------------------------------------------------------------

_SMART_QUOTES = "“”‘’"


@rule("FS013", "WARN",
      'Tabs in Code-Einrueckung sind Stilhinweise (WARN); typografische Anfuehrungszeichen im Code sind ERROR.')
def _rule_fs013(ctx: LintContext) -> list:
    findings = []
    tab_lines = [i + 1 for i, line in enumerate(ctx.masked_all.splitlines())
                 if re.match(r"^[ \t]*\t", line)]
    if tab_lines:
        preview = ", ".join(str(n) for n in tab_lines[:8])
        more = f" (+{len(tab_lines) - 8} weitere)" if len(tab_lines) > 8 else ""
        findings.append(Finding(
            "FS013", tab_lines[0], "WARN",
            f"Tab-Zeichen in {len(tab_lines)} Zeile(n): {preview}{more}."
        ))
    for m in re.finditer(f"[{_SMART_QUOTES}]", ctx.masked_all):
        findings.append(Finding(
            "FS013", ctx.line_at(m.start()), "ERROR",
            f"Typografisches Anfuehrungszeichen `{m.group(0)}` ausserhalb eines "
            "String-Literals -- bricht vermutlich den Parser."
        ))
    return findings


# --------------------------------------------------------------------------
# FS014 -- size / operation-count budget
# --------------------------------------------------------------------------

@rule("FS014", "WARN",
      'Quelltext >200 kB oder >5000 direkte Erzeugeraufrufe sind ein Groessenhinweis, keine gemessene Regenerationsprognose.')
def _rule_fs014(ctx: LintContext) -> list:
    findings = []
    size = len(ctx.source.encode("utf-8"))
    if size > 200_000:
        findings.append(Finding(
            "FS014", 1, "WARN",
            f"Datei ist {size:,} Bytes gross (> 200 kB) -- Regenerationszeit pruefen, "
            "ggf. in Bloecke/separate Feature Studios aufteilen."
        ))
    op_count = sum(1 for _ in _creation_calls(ctx))
    if op_count > 5000:
        findings.append(Finding(
            "FS014", 1, "WARN",
            f"{op_count} `id + \"...\"`-Operationsaufrufe (> 5000) -- Regenerationszeit "
            "pruefen, ggf. in Bloecke aufteilen."
        ))
    return findings


# --------------------------------------------------------------------------
# FS015 -- unknown function calls
# --------------------------------------------------------------------------

_KNOWN_STD_FUNCTIONS = {
    "opExtrude", "opBoolean", "opPattern", "opDeleteBodies", "opFillet", "opChamfer",
    "opShell", "opLoft", "opSweep", "opRevolve", "opPlane", "opOffsetFace",
    "opSplitPart", "opTranslate", "opRotate", "opTransform", "opDraft", "opThicken",
    "opMakeSolid", "opDeleteFace", "opReplaceFace", "opCreateHole",
    "newSketchOnPlane", "newSketch", "skRectangle", "skPolyline", "skLineSegment",
    "skArc", "skCircle", "skEllipse", "skSpline", "skSolve", "skConstraint",
    "skFitSpline", "sketchToParametric",
    "qCreatedBy", "qUnion", "qSubtraction", "qIntersection", "qSketchRegion",
    "qBodyType", "qEverything", "qNthElement", "qOwnedByBody", "qContainsPoint",
    "qClosestTo", "qLargest", "qGeometry", "qContainsFilter", "qEntityFilter",
    "qParallelPlanes", "qCoincidesWithPlane",
    "vector", "matrix", "transform", "identityTransform", "mirrorAcross", "plane", "box", "block",
    "cylinder", "cone", "sphere", "torus", "line", "regenError", "println", "print",
    "toString", "degToRad", "radToDeg", "sin", "cos", "tan", "asin", "acos", "atan",
    "sqrt", "abs", "min", "max", "floor", "ceil", "round", "atan2", "norm",
    "normalize", "cross", "dot", "extrude", "revolve", "loft", "sweep", "fillet",
    "chamfer", "shell", "isLength", "isAngle", "isInteger", "mergeMaps",
    "tolerantEquals", "lookupTableGet", "definition", "evaluateQuery", "evPlane",
    "evVertexPoint", "evEdgeTangentLine", "evFaceTangentPlane", "evApproximateBox",
    "evBox3d", "evDistance", "evCurveDefinition", "evSurfaceDefinition",
    "distance", "angleBetween", "toDouble", "random", "concat", "append", "size",
    "startFeatureParameter", "annotation", "expandCoefficientTable",
    "getVariable", "setVariable", "setProperty", "getProperty", "makeId",
    "color", "unstableIdComponent", "inverse", "evLine", "qAllModifiableSolidBodies", "qNothing", "qTransient", "evVolume", "evArea", "evLength", "newInstantiator",
    "addInstance", "instantiate", "derive", "isAnything", "isReal", "isBoolean",
    "isString", "isQueryEmpty", "keys", "values", "contains", "insert", "remove",
}

_KEYWORDS = {
    "if", "else", "for", "while", "try", "catch", "throw", "return", "function",
    "var", "const", "precondition", "annotation", "export", "import", "is", "as",
    "in", "true", "false", "new", "map", "array", "string", "number", "boolean",
    "context", "definition", "id", "defineFeature", "silent",
}


@rule("FS015", "WARN",
      'Unbekannte Aufrufnamen nur WARN: std-Liste und importierte/hoeherwertige Funktionen sind nicht vollstaendig aufloesbar.')
def _rule_fs015(ctx: LintContext) -> list:
    known = _KNOWN_STD_FUNCTIONS | _KEYWORDS | ctx.local_functions
    seen = {}
    for m in re.finditer(r"(?<![\w:.])([A-Za-z_]\w*)\s*\(", ctx.masked_all):
        name = m.group(1)
        if name in known:
            continue
        # namespaced calls (Foo::bar(...)) are resolved in another document
        prefix_start = max(0, m.start() - 2)
        if ctx.masked_comments[prefix_start:m.start()].endswith("::"):
            continue
        if name not in seen:
            seen[name] = ctx.line_at(m.start())
    findings = []
    for name, line in sorted(seen.items(), key=lambda kv: kv[1]):
        findings.append(Finding(
            "FS015", line, "WARN",
            f"Unbekannter Funktionsaufruf `{name}(...)` -- weder lokal definiert noch in "
            "der bekannten std-Liste. Tippfehler oder fehlender Import?"
        ))
    return findings


# --------------------------------------------------------------------------
# Conservative semantic heuristics (not a FeatureScript type checker).
# --------------------------------------------------------------------------

@rule("FS016", "WARN", "Wiederholte Helferaufrufe mit derselben ungesuffixten Id koennen kollidieren.")
def _rule_fs016(ctx):
    seen = {}
    findings = []
    for call in _creation_calls(ctx):
        if call.name not in ctx.local_functions:
            continue
        ident = _expr(ctx, call.args[1])
        if not re.fullmatch(r"\w+", ident):
            continue
        key = (_scope(ctx, call.start), ident)
        if key in seen:
            findings.append(Finding("FS016", ctx.line_at(call.start), "WARN",
                f"Helfer `{call.name}` erhaelt erneut `{ident}` ohne eindeutiges Suffix; Id-Namensraum pruefen."))
        seen[key] = call.start
    return findings


@rule("FS017", "ERROR", "opBoolean SUBTRACTION mit identischer Target-/Tool-Query ist ungueltig; UNION: WARN.")
def _rule_fs017(ctx):
    findings = []
    for call in ctx.calls:
        if call.name != "opBoolean":
            continue
        fields = _map_fields(ctx, call)
        if not {"tools", "targets", "operationType"} <= fields.keys():
            continue
        # Token whitespace is insignificant outside strings only.
        def canonical(span):
            return "".join(re.findall(r'"(?:[^"\\]|\\.)*"|[^\s"]+', _expr(ctx, span)))
        if canonical(fields["tools"]) != canonical(fields["targets"]):
            continue
        operation = _expr(ctx, fields["operationType"])
        if operation not in {"BooleanOperationType.SUBTRACTION", "BooleanOperationType.UNION"}:
            continue
        severity = "ERROR" if operation.endswith("SUBTRACTION") else "WARN"
        findings.append(Finding("FS017", ctx.line_at(call.start), severity,
            "opBoolean hat textuell identische `targets` und `tools`; Eigen-Boolean pruefen."))
    return findings


def _use_after(ctx, call, ident, allow_any=False):
    """Find a suspicious geometry-operation read, not a return/query composition."""
    _, scope_end = _scope(ctx, call.start)
    end = scope_end
    for m in re.finditer(r"\b" + re.escape(ident) + r"\b", ctx.masked_all[call.end+1:end]):
        pos = call.end + 1 + m.start()
        tail = ctx.masked_all[pos+len(ident):end]
        if re.match(r"\s*=(?!=)", tail):
            return None
        if ctx.masked_all[max(0, pos-1):pos] == ".":
            continue
        owner = min((c for c in ctx.calls if c.opening < pos < c.end),
                    key=lambda c: c.end-c.opening, default=None)
        if not allow_any and (owner is None or (not owner.name.startswith("op") and owner.name not in ctx.local_functions)):
            continue
        # A q* expression or qUnion return preserves a query intentionally.
        if not allow_any and owner is not None and owner.name.startswith("q"):
            continue
        return pos
    return None


@rule("FS018", "WARN", "Query-Variable nach opDeleteBodies ohne Neuzuweisung gelesen: geloeschte Koerper pruefen.")
def _rule_fs018(ctx):
    findings = []
    for call in ctx.calls:
        if call.name != "opDeleteBodies":
            continue
        span = _map_fields(ctx, call).get("entities")
        ident = _expr(ctx, span) if span else ""
        if not re.fullmatch(r"[A-Za-z_]\w*", ident):
            continue
        pos = _use_after(ctx, call, ident, allow_any=True)
        if pos is not None:
            findings.append(Finding("FS018", ctx.line_at(pos), "WARN",
                f"`{ident}` wird nach opDeleteBodies (Zeile {ctx.line_at(call.start)}) gelesen; Query kann leer sein."))
    return findings


@rule("FS019", "WARN", "qCreatedBy mit literalem Kind-Id ohne vorherigen lokalen Erzeuger: Tippfehler pruefen.")
def _rule_fs019(ctx):
    creators = {}
    for call in _creation_calls(ctx):
        key = _literal_id(_expr(ctx, call.args[1]))
        if key:
            creators.setdefault((_scope(ctx, call.start), key), []).append(call.start)
    findings = []
    for call in ctx.calls:
        if call.name != "qCreatedBy" or not call.args:
            continue
        key = _literal_id(_expr(ctx, call.args[0]))
        if not key:
            continue
        matches = creators.get((_scope(ctx, call.start), key), [])
        if not any(pos < call.start for pos in matches):
            findings.append(Finding("FS019", ctx.line_at(call.start), "WARN",
                f"qCreatedBy({_expr(ctx, call.args[0])}, ...) ohne vorherigen direkten lokalen Erzeuger; dynamische/uebergeordnete Ids manuell pruefen."))
    return findings


@rule("FS020", "INFO", "qCreatedBy ohne EntityType ist erlaubt, aber kann unbeabsichtigte Entity-Arten liefern.")
def _rule_fs020(ctx):
    return [Finding("FS020", ctx.line_at(c.start), "INFO",
                    "qCreatedBy ohne EntityType; gewollten BODY/FACE/EDGE-Filter pruefen (gueltiger Overload).")
            for c in ctx.calls if c.name == "qCreatedBy" and len(c.args) == 1]


@rule("FS021", "ERROR", "opLoft braucht mindestens zwei Profile; opSweep braucht ein nichtleeres Profil und einen Pfad.")
def _rule_fs021(ctx):
    findings = []
    for call in ctx.calls:
        if call.name not in {"opLoft", "opSweep"}:
            continue
        fields = _map_fields(ctx, call)
        if len(call.args) != 3 or not _expr(ctx, call.args[2]).startswith("{"):
            continue  # Computed maps cannot be inspected reliably.
        reason = "`profileSubqueries` fehlt" if call.name == "opLoft" and "profileSubqueries" not in fields else None
        profile = fields.get("profileSubqueries" if call.name == "opLoft" else "profiles")
        if profile:
            a, b = profile
            while a < b and ctx.masked_comments[a].isspace():
                a += 1
            end = ctx.pairs.get(a)
            if ctx.masked_all[a:a+1] == "[" and end is not None:
                count = len(_argument_spans(ctx.masked_all, a, end, ctx.pairs))
                if count < (2 if call.name == "opLoft" else 1):
                    reason = f"nur {count} literale Profile"
            if _expr(ctx, profile) in {"qNothing()", "qUnion([])"}:
                reason = "leere Profil-Query"
        if call.name == "opSweep" and ("profiles" not in fields or "path" not in fields):
            reason = "`profiles` oder `path` fehlt"
        if call.name == "opSweep" and "path" in fields and _expr(ctx, fields["path"]) in {"[]", "qNothing()", "qUnion([])"}:
            reason = "leerer Pfad"
        if reason:
            findings.append(Finding("FS021", ctx.line_at(call.start), "ERROR", f"{call.name}: {reason}."))
    return findings


@rule("FS022", "WARN", "isLength/isAngle-Parameter nicht erneut mit einer Laengen-/Winkeleinheit multiplizieren.")
def _rule_fs022(ctx):
    findings = []
    for call in ctx.calls:
        if call.name not in {"isLength", "isAngle"} or not call.args:
            continue
        param = _expr(ctx, call.args[0])
        if not re.fullmatch(r"\w+\.\w+", param):
            continue
        # Predicate and usage must belong to the same defineFeature invocation.
        owner = next((c for c in ctx.calls if c.name == "defineFeature" and c.start < call.start < c.end), None)
        if owner is None:
            continue
        for m in re.finditer(re.escape(param) + r"\s*\*\s*(millimeter|centimeter|meter|inch|degree|radian)\b",
                             ctx.masked_all[call.end:owner.end]):
            findings.append(Finding("FS022", ctx.line_at(call.end+m.start()), "WARN",
                f"`{param}` hat durch {call.name} bereits Einheiten; Multiplikation mit {m.group(1)} pruefen."))
    return findings


@rule("FS023", "WARN", "Sichtbare precondition-Parameter brauchen eine annotation mit Name.")
def _rule_fs023(ctx):
    findings = []
    for m in re.finditer(r"\bprecondition\s*\{", ctx.masked_all):
        start = m.end() - 1
        end = ctx.pairs.get(start)
        if end is None:
            continue
        previous = start + 1
        pattern = r"(?:\b(?:isLength|isAngle|isInteger|isReal)\s*\(\s*(\w+\.\w+)|\b(\w+\.\w+)\s+is\s+\w+)"
        for param in re.finditer(pattern, ctx.masked_all[start+1:end]):
            pos = start + 1 + param.start()
            between = ctx.masked_comments[previous:pos]
            if not re.search(r'"Name"\s*:', between):
                findings.append(Finding("FS023", ctx.line_at(pos), "WARN",
                    f"precondition-Parameter `{param.group(1) or param.group(2)}` ohne lokale annotation Name."))
            previous = pos + len(param.group(0))
    return findings


@rule("FS024", "WARN", "regenError braucht eine aussagekraeftige Meldung; freier Text ist erlaubt, keine String-Verbotsregel.")
def _rule_fs024(ctx):
    findings = []
    for call in ctx.calls:
        if call.name == "regenError" and (not call.args or re.fullmatch(r'"\s*"', _expr(ctx, call.args[0]))):
            findings.append(Finding("FS024", ctx.line_at(call.start), "WARN",
                "regenError ohne aussagekraeftige Fehlermeldung."))
    return findings


@rule("FS025", "WARN", "catch ohne throw kann fehlgeschlagene Geometrie still verschlucken (absichtliche Fallbacks erlaubt).")
def _rule_fs025(ctx):
    findings = []
    for m in re.finditer(r"\bcatch\b", ctx.masked_all):
        pos = m.end()
        while pos < len(ctx.source) and ctx.masked_all[pos].isspace():
            pos += 1
        if ctx.masked_all[pos:pos+1] == "(":
            pos = ctx.pairs.get(pos, pos) + 1
            while pos < len(ctx.source) and ctx.masked_all[pos].isspace():
                pos += 1
        end = ctx.pairs.get(pos)
        if end is not None and ctx.masked_all[pos] == "{" and not re.search(r"\bthrow\b", ctx.masked_all[pos:end]):
            findings.append(Finding("FS025", ctx.line_at(m.start()), "WARN",
                "catch ohne Rethrow; ist ein expliziter Fallback/Statuscheck vorhanden?"))
    return findings


@rule("FS026", "WARN", "0-basierte for-Schleife mit <= size(array) erreicht einen ungueltigen Index.")
def _rule_fs026(ctx):
    findings = []
    for call in ctx.calls:
        if call.name != "for":
            continue
        text = ctx.masked_all[call.opening+1:call.end]
        m = re.match(r"\s*(?:var\s+)?(\w+)\s*=\s*0\s*;\s*\1\s*<=\s*size\s*\(", text)
        if m:
            findings.append(Finding("FS026", ctx.line_at(call.start), "WARN",
                "for startet bei 0 und verwendet <= size(...); normalerweise < size(...)."))
    return findings


@rule("FS027", "INFO", "Lokale Variable ohne weitere lexikalische Verwendung: moeglicher Copy-Paste-Rest.")
def _rule_fs027(ctx):
    findings = []
    # Count per function (including nested closures); no repeated whole-file scans.
    scopes = {}
    for m in re.finditer(r"\b(?:var|const)\s+(\w+)\s*=", ctx.masked_all):
        scope = _scope(ctx, m.start())
        if scope == (0, len(ctx.source)) or m.group(1).startswith("_"):
            continue
        if scope not in scopes:
            scopes[scope] = Counter(re.findall(r"\b[A-Za-z_]\w*\b", ctx.masked_all[scope[0]:scope[1]]))
        if scopes[scope][m.group(1)] == 1:
            findings.append(Finding("FS027", ctx.line_at(m.start()), "INFO",
                f"Lokale Variable `{m.group(1)}` wird nicht gelesen; Initialisierung kann trotzdem Seiteneffekte haben."))
    return findings


@rule("FS028", "ERROR", "Aufruf lokal deklarierter Helfer mit falscher Argumentzahl (inklusive yz/lb/prism).")
def _rule_fs028(ctx):
    signatures = {}
    for m in re.finditer(r"\bfunction\s+(\w+)\s*\(", ctx.masked_all):
        opening = m.end()-1
        end = ctx.pairs.get(opening)
        if end is not None:
            signatures.setdefault(m.group(1), set()).add(len(_argument_spans(ctx.masked_all, opening, end, ctx.pairs)))
    findings = []
    for call in ctx.calls:
        if call.name in signatures and len(call.args) not in signatures[call.name]:
            findings.append(Finding("FS028", ctx.line_at(call.start),
                "WARN" if call.name in _KNOWN_STD_FUNCTIONS else "ERROR",
                f"`{call.name}` mit {len(call.args)} Argumenten; lokale Signatur(en): {sorted(signatures[call.name])}."
                + (" std-Overload kann zusaetzlich existieren." if call.name in _KNOWN_STD_FUNCTIONS else "")))
    return findings


@rule("FS029", "INFO", "Lokale box/plane/line-Helfer koennen std-Namen ueberladen; Signatur und Namespaces pruefen.")
def _rule_fs029(ctx):
    return [Finding("FS029", ctx.line_at(m.start()), "INFO",
                    f"Lokaler Helfer `{m.group(1)}` teilt den Namen einer std-Funktion; Overload/Signatur pruefen.")
            for m in re.finditer(r"\bfunction\s+(box|plane|line)\s*\(", ctx.masked_all)]


@rule("FS030", "WARN", "addInstance mit rohen Dokument-IDs ersetzt keinen importierten BuildFunction/PartStudioData.")
def _rule_fs030(ctx):
    findings = []
    for call in ctx.calls:
        if call.name != "addInstance":
            continue
        # The supported forms include addInstance(instantiator, buildFunction, options)
        # and PartStudioData. Do not require a loadedContext key on valid overloads.
        fields = _map_fields(ctx, call, 1)
        if {"documentId", "elementId", "version"} & fields.keys() and not {"buildFunction", "partStudio"} & fields.keys():
            findings.append(Finding("FS030", ctx.line_at(call.start), "WARN",
                "addInstance erhaelt rohe Dokument-IDs; Studio importieren und BuildFunction/PartStudioData uebergeben."))
    return findings


@rule("FS031", "ERROR", "Doppelte globale Funktionssignaturen oder Enum/Konstanten-Namen verhindern die Studio-Kompilierung; unterschiedliche Overloads sind erlaubt.")
def _rule_fs031(ctx):
    """Check studio declarations, not repeated local names in independent scopes.

    Function signatures consist of parameter types, not parameter names or
    return types. Do not reject legitimate overloads with different argument
    counts/types. This is intentionally not import/standard-library resolution.
    """
    seen = {}
    findings = []
    pattern = r"\b(function|enum|const|var)\s+([A-Za-z_]\w*)\s*([({=])"
    for match in re.finditer(pattern, ctx.masked_all):
        if ctx.brace_depth[match.start()] != 0:
            continue
        kind, name, delimiter = match.groups()
        signature = None
        if kind == "function":
            if delimiter != "(":
                continue
            opening = match.end()-1
            end = ctx.pairs.get(opening)
            if end is None:
                continue
            types = []
            for a, b in _argument_spans(ctx.masked_all, opening, end, ctx.pairs):
                param = ctx.masked_all[a:b].strip()
                typed = re.fullmatch(r"[A-Za-z_]\w*\s+is\s+(.+)", param, re.S)
                types.append(re.sub(r"\s+", "", typed.group(1)) if typed else "*")
            signature = tuple(types)
        elif (kind == "enum" and delimiter != "{") or (kind in {"const", "var"} and delimiter != "="):
            continue
        previous = seen.setdefault(name, [])
        collision = next((entry for entry in previous
                          if kind != "function" or entry[0] != "function" or entry[1] == signature), None)
        if collision:
            suffix = "(" + ", ".join(signature) + ")" if signature is not None else ""
            findings.append(Finding("FS031", ctx.line_at(match.start()), "ERROR",
                f"Doppelte globale Definition `{name}{suffix}`; erste kollidierende Definition in Zeile {collision[2]}. Doppelten Quellblock entfernen oder Signaturen trennen."))
        previous.append((kind, signature, ctx.line_at(match.start())))
    return findings


@rule("FS032", "ERROR", "`box` ist ein FeatureScript-Schluesselwort (new box(...)); als Variablen- oder Parametername kompiliert das Studio nicht.")
def _rule_fs032(ctx):
    """Observed 2026-10-10 (an end-cap project): `const box = evBox3d(...)` left the studio's featurespecs empty without a
    message; renaming the variable alone made it compile."""
    findings = []
    for match in re.finditer(r"\b(?:const|var)\s+box\b|[(,]\s*box\s+is\b", ctx.masked_all):
        findings.append(Finding("FS032", ctx.line_at(match.start()), "ERROR",
            "`box` als Name verhindert die Studio-Kompilierung (featurespecs leer); umbenennen, z. B. `bounds`."))
    return findings


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def lint_source(path: str, source: str) -> list:
    ctx = build_context(path, source)
    findings = []
    for spec in RULES:
        findings.extend(spec["func"](ctx))
    findings.sort(key=lambda f: (f.line, f.rule_id))
    return findings


def lint_file(path: Path) -> list:
    source = path.read_text(encoding="utf-8")
    return lint_source(str(path), source)


def _print_rules(as_json=False):
    if as_json:
        print(json.dumps({"schema_version": 1, "rules": [
            {key: spec[key] for key in ("id", "severity", "lesson")} for spec in RULES
        ]}, indent=2, ensure_ascii=False))
        return
    for spec in sorted(RULES, key=lambda s: s["id"]):
        print(f"{spec['id']}  [{spec['severity']:5}]  {spec['lesson']}")


def _report(findings: list, path: str, as_json: bool) -> None:
    if as_json:
        print(json.dumps({
            "schema_version": 1,
            "path": path,
            "counts": {level: sum(f.severity == level for f in findings) for level in SEVERITY_ORDER},
            "findings": [f.__dict__ for f in findings],
        }, indent=2, ensure_ascii=False))
        return
    if not findings:
        print(f"{path}: keine Befunde.")
        return
    print(f"{path}:")
    for f in findings:
        print(f"  {f.format()}")
    counts = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda kv: -SEVERITY_ORDER[kv[0]]))
    print(f"  -- {summary}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", nargs="?", help="Pfad zu einer .fs-Datei")
    parser.add_argument("--json", action="store_true", help="Befunde als JSON ausgeben")
    parser.add_argument("--strict", action="store_true",
                         help="WARN/INFO-Befunde fuehren ebenfalls zu Exit-Code 1")
    parser.add_argument("--rules", action="store_true", help="Alle Regeln + Lektion auflisten")
    args = parser.parse_args(argv)

    if args.rules:
        _print_rules(args.json)
        return 0

    if not args.file:
        parser.error("file ist erforderlich (ausser bei --rules)")

    path = Path(args.file)
    try:
        findings = lint_file(path)
    except (OSError, UnicodeError) as exc:
        if args.json:
            print(json.dumps({"schema_version": 1, "path": str(path), "counts":
                {level: 0 for level in SEVERITY_ORDER}, "findings": [],
                "error": {"kind": "input_error", "message": str(exc)}}, ensure_ascii=False))
        else:
            print(f"Datei nicht lesbar: {path}: {exc}", file=sys.stderr)
        return 2

    _report(findings, str(path), args.json)

    has_error = any(f.severity == "ERROR" for f in findings)
    has_warn = any(f.severity in ("WARN", "INFO") for f in findings)
    if has_error:
        return 2
    if has_warn and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
