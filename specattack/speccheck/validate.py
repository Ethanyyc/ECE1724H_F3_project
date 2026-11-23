"""Static part of loading LLM-written code (specs and programs): parse,
normalize, check a few rules and rewrite, without running anything. loader.py
then runs the code with run-time guards.

The model writes ordinary Python that builds Z3 formulas. The static rules keep
the code away from the machine and make every function a pure function of its
arguments, so that calling it again builds the same formula:

- only function definitions at the top level (helper functions are fine), and
  each requested function with the right number of plain parameters;
- no imports (lines importing z3 are dropped), no try (it could swallow the
  run-time guards), no global, no decorators, no lists, dicts, sets or calls as
  default values, no names or attributes that start with __, attributes only
  for list, dict and set methods, and no rebinding of the predefined names.

Normalization and rewrites:

- `z3.X` becomes `X`; type annotations, docstrings and `if __name__ == ...`
  blocks are removed;
- chained comparisons `a < b < c` become `__chain(a < b, b < c)`, a Python bool
  for plain values and And(...) for formulas (Python's own chaining would ask
  Z3 for a truth value);
- `/`, `//` and `%` become `__div`, `__floordiv` and `__mod`, which keep
  Python's meaning on plain numbers and use Z3 integer division and remainder
  on formulas (loader.py requires a positive constant divisor there, where Z3
  and Python agree).
"""

import ast
import copy
from dataclasses import dataclass
from typing import Optional

PREDEFINED = {"And", "Or", "Not", "Implies", "If", "ForAll", "Exists", "Sum", "Int", "Ints", "N", "range"}
METHODS = {"append", "extend", "insert", "pop", "remove", "index", "count", "copy", "reverse", "sort", "clear",
           "keys", "values", "items", "get", "add", "update", "discard"}
ARITHMETIC = {ast.Div: "__div", ast.FloorDiv: "__floordiv", ast.Mod: "__mod"}
CHAIN = "__chain"
TRY_NODES = (ast.Try, getattr(ast, "TryStar", ast.Try))
MUTABLE_DEFAULTS = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp, ast.Call)
MAX_SOURCE_CHARS = 20_000
MAX_NODES = 3_000


class Rejected(Exception):
    pass


@dataclass
class Validated:
    ok: bool
    reason: str
    tree: Optional[ast.Module] = None
    size: int = 0                    # AST nodes of all function definitions, before the rewrites


def validate(source, required, arity):
    """Check `source`.

    required: names of the functions it must define, e.g. ("pre", "post").
    arity: number of parameters of each required function.
    """
    if len(source) > MAX_SOURCE_CHARS:
        return Validated(False, "the code is too long")
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return Validated(False, f"syntax error: {error.msg} (line {error.lineno})")
    tree = _Normalize(_z3_names(tree)).visit(tree)
    ast.fix_missing_locations(tree)
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        return Validated(False, "the code is too long")
    try:
        _check_module(tree, tuple(required), dict(arity))
    except Rejected as error:
        return Validated(False, str(error))
    size = sum(source_size(node) for node in tree.body)
    tree = _Rewrite().visit(tree)
    ast.fix_missing_locations(tree)
    return Validated(True, "", tree, size)


def source_size(node):
    """Number of AST nodes, excluding load/store markers."""
    return sum(1 for child in ast.walk(node) if not isinstance(child, ast.expr_context))


# normalization

def _z3_names(tree):
    names = {"z3"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.asname for alias in node.names if alias.name == "z3" and alias.asname)
    return names


def _is_z3_import(node):
    if isinstance(node, ast.ImportFrom):
        return node.module == "z3" and node.level == 0
    if isinstance(node, ast.Import):
        return all(alias.name == "z3" for alias in node.names)
    return False


def _is_docstring(node):
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def _is_main_block(node):
    test = getattr(node, "test", None)
    return (isinstance(node, ast.If) and isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
            and test.left.id == "__name__")


def _all_args(arguments):
    args = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
    return args + [arg for arg in (arguments.vararg, arguments.kwarg) if arg is not None]


class _Normalize(ast.NodeTransformer):
    def __init__(self, z3_names):
        self.z3_names = z3_names

    def _body(self, body):
        body = [stmt for stmt in body if not (_is_z3_import(stmt) or _is_main_block(stmt))]
        if body and _is_docstring(body[0]):
            body = body[1:]
        return body

    def visit_Module(self, node):
        node.body = self._body(node.body)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node):
        node.returns = None
        for arg in _all_args(node.args):
            arg.annotation = None
        node.body = self._body(node.body)
        self.generic_visit(node)
        node.body = node.body or [ast.Pass()]
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_AnnAssign(self, node):
        if node.value is None:
            return None
        new = ast.copy_location(ast.Assign(targets=[node.target], value=node.value), node)
        self.generic_visit(new)
        return new

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id in self.z3_names and isinstance(node.ctx, ast.Load):
            return ast.copy_location(ast.Name(id=node.attr, ctx=ast.Load()), node)
        return node


# checks

def _check_module(tree, required, arity):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise Rejected("import statements are not allowed; the Z3 functions are already available")
    defined = []
    for stmt in tree.body:
        if not isinstance(stmt, ast.FunctionDef):
            raise Rejected(f"only function definitions are allowed at the top level, found {_kind(stmt)}")
        if stmt.name in defined:
            raise Rejected(f"function {stmt.name} is defined twice")
        defined.append(stmt.name)
    missing = [name for name in required if name not in defined]
    if missing:
        raise Rejected(f"missing function(s): {', '.join(missing)}")
    for stmt in tree.body:
        if stmt.name in arity:
            _check_signature(stmt, arity[stmt.name])
    for node in ast.walk(tree):
        _check_node(node)


def _check_signature(node, expected):
    args = node.args
    if args.posonlyargs or args.vararg or args.kwonlyargs or args.kwarg or args.defaults or args.kw_defaults:
        raise Rejected(f"{node.name} must take plain positional parameters")
    if len(args.args) != expected:
        raise Rejected(f"{node.name} must take {expected} parameter(s), found {len(args.args)}")


def _check_node(node):
    if isinstance(node, TRY_NODES):
        raise Rejected("try statements are not allowed")
    if isinstance(node, ast.Global):
        raise Rejected("global statements are not allowed")
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.decorator_list:
            raise Rejected("decorators are not allowed")
        _check_binding(node.name)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        defaults = node.args.defaults + [d for d in node.args.kw_defaults if d is not None]
        if any(isinstance(default, MUTABLE_DEFAULTS) for default in defaults):
            raise Rejected("default parameter values may not be lists, dicts, sets or function calls")
    if isinstance(node, ast.arg):
        _check_binding(node.arg)
    if isinstance(node, ast.Name):
        if node.id.startswith("__"):
            raise Rejected(f"names and attributes starting with __ are not allowed ({node.id})")
        if not isinstance(node.ctx, ast.Load):
            _check_binding(node.id)
    if isinstance(node, ast.Attribute):
        if node.attr.startswith("__"):
            raise Rejected(f"names and attributes starting with __ are not allowed ({node.attr})")
        if node.attr not in METHODS:
            raise Rejected(f"the attribute .{node.attr} is not allowed; only list, dict and set methods "
                           "such as .append can be used")
    if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
        _check_binding(node.name)


def _check_binding(name):
    if name.startswith("__"):
        raise Rejected(f"names and attributes starting with __ are not allowed ({name})")
    if name in PREDEFINED:
        raise Rejected(f"{name} is predefined and cannot be redefined")


# rewrites

def _call(name, args):
    return ast.Call(func=ast.Name(id=name, ctx=ast.Load()), args=args, keywords=[])


class _Rewrite(ast.NodeTransformer):
    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1:
            return node
        parts, left = [], node.left
        for op, right in zip(node.ops, node.comparators):
            parts.append(ast.Compare(left=copy.deepcopy(left), ops=[op], comparators=[copy.deepcopy(right)]))
            left = right
        return ast.copy_location(_call(CHAIN, parts), node)

    def visit_BinOp(self, node):
        self.generic_visit(node)
        name = ARITHMETIC.get(type(node.op))
        if name is None:
            return node
        return ast.copy_location(_call(name, [node.left, node.right]), node)

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        name = ARITHMETIC.get(type(node.op))
        if name is None:
            return node
        current = copy.deepcopy(node.target)
        current.ctx = ast.Load()
        return ast.copy_location(ast.Assign(targets=[node.target], value=_call(name, [current, node.value])), node)


def _kind(node):
    return type(node).__name__
