"""Keep the concrete four-layer README architecture enforceable as the project grows."""
import pytest

from tools.check_architecture import check_architecture, import_problem, static_imports


def test_repository_respects_readme_layer_boundaries():
    assert check_architecture() == []


@pytest.mark.parametrize(("module", "target"), [
    ("src.scheduling.course", "pandas"),
    ("src.scheduling.scheduler", "src.application.scheduling_service"),
    ("src.infrastructure.session_repository", "src.application.edit_history"),
    ("src.infrastructure.excel_reader", "src.gui.main_window"),
    ("src.application.edit_history", "PyQt6.QtCore"),
    ("src.application.schedule_preview", "src.gui.main_window"),
    ("src.application.scheduling_service", "mcp"),
    ("src.mcp_adapter.server", "PyQt6"),
    ("src.mcp_adapter.server", "src.infrastructure.session_repository"),
    ("src.gui.main_window", "tools.build_identity"),
    ("src.gui.main_window", "src.bootstrap.scheduling"),
    ("src.scheduling.course", "tests.test_scheduling"),
])
def test_reverse_or_optional_dependencies_are_rejected(module, target):
    assert import_problem(module, target)


@pytest.mark.parametrize(("module", "target"), [
    ("src.scheduling.course", "dataclasses"),
    ("src.gui.scheduler_worker", "src.bootstrap.scheduling"),
    ("src.application.scheduling_service", "src.infrastructure.excel_reader"),
    ("src.application.scheduling_service", "src.bootstrap.scheduling"),
    ("src.application.packaged_smoke", "src.gui.main_window"),
    ("src.application.packaged_workflow", "PyQt6.QtCore"),
    ("src.infrastructure.gui_session_lock", "PyQt6.QtCore"),
    ("src.mcp_adapter.server", "mcp.types"),
    ("src.mcp_adapter.worker", "src.infrastructure.schedule_exporter"),
])
def test_documented_composition_and_compatibility_seams_remain_valid(module, target):
    assert import_problem(module, target) is None


def test_static_imports_include_relative_package_and_function_local_imports():
    text = """from ..scheduling.course import Course
from ..infrastructure import schedule_exporter
def build():
    import PyQt6.QtCore
    from ..gui import main_window
"""
    imports = list(static_imports(
        text, "src.application.example",
        known_modules={"src.infrastructure.schedule_exporter", "src.gui.main_window"},
    ))
    assert imports == [(1, "src.scheduling.course"),
                       (2, "src.infrastructure.schedule_exporter"),
                       (4, "PyQt6.QtCore"), (5, "src.gui.main_window")]


def test_an_invalid_source_is_reported_without_importing_it(tmp_path):
    source = tmp_path / "src"
    (source / "scheduling").mkdir(parents=True)
    (source / "scheduling" / "course.py").write_text(
        'raise RuntimeError("must never import")\nfrom ..gui import main_window\n',
        encoding="utf-8",
    )
    violations = check_architecture(source)
    assert len(violations) == 1
    assert violations[0].path == "src/scheduling/course.py"
    assert violations[0].line == 2


def test_missing_source_directory_is_not_a_false_pass(tmp_path):
    with pytest.raises(ValueError, match="No Python sources"):
        check_architecture(tmp_path / "missing")
