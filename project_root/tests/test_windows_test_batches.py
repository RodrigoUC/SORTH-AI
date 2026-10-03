"""The serial Windows gate must execute every collected test exactly once."""
import json
from itertools import combinations
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from tools.windows_test_batches import BATCHES, batch_for_nodeid, verify_inventories


@pytest.mark.parametrize("nodeid,batch", [
    ("tests/test_gui/test_editor.py::test_save[param]", "gui"),
    ("tests/test_gui/nested/test_new.py::test_new", "gui"),
    ("tests/test_gui/test_theme_runtime.py::test_new[param]", "theme-runtime"),
    ("tests/test_gui/test_theme_runtime_extra.py::test_new", "gui"),
    ("tests/test_gui/test_new.py::test_case[test_theme_runtime.py]", "gui"),
    ("tests/test_gui/test_appearance_dialog.py::test_new[param]", "gui-layout"),
    ("tests/test_gui/test_compact_optional_controls.py::test_new", "gui-layout"),
    ("tests/test_gui/test_settings_design.py::test_new", "gui-layout"),
    ("tests/test_gui/test_settings_design_extra.py::test_new", "gui"),
    ("tests/test_gui/test_new.py::test_case[test_settings_design.py]", "gui"),
    ("tests/test_gui_extra.py::test_new", "remaining"),
    ("tests/test_new_layer/test_new.py::test_new", "remaining"),
    ("tests/test_domain.py::test_value[tests/test_gui/value]", "remaining"),
])
def test_batches_follow_test_file_directory_not_test_or_parameter_names(nodeid, batch):
    assert batch_for_nodeid(nodeid) == batch


def write_inventory(directory, batch, nodeids):
    (directory / f"tests-{batch}-inventory.json").write_text(
        json.dumps({"batch": batch, "nodeids": nodeids}), encoding="utf-8"
    )


@pytest.fixture
def inventories(tmp_path):
    batches = {
        "gui": ["tests/test_gui/test_example.py::test_gui"],
        "gui-layout": ["tests/test_gui/test_compact_optional_controls.py::test_layout"],
        "theme-runtime": ["tests/test_gui/test_theme_runtime.py::test_theme_runtime"],
        "remaining": ["tests/test_new_layer/test_example.py::test_remaining"],
    }
    batches["all"] = [nodeid for nodes in batches.values() for nodeid in nodes]
    for batch, nodeids in batches.items():
        write_inventory(tmp_path, batch, nodeids)
    return tmp_path, batches


def test_inventory_union_is_exact_and_new_directories_are_covered(inventories):
    directory, _ = inventories
    assert verify_inventories(directory) == {"all": 4, **dict.fromkeys(BATCHES, 1)}


@pytest.mark.parametrize("batch", ["all", *BATCHES])
def test_inventory_rejects_duplicates_within_any_collection(inventories, batch):
    directory, batches = inventories
    nodes = batches[batch]
    write_inventory(directory, batch, nodes + nodes)
    with pytest.raises(ValueError, match=f"Duplicate {batch} node IDs"):
        verify_inventories(directory)


@pytest.mark.parametrize("batch", BATCHES)
@pytest.mark.parametrize("problem", ["missing", "unexpected", "misplaced"])
def test_inventory_rejects_incomplete_or_misplaced_batches(inventories, batch, problem):
    directory, batches = inventories
    new_node = batches[batch][0] + "[new]"
    if problem == "missing":
        write_inventory(directory, "all", batches["all"] + [new_node])
    elif problem == "unexpected":
        write_inventory(directory, batch, batches[batch] + [new_node])
    else:
        other = next(name for name in BATCHES if name != batch)
        write_inventory(directory, batch, batches[other])
        write_inventory(directory, other, batches[batch])
    with pytest.raises(ValueError, match="Wrong .* batch" if problem == "misplaced" else f"{problem}=\\['"):
        verify_inventories(directory)


@pytest.mark.parametrize("first,second", list(combinations(BATCHES, 2)))
def test_inventory_rejects_overlap_between_every_pair(inventories, first, second):
    directory, batches = inventories
    write_inventory(directory, second, batches[first] + batches[second])
    with pytest.raises(ValueError, match="overlap=\\['"):
        verify_inventories(directory)


@pytest.mark.parametrize("batch", ["all", *BATCHES])
@pytest.mark.parametrize("problem", ["absent", "empty", "mislabelled", "invalid-nodeid"])
def test_inventory_requires_readable_complete_records(inventories, batch, problem):
    directory, batches = inventories
    path = directory / f"tests-{batch}-inventory.json"
    if problem == "absent":
        path.unlink()
    elif problem == "empty":
        write_inventory(directory, batch, [])
    elif problem == "mislabelled":
        path.write_text(json.dumps({"batch": "wrong-label", "nodeids": batches[batch]}), encoding="utf-8")
    else:
        write_inventory(directory, batch, [None])
    with pytest.raises((OSError, ValueError)):
        verify_inventories(directory)


def test_real_pytest_batches_capture_skips_failures_and_distinct_junit(tmp_path):
    root = Path(__file__).resolve().parents[1]
    gui = tmp_path / "tests/test_gui"
    gui.mkdir(parents=True)
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    (gui / "test_gui.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('value', [1, 2])\n"
        "def test_parameter(value): assert value > 0\n"
        "@pytest.mark.skip(reason='platform-only example')\n"
        "def test_skipped(): pass\n"
        "def test_failed(): assert False\n", encoding="utf-8"
    )
    (tmp_path / "tests/test_remaining.py").write_text("def test_remaining(): pass\n", encoding="utf-8")
    (gui / "test_theme_runtime.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('value', [1, 2])\n"
        "def test_new_runtime_case(value): assert value > 0\n"
        "@pytest.mark.skip(reason='runtime-only example')\n"
        "def test_skipped(): pass\n"
        "def test_failed(): assert False\n", encoding="utf-8"
    )
    (gui / "test_compact_optional_controls.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('value', [1, 2])\n"
        "def test_layout(value): assert value > 0\n"
        "@pytest.mark.skip(reason='layout-only example')\n"
        "def test_skipped(): pass\n"
        "def test_failed(): assert False\n", encoding="utf-8"
    )
    for directory in (gui / "new_gui_directory", tmp_path / "tests/new_layer"):
        directory.mkdir()
        (directory / f"test_{directory.name}.py").write_text("def test_auto_included(): pass\n", encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(root), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    for batch in ("all", *BATCHES):
        args = [sys.executable, "-m", "pytest", "-q", "-p", "tools.windows_test_batches",
                f"--test-inventory=tests-{batch}-inventory.json"]
        if batch == "all":
            args.append("--collect-only")
        else:
            args.extend([f"--regression-batch={batch}", f"--junitxml=tests-{batch}.xml"])
        result = subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == (1 if batch in ("gui", "gui-layout", "theme-runtime") else 0), result.stdout + result.stderr
    expected_counts = {"all": 15, "gui": 5, "gui-layout": 4, "theme-runtime": 4, "remaining": 2}
    assert verify_inventories(tmp_path) == expected_counts
    full = json.loads((tmp_path / "tests-all-inventory.json").read_text())["nodeids"]
    for batch in BATCHES:
        selected = json.loads((tmp_path / f"tests-{batch}-inventory.json").read_text())["nodeids"]
        assert selected == [nodeid for nodeid in full if batch_for_nodeid(nodeid) == batch]
    layout_report = ET.parse(tmp_path / "tests-gui-layout.xml").getroot()
    assert len(layout_report.findall(".//testcase")) == 4
    assert len(layout_report.findall(".//failure")) == 1
    assert len(layout_report.findall(".//skipped")) == 1
    gui_report = ET.parse(tmp_path / "tests-gui.xml").getroot()
    theme_runtime_report = ET.parse(tmp_path / "tests-theme-runtime.xml").getroot()
    remaining_report = ET.parse(tmp_path / "tests-remaining.xml").getroot()
    assert len(gui_report.findall(".//failure")) == 1
    assert len(gui_report.findall(".//skipped")) == 1
    assert len(theme_runtime_report.findall(".//failure")) == 1
    assert len(theme_runtime_report.findall(".//skipped")) == 1
    assert len(remaining_report.findall(".//testcase")) == 2
    verified = subprocess.run(
        [sys.executable, str(root / "tools/windows_test_batches.py"), "--verify", str(tmp_path)],
        capture_output=True, text=True, timeout=10,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert json.loads((tmp_path / "test-batches-verified.json").read_text()) == expected_counts
    (tmp_path / "tests-remaining-inventory.json").unlink()
    missing = subprocess.run(
        [sys.executable, str(root / "tools/windows_test_batches.py"), "--verify", str(tmp_path)],
        capture_output=True, text=True, timeout=10,
    )
    assert missing.returncode == 1
    assert "Regression batch coverage failed" in missing.stderr
    assert not (tmp_path / "test-batches-verified.json").exists()
