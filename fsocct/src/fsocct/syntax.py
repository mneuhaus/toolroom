"""A tokenizer and recursive-descent/Pratt parser. No host-language evaluation."""

import json
import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Token:
    text: str
    line: int
    column: int
    filename: str


class FSError(Exception):
    def __init__(self, message, token=None):
        super().__init__(message)
        self.message, self.token = message, token

    def __str__(self):
        if self.token:
            t = self.token
            return f"{t.filename}:{t.line}:{t.column}: {self.message}"
        return self.message


class Unsupported(FSError):
    """Compatibility errors deliberately cannot be swallowed by FeatureScript try."""


class LimitExceeded(FSError):
    pass


@dataclass
class Node:
    kind: str
    args: tuple
    token: Token
    exported: bool = False


_TOKEN = re.compile(
    r"(?P<space>\s+)|(?P<comment>//[^\n]*|/\*[\s\S]*?\*/)"
    r"|(?P<string>\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*')"
    r"|(?P<number>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"|(?P<name>[A-Za-z_][A-Za-z_0-9]*)"
    r"|(?P<op>\?\?=|&&=|\|\|=|::|=>|->|\?\.|\?\[|\?\?|==|!=|<=|>=|&&|\|\||"
    r"[+*/%^~\-]=|[{}()\[\],;:.?+*/%^~!<>=\-])"
)


def tokenize(source, filename):
    result, pos, line, column = [], 0, 1, 1
    while pos < len(source):
        m = _TOKEN.match(source, pos)
        token = Token(source[pos : pos + 20], line, column, filename)
        if not m:
            raise FSError(f"Unexpected character {source[pos]!r}", token)
        value = m.group()
        if m.lastgroup not in ("space", "comment"):
            result.append(Token(value, line, column, filename))
        count = value.count("\n")
        line += count
        column = len(value.rsplit("\n", 1)[-1]) + 1 if count else column + len(value)
        pos = m.end()
    result.append(Token("<eof>", line, column, filename))
    return result


class Parser:
    precedence: ClassVar = {
        "??": 10,
        "||": 15,
        "&&": 20,
        "==": 30,
        "!=": 30,
        "<": 40,
        ">": 40,
        "<=": 40,
        ">=": 40,
        "is": 45,
        "as": 45,
        "~": 50,
        "+": 60,
        "-": 60,
        "*": 70,
        "/": 70,
        "%": 70,
        "^": 90,
    }
    assignments: ClassVar = {"=", "+=", "-=", "*=", "/=", "%=", "^=", "~=", "&&=", "||=", "??="}

    def __init__(self, source, filename="<source>"):
        self.tokens = tokenize(source, filename)
        self.i = 0

    @property
    def t(self):
        return self.tokens[self.i]

    def take(self, text=None):
        t = self.t
        if text is not None and t.text != text:
            raise FSError(f"Expected {text!r}, found {t.text!r}", t)
        self.i += 1
        return t

    def accept(self, text):
        if self.t.text == text:
            return self.take()
        return None

    def name(self):
        t = self.take()
        if not re.fullmatch(r"[A-Za-z_]\w*", t.text):
            raise FSError("Expected an identifier", t)
        return t.text

    def type_name(self):
        name = self.name()
        while self.accept("::"):
            name += "::" + self.name()
        return name

    def node(self, kind, t, *args):
        return Node(kind, args, t)

    def program(self):
        nodes = []
        while self.t.text != "<eof>":
            t = self.t
            exported = bool(self.accept("export"))
            if self.accept("FeatureScript"):
                n = self.node("version", t, self.take().text)
                self.take(";")
            elif self.t.text == "import" or (
                self.tokens[self.i + 1].text == "::" and self.tokens[self.i + 2].text == "import"
            ):
                ns = None
                if self.t.text != "import":
                    ns = self.name()
                    self.take("::")
                self.take("import")
                self.take("(")
                fields = {}
                while self.t.text != ")":
                    k = self.name()
                    self.take(":")
                    fields[k] = self.expr()
                    if not self.accept(","):
                        break
                self.take(")")
                self.take(";")
                n = self.node("import", t, ns, fields)
            elif self.accept("enum"):
                name = self.name()
                self.take("{")
                values = []
                while self.t.text != "}":
                    if self.accept("annotation"):
                        self.expr()
                    values.append(self.name())
                    if not self.accept(","):
                        break
                self.take("}")
                n = self.node("enum", t, name, values)
            elif self.accept("type"):
                name = self.name()
                self.take("typecheck")
                pred = self.type_name()
                self.take(";")
                n = self.node("type", t, name, pred)
            elif self.t.text in ("function", "predicate"):
                kind = self.take().text
                name = self.name()
                n = self.node("function_decl", t, name, self.function(t, kind))
            elif self.t.text == "const":
                n = self.simple()
                self.take(";")
            elif self.accept("annotation"):
                n = self.node("annotation", t, self.expr())
            else:
                raise Unsupported(f"Unsupported top-level construct {self.t.text!r}", self.t)
            n.exported = exported
            nodes.append(n)
        return nodes

    def parameters(self):
        self.take("(")
        params = []
        if self.t.text != ")":
            while True:
                name = self.name()
                constraint = self.type_name() if self.accept("is") else None
                params.append((name, constraint))
                if not self.accept(","):
                    break
        self.take(")")
        return params

    def function(self, t, kind="function", params=None, arrow=False):
        params = self.parameters() if params is None else params
        ret = self.type_name() if self.accept("returns") else None
        pre = self.statement() if self.accept("precondition") else None
        if arrow:
            self.take("=>")
        if self.t.text == "{":
            body = self.statement()
        elif arrow:
            body = self.node("return", t, self.expr())
        else:
            raise FSError("Expected function body", self.t)
        return self.node("function", t, params, ret, pre, body, kind)

    def simple(self):
        t = self.t
        if t.text in ("var", "const"):
            self.take()
            name = self.name()
            constraint = self.type_name() if self.accept("is") else None
            value = self.expr() if self.accept("=") else None
            if (t.text == "const" or constraint) and value is None:
                raise FSError("Constants and typed variables need an initializer", t)
            return self.node("declare", t, name, constraint, value, t.text == "const")
        value = self.expr()
        if self.t.text in self.assignments:
            op = self.take().text
            return self.node("assign", t, value, op, self.expr())
        return self.node("expression", t, value)

    def statement(self):
        t = self.t
        if self.accept("{"):
            nodes = []
            while self.t.text != "}":
                if self.t.text == "<eof>":
                    raise FSError("Unclosed block", t)
                nodes.append(self.statement())
            self.take("}")
            return self.node("block", t, nodes)
        if self.accept(";"):
            return self.node("block", t, [])
        if self.accept("annotation"):
            return self.node("annotation", t, self.expr())
        if self.accept("if"):
            self.take("(")
            cond = self.expr()
            self.take(")")
            yes = self.statement()
            no = self.statement() if self.accept("else") else None
            return self.node("if", t, cond, yes, no)
        if self.accept("while"):
            self.take("(")
            cond = self.expr()
            self.take(")")
            return self.node("while", t, cond, self.statement())
        if self.accept("for"):
            self.take("(")
            start = self.i
            declares = bool(self.accept("var"))
            names = []
            if re.fullmatch(r"[A-Za-z_]\w*", self.t.text):
                names.append(self.name())
                if self.accept(","):
                    names.append(self.name())
            if self.accept("in"):
                container = self.expr()
                self.take(")")
                return self.node("for_in", t, names, container, self.statement(), declares)
            self.i = start
            init = self.simple() if self.t.text != ";" else None
            self.take(";")
            cond = self.expr() if self.t.text != ";" else self.node("literal", t, True)
            self.take(";")
            step = self.simple() if self.t.text != ")" else None
            self.take(")")
            return self.node("for", t, init, cond, step, self.statement())
        if t.text in ("return", "throw", "break", "continue"):
            self.take()
            value = self.expr() if t.text in ("return", "throw") and self.t.text != ";" else None
            self.take(";")
            return self.node(t.text, t, value)
        if t.text == "try" and self.tokens[self.i + 1].text in ("{", "silent"):
            start = self.i
            self.take()
            self.accept("silent")
            if self.t.text == "{":
                body = self.statement()
                name, handler = None, None
                if self.accept("catch"):
                    if self.accept("("):
                        name = self.name()
                        self.take(")")
                    handler = self.statement()
                return self.node("try", t, body, name, handler)
            self.i = start
        result = self.simple()
        self.take(";")
        return result

    def expr(self, minimum=0):
        t = self.take()
        s = t.text
        if s in ("true", "false", "undefined"):
            left = self.node("literal", t, {"true": True, "false": False, "undefined": None}[s])
        elif s[0].isdigit() or (s[0] == "." and len(s) > 1):
            left = self.node("literal", t, float(s))
        elif s[0] in "\"'":
            # JSON escapes plus FeatureScript single-quoted strings.
            if s[0] == "'":
                s = '"' + s[1:-1].replace('"', '\\"').replace("\\'", "'") + '"'
            try:
                left = self.node("literal", t, json.loads(s))
            except ValueError as e:
                raise FSError("Invalid string escape", t) from e
        elif s in ("-", "!", "+"):
            left = self.node("unary", t, s, self.expr(80))
        elif s == "function":
            left = self.function(t)
        elif s == "try":
            self.accept("silent")
            self.take("(")
            left = self.node("try_expr", t, self.expr())
            self.take(")")
        elif s == "new":
            self.take("box")
            self.take("(")
            left = self.node("box", t, self.expr())
            self.take(")")
        elif s == "(":
            # A parenthesized lambda parameter list is distinguishable by =>.
            start = self.i
            depth, j = 1, self.i
            while depth and j < len(self.tokens):
                depth += (self.tokens[j].text == "(") - (self.tokens[j].text == ")")
                j += 1
            is_arrow = j < len(self.tokens) and self.tokens[j].text in ("=>", "returns")
            if is_arrow:
                self.i = start - 1
                left = self.function(t, arrow=True)
            else:
                left = self.expr()
                self.take(")")
        elif s == "[":
            values = []
            while self.t.text != "]":
                values.append(self.expr())
                if not self.accept(","):
                    break
            self.take("]")
            left = self.node("array", t, values)
        elif s == "{":
            pairs = []
            while self.t.text != "}":
                if (
                    re.fullmatch(r"[A-Za-z_]\w*", self.t.text)
                    and self.tokens[self.i + 1].text == ":"
                ):
                    k = self.take()
                    key = self.node("literal", k, k.text)
                else:
                    key = self.expr()
                self.take(":")
                pairs.append((key, self.expr()))
                if not self.accept(","):
                    break
            self.take("}")
            left = self.node("map", t, pairs)
        elif re.fullmatch(r"[A-Za-z_]\w*", s):
            while self.accept("::"):
                s += "::" + self.name()
            if self.t.text == "=>":
                left = self.function(t, params=[(s, None)], arrow=True)
            else:
                left = self.node("name", t, s)
        else:
            raise Unsupported(f"Unsupported expression starting with {s!r}", t)

        while True:
            op = self.t.text
            if op in ("(", "[", "?["):
                self.take()
                if op == "(":
                    args = []
                    while self.t.text != ")":
                        args.append(self.expr())
                        if not self.accept(","):
                            break
                    self.take(")")
                    left = self.node("call", t, left, args)
                else:
                    index = self.expr() if self.t.text != "]" else None
                    self.take("]")
                    left = self.node("index", t, left, index, op == "?[")
            elif op in (".", "?."):
                self.take()
                key = self.node("literal", self.t, self.name())
                left = self.node("index", t, left, key, op == "?.")
            elif op == "->":
                self.take()
                fn = self.node("name", self.t, self.type_name())
                self.take("(")
                args = [left]
                while self.t.text != ")":
                    args.append(self.expr())
                    if not self.accept(","):
                        break
                self.take(")")
                left = self.node("call", t, fn, args)
            elif op == "?" and minimum <= 5:
                self.take()
                yes = self.expr()
                self.take(":")
                left = self.node("conditional", t, left, yes, self.expr(5))
            elif op in self.precedence and self.precedence[op] >= minimum:
                self.take()
                if op in ("is", "as"):
                    left = self.node("type_expr", t, op, left, self.type_name())
                else:
                    right = self.expr(self.precedence[op] + (0 if op == "^" else 1))
                    left = self.node("binary", t, op, left, right)
            else:
                return left


def parse(source, filename="<source>"):
    return Parser(source, filename).program()
