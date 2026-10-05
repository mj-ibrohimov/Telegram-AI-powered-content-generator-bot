"""Statically checks every app/ module for references to names that are
never defined anywhere in that module (not imported, not assigned, not a
parameter, not a builtin). This is the check that actually catches a bug
like the one that shipped: describe_exception() used inside an except block
but never imported -- a plain `import app.module` does NOT fail on this,
because Python doesn't resolve names inside function bodies until the
function is called (see test_imports.py's docstring for the real-world
incident this caught).

This is necessarily a conservative approximation (it does not do full
scope/control-flow analysis), so it can have false negatives on more
convoluted code, but a bare NameError like the admin.py / publication_service.py
bug is exactly the class of mistake it's designed to catch.
"""
import ast
import builtins
import pathlib

import pytest

APP_ROOT = pathlib.Path(__file__).parent.parent / "app"


def _iter_app_files():
    return sorted(APP_ROOT.rglob("*.py"))


def _collect_module_level_names(tree: ast.Module) -> set[str]:
    """Names available anywhere in the module: imports, top-level/nested
    assignments, function/class defs, and their parameters."""
    names: set[str] = set(dir(builtins))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
            args = node.args
            for arg in (
                args.posonlyargs + args.args + args.kwonlyargs + ([args.vararg] if args.vararg else []) + (
                    [args.kwarg] if args.kwarg else []
                )
            ):
                if arg is not None:
                    names.add(arg.arg)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    names.add(sub.id)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    for sub in ast.walk(item.optional_vars):
                        if isinstance(sub, ast.Name):
                            names.add(sub.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in node.generators:
                for sub in ast.walk(generator.target):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
        elif isinstance(node, ast.Global):
            names.update(node.names)
        elif isinstance(node, ast.Lambda):
            for arg in node.args.args:
                names.add(arg.arg)
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            names.add(node.target.id)

    return names


def _find_undefined_loads(tree: ast.Module, defined: set[str]) -> list[tuple[int, str]]:
    undefined = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined:
                undefined.append((node.lineno, node.id))
    return undefined


@pytest.mark.parametrize("path", _iter_app_files(), ids=lambda p: str(p.relative_to(APP_ROOT)))
def test_no_undefined_names(path: pathlib.Path):
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    defined = _collect_module_level_names(tree)
    undefined = _find_undefined_loads(tree, defined)

    if undefined:
        details = ", ".join(f"line {line}: '{name}'" for line, name in undefined)
        pytest.fail(f"{path.relative_to(APP_ROOT)} references undefined name(s): {details}")
