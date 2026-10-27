"""Check the README's layer boundaries without importing application code.

Run from any directory: python project_root/tools/check_architecture.py
Checks static imports, including function-local imports. Dynamic import strings,
subprocess commands and runtime side effects still require behavioral tests.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from importlib.util import resolve_name
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_LAYERS = {
    "scheduling": {"scheduling"},
    "application": {"application", "scheduling"},
    "infrastructure": {"infrastructure", "application", "scheduling"},
    "gui": {"gui", "application", "infrastructure", "scheduling"},
    "mcp_adapter": {"mcp_adapter", "application", "infrastructure", "scheduling"},
    "bootstrap": {"bootstrap", "application", "infrastructure", "scheduling", "gui"},
}
# Presentation's scheduling worker is an explicit composition entrypoint.
IMPORT_EXCEPTIONS = {("src.gui.scheduler_worker", "src.bootstrap.scheduling")}


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    imported: str
    reason: str

    def __str__(self):
        return f"{self.path}:{self.line}: {self.imported}: {self.reason}"


def module_name(path: Path, source_root: Path) -> str:
    parts = list(path.relative_to(source_root.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def static_imports(text: str, module: str, *, is_package=False, known_modules=()):
    """Yield normalized targets for both 'import x' and relative/from imports."""
    package = module if is_package else module.rpartition(".")[0]
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                target = resolve_name("." * node.level + target, package)
            children = [f"{target}.{alias.name}" for alias in node.names]
            # from ..infrastructure import schedule_exporter imports that module,
            # whereas from ..infrastructure.schedule_exporter import Exporter
            # imports a symbol from the stated module.
            targets = {child if child in known_modules else target for child in children}
            for imported in sorted(targets):
                yield node.lineno, imported


def import_problem(module: str, imported: str) -> str | None:
    parts = module.split(".")
    layer = parts[1] if len(parts) > 1 else ""
    root = imported.split(".")[0]
    if root in {"tools", "tests", "benchmark", "gui_app", "main", "mcp_app"}:
        return "runtime code must not depend on developer tools, tests or entrypoints"
    if root == "src":
        target_parts = imported.split(".")
        if len(target_parts) < 2:
            return None
        target_layer = target_parts[1]
        if (module, imported) in IMPORT_EXCEPTIONS:
            return None
        if target_layer not in ALLOWED_LAYERS.get(layer, set()):
            return f"{layer or 'src'} must not import layer {target_layer}"
    elif layer == "scheduling" and root not in sys.stdlib_module_names:
        return "the scheduling domain must use only its own modules and the standard library"
    elif root in {"PyQt6", "tkinter"}:
        if layer in {"application", "infrastructure", "mcp_adapter"}:
            return "UI dependencies belong to presentation, not this module"
    elif root in {"mcp", "anyio"} and layer != "mcp_adapter":
        return "optional MCP dependencies belong to mcp_adapter"
    return None


def check_architecture(source_root=ROOT / "src") -> list[Violation]:
    source_root = Path(source_root)
    files = sorted(source_root.rglob("*.py"))
    if not files:
        raise ValueError(f"No Python sources found in {source_root}")
    modules = {module_name(path, source_root) for path in files}
    violations = []
    for path in files:
        module = module_name(path, source_root)
        relative = path.relative_to(source_root.parent).as_posix()
        for line, imported in static_imports(
            path.read_text(encoding="utf-8"), module,
            is_package=path.name == "__init__.py", known_modules=modules,
        ):
            reason = import_problem(module, imported)
            if reason is None and imported.startswith('src.') and imported not in modules:
                reason = 'first-party import target does not exist'
            if reason:
                violations.append(Violation(relative, line, imported, reason))
    return violations


def main() -> int:
    violations = check_architecture()
    for violation in violations:
        print(violation)
    if not violations:
        print("Architecture boundaries passed.")
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main())
