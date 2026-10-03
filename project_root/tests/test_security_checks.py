"""Gate contracts run with stdlib unittest; no GUI or application dependencies."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.security_review import ROOT, execute, fingerprint, main, review_audit, review_bandit, validate_lock, write_audit_inventory


class SecurityGateTests(unittest.TestCase):
    def test_lock_matches_all_direct_manifests(self):
        self.assertIn('pywin32-ctypes', validate_lock())

    def test_optional_multiline_lock_and_dev_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            checksum = 'a' * 64
            (root / 'requirements-mcp.lock').write_text(
                '# generated\npackage[extra]==1.0 \\\n    --hash=sha256:' + checksum + '\n    # via manifest\n')
            (root / 'requirements-mcp.txt').write_text('package==1.0\n')
            (root / 'requirements-mcp-dev.txt').write_text('-r requirements-mcp.txt\n')
            with patch('tools.security_review.ROOT', root):
                self.assertEqual(validate_lock('requirements-mcp.lock',
                    ('requirements-mcp.txt', 'requirements-mcp-dev.txt')), {'package': '1.0'})

    def test_audit_inventory_retains_windows_only_packages_on_linux(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            checksum = 'a' * 64
            (root / 'optional.lock').write_text(
                'base==1.0 --hash=sha256:' + checksum + '\n' +
                'windows-only==2.0; sys_platform == "win32" --hash=sha256:' + checksum + '\n')
            output = root / 'audit-only.txt'
            with patch('tools.security_review.ROOT', root):
                pins = write_audit_inventory('optional.lock', output)
            self.assertEqual(pins, {'base': '1.0', 'windows-only': '2.0'})
            self.assertIn('windows-only==2.0 --hash=sha256:', output.read_text())
            self.assertNotIn('sys_platform', output.read_text())
            self.assertIn('never install', output.read_text())

    def test_audit_inventory_rejects_ambiguous_versions_and_invalid_markers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            checksum = 'a' * 64
            for requirements in (['package>=1.0'], ['package==1.*'],
                                 ['package==1.0; invalid_marker == "x"'],
                                 ['package==1.0; sys_platform == "win32"',
                                  'package==2.0; sys_platform == "linux"']):
                (root / 'optional.lock').write_text('\n'.join(
                    item + ' --hash=sha256:' + checksum for item in requirements))
                with patch('tools.security_review.ROOT', root), self.assertRaises(ValueError):
                    write_audit_inventory('optional.lock', root / 'audit-only.txt')

    def test_changed_manifest_requires_lock_refresh(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('requirements-windows.lock', 'requirements.txt', 'requirements-dev.txt', 'requirements-docs.txt'):
                (root / name).write_text((ROOT / name).read_text())
            (root / 'requirements.txt').write_text('pandas==0.0.1\n')
            with patch('tools.security_review.ROOT', root), self.assertRaises(ValueError):
                validate_lock()

    def test_audit_finding_is_not_clean(self):
        vulnerable = {'dependencies': [{'name': 'synthetic', 'version': '1', 'vulns': [{'id': 'SYNTHETIC'}]}]}
        self.assertEqual(len(review_audit(vulnerable, 1)), 1)
        with self.assertRaises(ValueError):
            review_audit(vulnerable, 0)

    def test_audit_missing_or_skipped_packages_is_incomplete(self):
        for report, code in [({}, 1), ({'dependencies': []}, 0),
                             ({'dependencies': [{'skip_reason': 'network unavailable'}]}, 0)]:
            with self.subTest(report=report), self.assertRaises(ValueError):
                review_audit(report, code)

    def test_static_exact_exceptions_are_bounded_and_stale_fail(self):
        finding = {'filename': './sample.py', 'test_id': 'B307', 'code': '1 eval(value)\n'}
        file, test, digest = fingerprint(finding)
        exception = {'file': file, 'test_id': test, 'code_sha256': digest, 'count': 1,
                     'reason': 'Synthetic test only', 'reviewed_on': '2026-10-02'}
        report = {'errors': [], 'metrics': {'_totals': {'loc': 1}}, 'results': [finding]}
        self.assertEqual(review_bandit(report, [exception], 1), [])
        report['results'].append(finding)
        self.assertEqual(len(review_bandit(report, [exception], 1)), 1)
        report['results'] = []
        with self.assertRaises(ValueError):
            review_bandit(report, [exception], 0)

    @unittest.skipUnless(importlib.util.find_spec('bandit'), 'Install security/requirements.txt for live analyzer contract')
    def test_real_bandit_finding_and_syntax_error_fail_differently(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'sample.py', Path(folder) / 'report.json'
            source.write_text('eval(input())\n')
            command = [sys.executable, '-m', 'bandit', '--ignore-nosec', str(source), '-f', 'json', '-o', str(output)]
            process = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertTrue(review_bandit(json.loads(output.read_text()), [], process.returncode))
            source.write_text('def invalid(\n')
            process = subprocess.run(command, capture_output=True, text=True, check=False)
            with self.assertRaises(ValueError):
                review_bandit(json.loads(output.read_text()), [], process.returncode)

    def test_failed_tool_cannot_reuse_stale_report(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            output.write_text('{"dependencies": []}')
            with self.assertRaises(FileNotFoundError):
                execute([sys.executable, '-c', 'raise SystemExit(2)'], output)
            self.assertFalse(output.exists())

    def test_cli_infrastructure_failure_is_exit_two(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('sys.argv', ['security_review.py', 'static', '--output-dir', folder]), \
                    patch('tools.security_review.execute', side_effect=OSError('synthetic outage')):
                self.assertEqual(main(), 2)
            result = json.loads((Path(folder) / 'static-status.json').read_text())
            self.assertEqual(result['status'], 'incomplete')

    def test_workflow_privilege_and_pinning_contract(self):
        workflow = (ROOT.parent / '.github/workflows/security-review.yml').read_text()
        self.assertIn('contents: read', workflow)
        self.assertIn('persist-credentials: false', workflow)
        for manifest in ('requirements-mcp.txt', 'requirements-mcp-dev.txt', 'requirements-mcp.lock'):
            self.assertIn(f"hashFiles('project_root/{manifest}') != ''", workflow)
        self.assertIn('schedule:', workflow)
        self.assertIn('pull_request:', workflow)
        for forbidden in ('pull_request_target', 'secrets.', 'continue-on-error', '--fix', 'write-all', 'security-events: write'):
            self.assertNotIn(forbidden, workflow)
        import re
        actions = re.findall(r'uses: (\S+)', workflow)
        self.assertEqual(len(actions), 3)
        self.assertTrue(all(re.fullmatch(r'actions/[a-z-]+@[0-9a-f]{40}', action) for action in actions))
        dependabot = (ROOT.parent / '.github/dependabot.yml').read_text()
        self.assertEqual(re.findall(r'package-ecosystem: (\S+)', dependabot), ['github-actions'])


if __name__ == '__main__':
    unittest.main()
