"""Stacked PRs receive the same exact-head read-only gates as main PRs."""
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('name', ['windows-review.yml', 'security-review.yml', 'mcp-optional.yml'])
def test_main_and_review_stacks_have_read_only_review_gates(name):
    text = (ROOT / '.github' / 'workflows' / name).read_text()
    assert '  pull_request:\n    branches: [main, feat/optional-mcp-preview, feat/product-controls-and-scenarios, feat/import-performance-layer]' in text
    assert '  push:\n    branches: [main]' in text
    assert 'pull_request_target:' not in text
    assert re.search(r'^permissions:\n  contents: read\n', text, re.MULTILINE)
    assert 'persist-credentials: false' in text
    assert 'ref: ${{ github.event.pull_request.head.sha || github.sha }}' in text
    refs = re.findall(r'uses:\s+[^@\s]+@([^\s#]+)', text)
    assert refs and all(re.fullmatch(r'[0-9a-f]{40}', ref) for ref in refs)


def test_windows_regression_gate_is_bounded_and_diagnostic():
    text = (ROOT / ".github/workflows/windows-review.yml").read_text()
    steps = {
        block.splitlines()[0]: block
        for block in text.split("      - name: ")[1:]
    }
    inventory = steps["Collect full regression inventory"]
    assert "id: regression-inventory" in inventory
    assert "timeout-minutes: 2" in inventory
    assert "-m pytest --collect-only -q -p tools.windows_test_batches" in inventory
    assert "--test-inventory=build/reports/tests-all-inventory.json" in inventory
    assert "if ($LASTEXITCODE -ne 0)" in inventory

    for name, batch, minutes in (("Run GUI regression tests", "gui", 8),
                                 ("Run GUI layout regression tests", "gui-layout", 6),
                                 ("Run theme runtime regression tests", "theme-runtime", 7),
                                 ("Run remaining regression tests", "remaining", 4)):
        step = steps[name]
        assert f"timeout-minutes: {minutes}" in step
        assert "-m pytest -vv -p tools.windows_test_batches" in step
        assert f"--regression-batch={batch}" in step
        assert f"--test-inventory=build/reports/tests-{batch}-inventory.json" in step
        assert f"-o faulthandler_timeout=120 --junitxml=build/reports/tests-{batch}.xml" in step
        assert "if ($LASTEXITCODE -ne 0)" in step
        assert "continue-on-error:" not in step
        assert "--maxfail" not in step and " -x " not in step

    collect_after_failure = "if: ${{ !cancelled() && steps.regression-inventory.outcome == 'success' }}"
    assert collect_after_failure in steps["Run GUI layout regression tests"]
    assert collect_after_failure in steps["Run theme runtime regression tests"]
    assert collect_after_failure in steps["Run remaining regression tests"]
    verify = steps["Verify exact regression batch coverage"]
    assert collect_after_failure in verify
    assert "timeout-minutes: 1" in verify
    assert "tools/windows_test_batches.py --verify build/reports" in verify
    assert "if ($LASTEXITCODE -ne 0)" in verify
    assert text.index("Collect full regression inventory") < text.index("Run GUI regression tests")
    assert text.index("Run GUI regression tests") < text.index("Run GUI layout regression tests")
    assert text.index("Run GUI layout regression tests") < text.index("Run theme runtime regression tests")
    assert text.index("Run theme runtime regression tests") < text.index("Run remaining regression tests")
    assert text.index("Run remaining regression tests") < text.index("Verify exact regression batch coverage")
    assert text.index("Verify exact regression batch coverage") < text.index("Generate current manual")
    assert "continue-on-error:" not in text
    # Build and package steps retain the default success() gate after all tests.
    for name, step in steps.items():
        if text.index(f"      - name: {name}") >= text.index("      - name: Generate current manual"):
            if name != "Upload test and smoke evidence":
                assert "        if:" not in step
    evidence = steps["Upload test and smoke evidence"]
    assert "if: always()" in evidence
    assert "project_root/build/reports/*.json" in evidence
    assert "project_root/build/reports/*.xml" in evidence
