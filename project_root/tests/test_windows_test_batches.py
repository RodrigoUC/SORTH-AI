"""The serial Windows gate must execute every collected test exactly once."""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from tools.windows_test_batches import batch_for_nodeid, verify_inventories


@pytest.mark.parametrize("nodeid,batch", [
    ("tests/test_gui/test_editor.py::test_save[param]", "gui"),
    ("tests/test_gui/nested/test_new.py::test_new", "gui"),
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
    gui = ["tests/test_gui/test_example.py::test_gui"]
    remaining = ["tests/test_new_layer/test_example.py::test_remaining"]
    for batch, nodeids in (("all", gui + remaining), ("gui", gui), ("remaining", remaining)):
        write_inventory(tmp_path, batch, nodeids)
    return tmp_path, gui, remaining


def test_inventory_union_is_exact_and_new_directories_are_covered(inventories):
    directory, _, _ = inventories
    assert verify_inventories(directory) == {"all": 2, "gui": 1, "remaining": 1}


@pytest.mark.parametrize("batch", ["all", "gui", "remaining"])
def test_inventory_rejects_duplicates_within_any_collection(inventories, batch):
    directory, gui, remaining = inventories
    nodes = {"all": gui + remaining, "gui": gui, "remaining": remaining}[batch]
    write_inventory(directory, batch, nodes + nodes)
    with pytest.raises(ValueError, match=f"Duplicate {batch} node IDs"):
        verify_inventories(directory)


@pytest.mark.parametrize("problem", ["missing", "unexpected", "overlap", "misplaced"])
def test_inventory_rejects_incomplete_or_overlapping_batches(inventories, problem):
    directory, gui, remaining = inventories
    if problem == "missing":
        write_inventory(directory, "all", gui + remaining + ["tests/test_new.py::test_missing"])
    elif problem == "unexpected":
        write_inventory(directory, "remaining", remaining + ["tests/test_new.py::test_unexpected"])
    elif problem == "overlap":
        write_inventory(directory, "remaining", gui + remaining)
    else:
        write_inventory(directory, "gui", remaining)
        write_inventory(directory, "remaining", gui)
    with pytest.raises(ValueError, match="Wrong gui batch" if problem == "misplaced" else f"{problem}=\\['"):
        verify_inventories(directory)


@pytest.mark.parametrize("problem", ["absent", "empty", "mislabelled", "invalid-nodeid"])
def test_inventory_requires_readable_complete_records(inventories, problem):
    directory, gui, _ = inventories
    path = directory / "tests-gui-inventory.json"
    if problem == "absent":
        path.unlink()
    elif problem == "empty":
        write_inventory(directory, "gui", [])
    elif problem == "mislabelled":
        path.write_text(json.dumps({"batch": "remaining", "nodeids": gui}), encoding="utf-8")
    else:
        write_inventory(directory, "gui", [None])
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
    env = {**os.environ, "PYTHONPATH": str(root), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    for batch in ("all", "gui", "remaining"):
        args = [sys.executable, "-m", "pytest", "-q", "-p", "tools.windows_test_batches",
                f"--test-inventory=tests-{batch}-inventory.json"]
        if batch == "all":
            args.append("--collect-only")
        else:
            args.extend([f"--regression-batch={batch}", f"--junitxml=tests-{batch}.xml"])
        result = subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == (1 if batch == "gui" else 0), result.stdout + result.stderr
    assert verify_inventories(tmp_path) == {"all": 5, "gui": 4, "remaining": 1}
    full = json.loads((tmp_path / "tests-all-inventory.json").read_text())["nodeids"]
    for batch in ("gui", "remaining"):
        selected = json.loads((tmp_path / f"tests-{batch}-inventory.json").read_text())["nodeids"]
        assert selected == [nodeid for nodeid in full if batch_for_nodeid(nodeid) == batch]
    gui_report = ET.parse(tmp_path / "tests-gui.xml").getroot()
    remaining_report = ET.parse(tmp_path / "tests-remaining.xml").getroot()
    assert len(gui_report.findall(".//failure")) == 1
    assert len(gui_report.findall(".//skipped")) == 1
    assert len(remaining_report.findall(".//testcase")) == 1
    verified = subprocess.run(
        [sys.executable, str(root / "tools/windows_test_batches.py"), "--verify", str(tmp_path)],
        capture_output=True, text=True, timeout=10,
    )
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert json.loads((tmp_path / "test-batches-verified.json").read_text()) == {
        "all": 5, "gui": 4, "remaining": 1,
    }
    (tmp_path / "tests-remaining-inventory.json").unlink()
    missing = subprocess.run(
        [sys.executable, str(root / "tools/windows_test_batches.py"), "--verify", str(tmp_path)],
        capture_output=True, text=True, timeout=10,
    )
    assert missing.returncode == 1
    assert "Regression batch coverage failed" in missing.stderr
    assert not (tmp_path / "test-batches-verified.json").exists()
