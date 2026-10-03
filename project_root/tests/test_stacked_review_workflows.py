"""Stacked PRs receive the same exact-head read-only gates as main PRs."""
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('name', ['windows-review.yml', 'security-review.yml', 'mcp-optional.yml'])
def test_main_and_review_stacks_have_read_only_review_gates(name):
    text = (ROOT / '.github' / 'workflows' / name).read_text()
    assert '  pull_request:\n    branches: [main, feat/optional-mcp-preview, feat/product-controls-and-scenarios]' in text
    assert '  push:\n    branches: [main]' in text
    assert 'pull_request_target:' not in text
    assert re.search(r'^permissions:\n  contents: read\n', text, re.MULTILINE)
    assert 'persist-credentials: false' in text
    assert 'ref: ${{ github.event.pull_request.head.sha || github.sha }}' in text
    refs = re.findall(r'uses:\s+[^@\s]+@([^\s#]+)', text)
    assert refs and all(re.fullmatch(r'[0-9a-f]{40}', ref) for ref in refs)


def test_windows_regression_gate_is_bounded_and_diagnostic():
    text = (ROOT / ".github/workflows/windows-review.yml").read_text()
    assert "      - name: Run all regression tests\n        timeout-minutes: 8" in text
    assert "-m pytest -vv -o faulthandler_timeout=120 --junitxml=build/reports/tests.xml" in text
