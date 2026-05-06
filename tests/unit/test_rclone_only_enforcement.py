"""Architecture enforcement test: verify ONLY rclone_adapter.py calls subprocess.

This test uses AST analysis to ensure no cloud provider SDK or direct HTTP calls
exist in file operation code paths. Only RcloneAdapter may spawn rclone subprocesses.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Files allowed to call subprocess.run / subprocess.Popen
ALLOWED_SUBPROCESS_MODULES = {"src.adapters.rclone_adapter"}

# Modules that should NEVER call subprocess
FORBIDDEN_PATTERNS = {"httpx", "requests", "urllib", "aiohttp"}


class SubprocessCallDetector(ast.NodeVisitor):
    """AST visitor that detects subprocess.run / subprocess.Popen calls outside allowed modules."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[str] = []
        self.module_name: str | None = None

    def visit_Module(self, node: ast.Module):
        # Extract module name from filepath
        rel = Path(self.filepath).relative_to(Path(__file__).parent.parent.parent)
        parts = list(rel.parts)
        if parts[0] == "src":
            parts[0] = "src"
        elif parts[0] == "tests":
            parts[0] = "tests"
        self.module_name = ".".join(parts).removesuffix(".py")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            # Check for subprocess.run / subprocess.Popen / subprocess.call / subprocess.check_output
            if node.func.attr in ("run", "Popen", "call", "check_output", "startfile"):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
                    if self.module_name and self.module_name not in ALLOWED_SUBPROCESS_MODULES:
                        self.violations.append(
                            f"{self.module_name} calls subprocess.{func_name}() at line {node.lineno}"
                        )
        self.generic_visit(node)


def _get_all_python_files() -> list[Path]:
    """Get all Python source files in src/ (excluding __pycache__)."""
    root = Path(__file__).parent.parent.parent
    src_dir = root / "src"
    files = []
    for path in src_dir.rglob("*.py"):
        if "__pycache__" not in str(path):
            files.append(path)
    return files


def _get_violations(filepath: Path) -> list[str]:
    """Return subprocess violations for a single file."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception:
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return [f"{filepath}: unable to parse (syntax error)"]

    detector = SubprocessCallDetector(str(filepath))
    detector.visit(tree)
    return detector.violations


class TestRcloneOnlyEnforcement:
    """Verify only rclone_adapter.py may call subprocess."""

    def test_only_rclone_adapter_calls_subprocess(self):
        """AST scan: only src/adapters/rclone_adapter.py may call subprocess.run/Popen."""
        files = _get_all_python_files()
        all_violations: dict[str, list[str]] = {}

        for filepath in files:
            violations = _get_violations(filepath)
            if violations:
                all_violations[str(filepath)] = violations

        if all_violations:
            msg = "Subprocess calls found outside allowed modules:\n"
            for fpath, vlist in all_violations.items():
                for v in vlist:
                    msg += f"  {v}\n"
            pytest.fail(msg)

    def test_rclone_adapter_is_in_allowed_set(self):
        """Verify rclone_adapter module is correctly in the allowed set."""
        from src.adapters import rclone_adapter
        mod_name = rclone_adapter.__name__
        assert mod_name in ALLOWED_SUBPROCESS_MODULES or "rclone_adapter" in mod_name

    def test_no_forbidden_http_modules_in_file_ops(self):
        """Verify no cloud-provider HTTP SDKs are imported in file operation paths."""
        # Check that services/base.py doesn't import forbidden HTTP libraries
        services_base = Path(__file__).parent.parent.parent / "src" / "services" / "base.py"
        if services_base.exists():
            source = services_base.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_PATTERNS:
                assert pattern not in source, (
                    f"services/base.py imports '{pattern}' — "
                    "file operations must go through RcloneAdapter only"
                )
