"""Serial pytest batches and an exact-coverage guard for the Windows review job.

Load with ``-p tools.windows_test_batches``. All batches collect the full suite
before selecting tests, so new tests automatically belong to exactly one batch.
The standalone verifier compares the actual selected node IDs to a separate full
collection. It does not turn failed tests into successful workflow steps.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


BATCHES = ("gui", "gui-layout", "theme-runtime", "remaining")

# Measured Windows real-font runs spend over 200 seconds in these layout and
# palette matrices alone. Keep their full modules together in a fresh serial
# process rather than letting an expanding GUI batch hit its eight-minute cap.
# The desktop MCP guide review hit that cap with no assertion failure while
# these additional native-layout matrices remained in GUI. Keep whole modules
# here so future parametrizations retain the same exact-coverage contract.
GUI_LAYOUT_FILES = frozenset({
    "tests/test_gui/test_appearance_dialog.py",
    "tests/test_gui/test_compact_optional_controls.py",
    "tests/test_gui/test_project_dialog_layout.py",
    "tests/test_gui/test_settings_design.py",
    "tests/test_gui/test_calendar_dialog_layout.py",
    "tests/test_gui/test_help_details_keyboard.py",
    "tests/test_gui/test_resource_dialog_layout.py",
    "tests/test_gui/test_theme_creation_dialog.py",
    # Run37268686625 measured GUI459s/480s and layout259s/360s. These
    # complete native-layout modules transfer ~42s without changing a limit or
    # omitting any case; new parametrizations keep the same exact routing.
    "tests/test_gui/test_update_dialog.py",
    "tests/test_gui/test_main_seed_focus.py",
    "tests/test_gui/test_menu_layout.py",
})


def batch_for_nodeid(nodeid: str) -> str:
    test_file = nodeid.split("::", 1)[0]
    if test_file == "tests/test_gui/test_theme_runtime.py":
        return "theme-runtime"
    if test_file in GUI_LAYOUT_FILES:
        return "gui-layout"
    return "gui" if test_file.startswith("tests/test_gui/") else "remaining"


def pytest_addoption(parser):
    group = parser.getgroup("Windows regression batches")
    group.addoption("--regression-batch", choices=BATCHES, default=None)
    group.addoption("--test-inventory", type=Path, default=None)


def pytest_collection_modifyitems(config, items):
    batch = config.getoption("regression_batch")
    if batch is None:
        return
    selected, deselected = [], []
    for item in items:
        (selected if batch_for_nodeid(item.nodeid) == batch else deselected).append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)


def pytest_collection_finish(session):
    destination = session.config.getoption("test_inventory")
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({
            "batch": session.config.getoption("regression_batch") or "all",
            "nodeids": [item.nodeid for item in session.items],
        }, indent=2) + "\n", encoding="utf-8")


def verify_inventories(directory: Path) -> dict[str, int]:
    """Reject duplicates, omissions, unexpected tests, and mislabelled batches."""
    inventories = {}
    for batch in ("all", *BATCHES):
        path = directory / f"tests-{batch}-inventory.json"
        inventory = json.loads(path.read_text(encoding="utf-8"))
        nodeids = inventory["nodeids"]
        if inventory["batch"] != batch or not isinstance(nodeids, list) or not nodeids:
            raise ValueError(f"Invalid or empty {batch} inventory: {path}")
        if not all(isinstance(nodeid, str) and nodeid for nodeid in nodeids):
            raise ValueError(f"Invalid node IDs in {path}")
        duplicates = [nodeid for nodeid, count in Counter(nodeids).items() if count != 1]
        if duplicates:
            raise ValueError(f"Duplicate {batch} node IDs: {duplicates!r}")
        inventories[batch] = set(nodeids)

    full = inventories["all"]
    selected = Counter(nodeid for batch in BATCHES for nodeid in inventories[batch])
    overlap = {nodeid for nodeid, count in selected.items() if count > 1}
    missing = full - selected.keys()
    unexpected = selected.keys() - full
    if overlap or missing or unexpected:
        raise ValueError(
            f"Regression inventory mismatch: overlap={sorted(overlap)!r}; "
            f"missing={sorted(missing)!r}; unexpected={sorted(unexpected)!r}"
        )
    for batch in BATCHES:
        misplaced = [nodeid for nodeid in inventories[batch] if batch_for_nodeid(nodeid) != batch]
        if misplaced:
            raise ValueError(f"Wrong {batch} batch: {sorted(misplaced)!r}")
    return {batch: len(inventories[batch]) for batch in ("all", *BATCHES)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, required=True, metavar="REPORTS_DIRECTORY")
    args = parser.parse_args()
    summary = args.verify / "test-batches-verified.json"
    try:
        summary.unlink(missing_ok=True)  # A failed rerun must not leave a stale success report.
        counts = verify_inventories(args.verify)
        summary.write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Regression batch coverage failed: {error}\n")
    breakdown = " + ".join(f"{counts[batch]} {batch}" for batch in BATCHES)
    print(f"Regression coverage verified: {breakdown} = {counts['all']} unique tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
