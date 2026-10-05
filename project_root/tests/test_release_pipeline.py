"""Network-free publisher/manifest tests; unittest runs without app dependencies."""
import copy
import hashlib
import importlib.util
import json
import io
import tarfile
from pathlib import Path
import re
import shutil
import subprocess
import warnings
import urllib.error
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('release_pipeline', ROOT / 'project_root/tools/release_pipeline.py')
rp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rp)
SHA = 'a' * 40
EVENT = 'b' * 40


def build_candidate(directory):
    directory.mkdir()
    names = rp.asset_names(SHA)
    for name in names - {'SHA256SUMS.txt'}:
        (directory / name).write_bytes(name.encode())
    rp.write_json(directory / 'build-info.json', {
        'version': '2.0.0', 'source_commit': SHA, 'build_id': f'2.0.0-{SHA[:12]}', 'signed': False})
    sums = ''.join(f'{rp.digest(directory / n)}  {n}\n' for n in sorted(names - {'SHA256SUMS.txt'}))
    (directory / 'SHA256SUMS.txt').write_text(sums)
    assets = {n: rp.record(directory / n) for n in names}
    candidate = {'schema_version': 1, 'repository': rp.REPO, 'version': rp.VERSION,
                 'tag': rp.TAG, 'source_commit': SHA, 'source_run_id': 42,
                 'source_run_attempt': 1, 'assets': assets}
    rp.write_json(directory / 'release-candidate.json', candidate)
    approval = {'schema_version': 1, 'repository': rp.REPO, 'version': rp.VERSION,
                'tag': rp.TAG, 'publish': True, 'source_commit': SHA, 'source_run_id': 42,
                'source_run_attempt': 1, 'artifact_id': 84, 'artifact_sha256': 'c' * 64,
                'candidate_sha256': rp.digest(directory / 'release-candidate.json'), 'assets': assets,
                'gates': {g: {'passed': True, 'evidence': 'reviewed evidence reference'} for g in rp.GATES},
                'release_notes': 'Approved unsigned first release notes.'}
    return approval


def good_run():
    return {'head_sha': SHA, 'head_branch': 'main', 'event': 'push', 'path': rp.WORKFLOW,
            'status': 'completed', 'conclusion': 'success', 'run_attempt': 1, 'id': 42,
            'repository': {'full_name': rp.REPO}, 'head_repository': {'full_name': rp.REPO}}


class FakeGitHub:
    def __init__(self, approval, *, tag_exists=False, release_exists=False, omit_digest=False,
                 fail_upload=False, extra_asset=False, changed_main=False):
        self.approval = approval
        self.tag_exists = tag_exists
        self.release_exists = release_exists
        self.omit_digest = omit_digest
        self.fail_upload = fail_upload
        self.extra_asset = extra_asset
        self.changed_main = changed_main
        self.calls = []
        self.assets = []
        self.created_tag = False
        self.created_draft = False
        self.published = False

    def request(self, method, path, data=None, **kwargs):
        self.calls.append((method, path, data))
        if path.endswith('/git/ref/heads/release-approval/v2.0.0'):
            return {'object': {'sha': EVENT}}
        if path.endswith('/git/ref/heads/main'):
            return {'object': {'sha': EVENT if self.changed_main else SHA}}
        if '/actions/runs/' in path:
            return good_run()
        if path.endswith(f'/git/ref/tags/{rp.TAG}'):
            return {'object': {'sha': SHA}} if self.tag_exists or self.created_tag else None
        if path.endswith(f'/releases/tags/{rp.TAG}'):
            return {'id': 1} if self.release_exists else None
        if '/releases?per_page=' in path:
            return []
        if method == 'POST' and path.endswith('/git/refs'):
            self.created_tag = True
            return {'object': {'sha': SHA}}
        if method == 'POST' and path.endswith('/releases'):
            assert data['draft'] is True and data['make_latest'] == 'false'
            self.created_draft = True
            return {'id': 7, 'draft': True}
        if method == 'POST' and '/assets?name=' in path:
            if self.fail_upload:
                raise RuntimeError('simulated upload failure')
            name = path.split('?name=')[1]
            item = {'name': name, 'size': len(data), 'state': 'uploaded'}
            if not self.omit_digest:
                item['digest'] = 'sha256:' + hashlib.sha256(data).hexdigest()
            self.assets.append(item)
            return item
        if method == 'GET' and '/assets?' in path:
            return self.assets + ([{'name': 'unexpected.exe'}] if self.extra_asset else [])
        if method == 'GET' and path.endswith('/releases/7'):
            return {'id': 7, 'draft': True, 'tag_name': rp.TAG, 'name': f'SORTH-AI {rp.VERSION}',
                    'body': self.approval['release_notes'], 'prerelease': False, 'target_commitish': SHA}
        if method == 'PATCH' and path.endswith('/releases/7'):
            self.published = True
            return {'id': 7, 'draft': False, 'tag_name': rp.TAG, 'name': f'SORTH-AI {rp.VERSION}',
                    'body': self.approval['release_notes'], 'prerelease': False, 'target_commitish': SHA,
                    'html_url': f'https://github.com/{rp.REPO}/releases/tag/{rp.TAG}'}
        raise AssertionError((method, path))


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'candidate'
        self.approval = build_candidate(self.directory)

    def test_default_is_held(self):
        value = copy.deepcopy(self.approval)
        value['publish'] = False
        # The approval branch is intentionally allowed to contain publish=true.
        # Test behavior from a fixed fixture, not the current checkout's manifest.
        rp.validate_approval(value)
        with self.assertRaisesRegex(ValueError, 'held'):
            rp.validate_approval(value, publishing=True)

    def test_valid_candidate_and_manifest(self):
        rp.verify_candidate(self.directory, SHA, self.approval)
        rp.validate_approval(self.approval, publishing=True)
        self.assertEqual(len([n for n in self.approval['assets'] if n.endswith('.exe')]), 1)

    def test_wrong_identity_and_schema_rejected(self):
        for key, value in [('version', '2.0.1'), ('tag', 'v2.0.1'), ('source_commit', 'a' * 12),
                           ('repository', 'someone/other'), ('source_run_id', True),
                           ('source_run_attempt', 0), ('artifact_sha256', None), ('publish', 'true')]:
            with self.subTest(key=key):
                bad = copy.deepcopy(self.approval)
                bad[key] = value
                with self.assertRaises(ValueError):
                    rp.validate_approval(bad)
        bad = copy.deepcopy(self.approval)
        bad['extra'] = True
        with self.assertRaises(ValueError):
            rp.validate_approval(bad)

    def test_every_gate_requires_evidence(self):
        for name in rp.GATES:
            for field, value in [('passed', False), ('evidence', '  ')]:
                with self.subTest(gate=name, field=field):
                    bad = copy.deepcopy(self.approval)
                    bad['gates'][name][field] = value
                    with self.assertRaisesRegex(ValueError, 'Outstanding'):
                        rp.validate_approval(bad)

    def test_all_assets_required_and_extra_installer_rejected(self):
        for name in self.approval['assets']:
            with self.subTest(name=name):
                bad = copy.deepcopy(self.approval)
                del bad['assets'][name]
                with self.assertRaises(ValueError):
                    rp.validate_approval(bad)
        bad = copy.deepcopy(self.approval)
        bad['assets']['other-setup.exe'] = {'size': 1, 'sha256': 'd' * 64}
        with self.assertRaises(ValueError):
            rp.validate_approval(bad)

    def test_no_checksum_or_wrong_checksum_is_rejected(self):
        sums = self.directory / 'SHA256SUMS.txt'
        sums.write_text('')
        with self.assertRaises(ValueError):
            rp.verify_candidate(self.directory, SHA, self.approval)
        sums.unlink()
        with self.assertRaises(ValueError):
            rp.verify_candidate(self.directory, SHA, self.approval)

    def test_missing_digest_and_size_rejected(self):
        for field, value in [('sha256', ''), ('size', 0), ('size', True)]:
            bad = copy.deepcopy(self.approval)
            bad['assets']['MANUAL_USUARIO.pdf'][field] = value
            with self.assertRaises(ValueError):
                rp.validate_approval(bad)

    def test_installer_respects_updater_512_mib_limit(self):
        name = next(n for n in self.approval['assets'] if n.endswith('.exe'))
        self.approval['assets'][name]['size'] = 512 * 1024 * 1024
        rp.validate_approval(self.approval)
        self.approval['assets'][name]['size'] += 1
        with self.assertRaisesRegex(ValueError, 'asset size'):
            rp.validate_approval(self.approval)

    def test_changed_file_or_candidate_cannot_publish(self):
        (self.directory / 'MANUAL_USUARIO.pdf').write_bytes(b'changed')
        api = FakeGitHub(self.approval)
        with self.assertRaises(ValueError):
            rp.publish(api, self.approval, self.directory, EVENT)
        self.assertEqual(api.calls, [])

    def test_changed_manifest_digest_rejected(self):
        self.approval['candidate_sha256'] = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'not approved'):
            rp.verify_candidate(self.directory, SHA, self.approval)

    def test_preexisting_tag_or_release_never_written(self):
        for flag in ('tag_exists', 'release_exists'):
            api = FakeGitHub(self.approval, **{flag: True})
            with self.assertRaisesRegex(ValueError, 'already exists'):
                rp.publish(api, self.approval, self.directory, EVENT)
            self.assertFalse(any(method != 'GET' for method, _, _ in api.calls))

    def test_preexisting_draft_without_tag_on_later_page_never_written(self):
        class DraftAPI(FakeGitHub):
            def request(self, method, path, data=None, **kwargs):
                if '/releases?per_page=100&page=1' in path:
                    return [{'tag_name': f'v0.0.{i}'} for i in range(100)]
                if '/releases?per_page=100&page=2' in path:
                    return [{'tag_name': rp.TAG, 'draft': True}]
                return super().request(method, path, data, **kwargs)
        api = DraftAPI(self.approval)
        with self.assertRaisesRegex(ValueError, 'draft already exists'):
            rp.publish(api, self.approval, self.directory, EVENT)
        self.assertFalse(any(m != 'GET' for m, _, _ in api.calls))

    def test_storage_redirects_reject_downgrade_credentials_ports_and_other_hosts(self):
        for url in ['http://x.blob.core.windows.net/a', 'https://evil.example/a',
                    'https://x.blob.core.windows.net.evil.example/a',
                    'https://user@x.blob.core.windows.net/a', 'https://x.blob.core.windows.net:443/a',
                    'https://x.blob.core.windows.net/a#fragment', 'https://x.blob.core.windows.net/a\n']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                rp.validate_storage_url(url)
        rp.validate_storage_url('https://productionresultssa0.blob.core.windows.net/a?sig=value')
        rp.validate_storage_url('https://results-receiver.actions.githubusercontent.com/a')

    def test_revoked_or_deleted_approval_branch_never_written(self):
        for current in (None, {'object': {'sha': 'f' * 40}}):
            class RevokedAPI(FakeGitHub):
                def request(self, method, path, data=None, **kwargs):
                    if path.endswith('/git/ref/heads/release-approval/v2.0.0'):
                        return current
                    return super().request(method, path, data, **kwargs)
            api = RevokedAPI(self.approval)
            with self.assertRaisesRegex(ValueError, 'Approval branch moved'):
                rp.publish(api, self.approval, self.directory, EVENT)
            self.assertFalse(any(m != 'GET' for m, _, _ in api.calls))

    def test_revocation_after_upload_keeps_draft(self):
        class RevokedAPI(FakeGitHub):
            def request(self, method, path, data=None, **kwargs):
                if path.endswith('/git/ref/heads/release-approval/v2.0.0') and self.assets:
                    return None
                return super().request(method, path, data, **kwargs)
        api = RevokedAPI(self.approval)
        with self.assertRaisesRegex(ValueError, 'Approval branch moved'):
            rp.publish(api, self.approval, self.directory, EVENT)
        self.assertTrue(api.created_draft)
        self.assertFalse(api.published)

    def test_local_metadata_is_bounded(self):
        path = Path(self.temp.name) / 'oversized.json'
        path.write_bytes(b' ' * (rp.MAX_METADATA + 1))
        with self.assertRaisesRegex(ValueError, 'metadata exceeds'):
            rp.read_json(path)
        with self.assertRaisesRegex(ValueError, 'Checksum metadata exceeds'):
            rp.checksums(path)
        path.write_text(''.join('a' * 64 + f'  file{i}.zip\n' for i in range(17)))
        with self.assertRaisesRegex(ValueError, 'Too many checksum'):
            rp.checksums(path)

    def test_main_changed_never_written(self):
        api = FakeGitHub(self.approval, changed_main=True)
        with self.assertRaisesRegex(ValueError, 'Main changed'):
            rp.publish(api, self.approval, self.directory, EVENT)
        self.assertFalse(any(method != 'GET' for method, _, _ in api.calls))

    def test_artifact_transport_strips_credentials_and_bounds_redirects(self):
        api = rp.GitHub('synthetic-token')
        calls = []
        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                if len(calls) == 1:
                    raise urllib.error.HTTPError(request.full_url, 302, 'redirect',
                        {'Location': 'https://productionresultssa0.blob.core.windows.net/a?sig=synthetic'}, io.BytesIO())
                return io.BytesIO(b'archive')
        api.opener = Opener()
        api.download_artifact(84, Path(self.temp.name) / 'transport.zip')
        self.assertEqual(calls[0].get_header('Authorization'), 'Bearer synthetic-token')
        self.assertIsNone(calls[1].get_header('Authorization'))
        class Loop:
            def open(self, request, timeout):
                calls.append(request)
                raise urllib.error.HTTPError(request.full_url, 302, 'redirect',
                    {'Location': request.full_url}, io.BytesIO())
        api.opener = Loop()
        calls.clear()
        with self.assertRaises(ValueError):
            api.download_storage('https://productionresultssa0.blob.core.windows.net/a', Path(self.temp.name) / 'loop.zip')
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(c.get_header('Authorization') is None for c in calls))
        class Downgrade:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(request.full_url, 302, 'redirect',
                    {'Location': 'http://productionresultssa0.blob.core.windows.net/a'}, io.BytesIO())
        api.opener = Downgrade()
        with self.assertRaisesRegex(ValueError, 'Unsafe artifact'):
            api.download_storage('https://productionresultssa0.blob.core.windows.net/a', Path(self.temp.name) / 'downgrade.zip')

    def test_api_metadata_response_is_bounded(self):
        api = rp.GitHub('synthetic-token')
        class Oversized:
            def open(self, request, timeout):
                return io.BytesIO(b' ' * (rp.MAX_METADATA + 1))
        api.opener = Oversized()
        with self.assertRaisesRegex(ValueError, 'metadata exceeds'):
            api.request('GET', rp.prefix('releases'))

    def test_success_creates_draft_then_uploads_verifies_and_publishes(self):
        api = FakeGitHub(self.approval)
        rp.publish(api, self.approval, self.directory, EVENT)
        self.assertTrue(api.published)
        writes = [(m, p) for m, p, _ in api.calls if m != 'GET']
        self.assertTrue(writes[0][1].endswith('/git/refs'))
        self.assertTrue(writes[1][1].endswith('/releases'))
        self.assertEqual(writes[-1], ('PATCH', rp.prefix('releases/7')))
        self.assertEqual(len(api.assets), len(self.approval['assets']))
        self.assertFalse(any(m == 'DELETE' for m, _, _ in api.calls))

    def test_partial_failures_leave_draft_held_and_no_retries(self):
        for flag in ('omit_digest', 'fail_upload', 'extra_asset'):
            with self.subTest(flag=flag):
                api = FakeGitHub(self.approval, **{flag: True})
                with self.assertRaises((ValueError, RuntimeError)):
                    rp.publish(api, self.approval, self.directory, EVENT)
                self.assertTrue(api.created_draft)
                self.assertFalse(api.published)
                self.assertFalse(any(m in {'PATCH', 'DELETE'} for m, _, _ in api.calls))
                targets = [p for m, p, _ in api.calls if m == 'POST']
                self.assertEqual(len(targets), len(set(targets)))

    def test_fetch_verifies_archive_digest_and_provenance(self):
        archive = Path(self.temp.name) / 'approved.zip'
        with zipfile.ZipFile(archive, 'w') as zf:
            for item in self.directory.iterdir():
                zf.write(item, item.name)
        self.approval['artifact_sha256'] = rp.digest(archive)
        artifact = {'id': 84, 'name': 'SORTH-release-candidate-42-1', 'expired': False,
                    'digest': 'sha256:' + self.approval['artifact_sha256'],
                    'workflow_run': {'id': 42, 'head_sha': SHA}}
        outer = self
        class FetchAPI(FakeGitHub):
            def request(self, method, path, data=None, **kwargs):
                if path.endswith('/actions/artifacts/84'):
                    return artifact
                return super().request(method, path, data, **kwargs)
            def download_artifact(self, artifact_id, destination):
                outer.assertEqual(artifact_id, 84)
                shutil.copyfile(archive, destination)
        api = FetchAPI(self.approval)
        rp.fetch_candidate(api, self.approval, Path(self.temp.name) / 'downloaded', EVENT)
        self.assertFalse(any(m != 'GET' for m, _, _ in api.calls))
        for index, (field, value) in enumerate([('expired', True), ('name', 'other'),
                                               ('digest', None), ('workflow_run', {'id': 43, 'head_sha': SHA})]):
            original = artifact[field]
            artifact[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                rp.fetch_candidate(api, self.approval, Path(self.temp.name) / f'bad-download{index}', EVENT)
            artifact[field] = original
        archive.write_bytes(b'changed after metadata')
        with self.assertRaisesRegex(ValueError, 'archive SHA-256'):
            rp.fetch_candidate(api, self.approval, Path(self.temp.name) / 'corrupted-download', EVENT)

    def test_candidate_assembly_uses_exact_git_source_and_all_required_assets(self):
        source = Path(self.temp.name) / 'source-repository'
        source.mkdir()
        (source / 'project_root').mkdir()
        (source / 'project_root/VERSION').write_text('2.0.0\n')
        (source / 'README.md').write_text('Synthetic source fixture.\n')
        native_path = '_internal/PyQt6/QtCore.pyd'
        native = b'synthetic Qt bytes'
        expected = {'schema_version': 1, 'artifact_file_expectations': [{'packaged_path': native_path,
            'size': len(native), 'sha256': hashlib.sha256(native).hexdigest(),
            'required': True, 'source_delivery_in_scope': True}]}
        (source / 'third_party').mkdir()
        rp.write_json(source / 'third_party/release-source-correspondence.json', expected)
        for args in [('init',), ('config', 'user.name', 'Test'), ('config', 'user.email', 'test@example.invalid'),
                     ('add', '.'), ('commit', '-m', 'fixture')]:
            subprocess.run(['git', '-C', str(source), *args], check=True, capture_output=True)
        sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        review = Path(self.temp.name) / 'review'
        review.mkdir()
        names = rp.asset_names(sha)
        archive_name = next(n for n in names if n.endswith('-unsigned.zip'))
        installer_name = next(n for n in names if n.endswith('.exe'))
        for name in (archive_name, installer_name):
            (review / name).write_bytes(b'synthetic fixture bytes')
        info = {'version': '2.0.0', 'source_commit': sha, 'build_id': f'2.0.0-{sha[:12]}', 'signed': False,
                'files': [{'path': native_path, 'size': len(native), 'sha256': hashlib.sha256(native).hexdigest()}]}
        rp.write_json(review / 'build-info.json', info)
        with zipfile.ZipFile(review / archive_name, 'w') as zf:
            zf.writestr('SORTH/' + native_path, native)
            zf.writestr('SORTH/build-info.json', json.dumps(info))
        (review / 'SHA256SUMS.txt').write_text(''.join(f'{rp.digest(review / n)}  {n}\n' for n in (archive_name, installer_name)))
        manual = Path(self.temp.name) / 'manual.pdf'
        manual.write_bytes(b'%PDF-synthetic fixture')
        bundle = Path(self.temp.name) / 'sources.tar.gz'
        raw = json.dumps(expected).encode()
        with tarfile.open(bundle, 'w:gz') as tar:
            member = tarfile.TarInfo('THIRD-PARTY-SOURCES/supplier-correspondence.json')
            member.size = len(raw)
            tar.addfile(member, io.BytesIO(raw))
        output = Path(self.temp.name) / 'assembled'
        with patch.object(rp, 'ROOT', source):
            value = rp.assemble_candidate(review, manual, bundle, output, sha, 42, 1)
            self.assertEqual(value['source_commit'], sha)
            self.assertEqual(set(value['assets']), names)
            for bad_sha in (SHA, sha[:12]):
                with self.assertRaises(ValueError):
                    rp.assemble_candidate(review, manual, bundle, output, bad_sha, 42, 1)
            with self.assertRaisesRegex(ValueError, 'must be new'):
                rp.assemble_candidate(review, manual, bundle, output, sha, 42, 1)
            (source / 'README.md').write_text('uncommitted overlay')
            with self.assertRaisesRegex(ValueError, 'dirty'):
                rp.assemble_candidate(review, manual, bundle, Path(self.temp.name) / 'dirty', sha, 42, 1)

    def test_wrong_or_failed_or_pr_or_rerun_source_rejected(self):
        for key, value in [('head_sha', EVENT), ('head_branch', 'release/prep'), ('event', 'pull_request'),
                           ('path', 'other.yml'), ('status', 'in_progress'), ('conclusion', 'failure'),
                           ('run_attempt', 2), ('head_repository', {'full_name': 'fork/repo'})]:
            run = good_run()
            run[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                rp.verify_run(run, self.approval)

    def test_actual_native_bytes_require_matching_scoped_source(self):
        root = Path(self.temp.name) / 'correspondence'
        (root / 'third_party').mkdir(parents=True)
        core = '_internal/PyQt6/QtCore.pyd'
        qm = '_internal/PyQt6/Qt6/translations/qtbase_es.qm'
        original = {core: b'core bytes', qm: b'translation bytes'}
        def row(path, required):
            return {'packaged_path': path, 'size': len(original[path]),
                    'sha256': hashlib.sha256(original[path]).hexdigest(),
                    'required': required, 'source_delivery_in_scope': True}
        expected = {'schema_version': 1, 'artifact_file_expectations': [row(core, True), row(qm, False)]}
        bundle = root / 'sources.tar.gz'
        def prepare(files, *, metadata_files=None, matrix=None, bundle_matrix=None):
            matrix = matrix or expected
            rp.write_json(root / 'third_party/release-source-correspondence.json', matrix)
            raw = json.dumps(bundle_matrix or matrix).encode()
            with tarfile.open(bundle, 'w:gz') as tar:
                entry = tarfile.TarInfo('THIRD-PARTY-SOURCES/supplier-correspondence.json')
                entry.size = len(raw)
                tar.addfile(entry, io.BytesIO(raw))
            info = {'files': [{'path': n, 'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
                              for n, b in (metadata_files or files).items()]}
            archive = root / 'app.zip'
            with zipfile.ZipFile(archive, 'w') as zf:
                for n, b in files.items():
                    zf.writestr('SORTH/' + n, b)
                zf.writestr('SORTH/build-info.json', json.dumps(info))
            return archive, info
        with patch.object(rp, 'ROOT', root):
            for files in ({core: original[core]}, original):
                archive, info = prepare(files)
                result = rp.verify_packaged_sources(archive, info, bundle)
                self.assertEqual(result['verified_scoped_files'], len(files))
            for files, declared in [({core: b'changed'}, {core: original[core]}),
                                     ({core: b'changed'}, None), ({qm: original[qm]}, None),
                                     ({**original, '_internal/PyQt6/Unknown.pyd': b'unknown'}, None),
                                     ({**original, '_internal/Qt6Unexpected.dll': b'unknown'}, None),
                                     ({**original, '_internal/QT6UNEXPECTED.DLL': b'unknown'}, None),
                                     ({**original, '_internal/Elsewhere/PyQt6/Unknown.pyd': b'unknown'}, None)]:
                archive, info = prepare(files, metadata_files=declared)
                with self.assertRaises(ValueError):
                    rp.verify_packaged_sources(archive, info, bundle)
            out_of_scope = copy.deepcopy(expected)
            out_of_scope['artifact_file_expectations'][0]['source_delivery_in_scope'] = False
            archive, info = prepare(original, matrix=out_of_scope)
            with self.assertRaisesRegex(ValueError, 'out of scope'):
                rp.verify_packaged_sources(archive, info, bundle)
            archive, info = prepare(original, bundle_matrix=out_of_scope)
            with self.assertRaisesRegex(ValueError, 'differs from reviewed'):
                rp.verify_packaged_sources(archive, info, bundle)

    def test_approval_tree_allows_only_manifest_diff(self):
        def fake_git(*args):
            if args[:2] == ('rev-parse', 'HEAD'):
                return SHA
            if args[0] == 'cat-file':
                return str(len(json.dumps(self.approval)))
            if args[0] == 'show':
                return json.dumps(self.approval)
            if args[0] == 'diff':
                return rp.APPROVAL
            return ''
        with patch.object(rp, 'git', side_effect=fake_git), patch.object(rp.subprocess, 'run'):
            rp.verify_approval_tree(self.approval, EVENT)
        def changed_git(*args):
            return rp.APPROVAL + '\nproject_root/tools/release_pipeline.py' if args[0] == 'diff' else fake_git(*args)
        with patch.object(rp, 'git', side_effect=changed_git), patch.object(rp.subprocess, 'run'):
            with self.assertRaisesRegex(ValueError, 'only'):
                rp.verify_approval_tree(self.approval, EVENT)

    def test_archive_traversal_duplicates_and_symlinks_rejected(self):
        for index, names in enumerate([['../escape'], ['/absolute'], ['a', 'a'], ['a\\b'], ['C:bad'],
                                       ['artifacts//build-info.json'], ['artifacts/./build-info.json'],
                                       ['A.txt', 'a.txt'], ['a.']]):
            archive = Path(self.temp.name) / f'bad{index}.zip'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(archive, 'w') as zf:
                    for name in names:
                        zf.writestr(name, b'bad')
            with self.assertRaises(ValueError):
                rp.extract_flat(archive, Path(self.temp.name) / f'out{index}')
        archive = Path(self.temp.name) / 'symlink.zip'
        with zipfile.ZipFile(archive, 'w') as zf:
            info = zipfile.ZipInfo('link')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, b'/etc/passwd')
        with self.assertRaises(ValueError):
            rp.extract_flat(archive, Path(self.temp.name) / 'symlink-out')

    def test_duplicate_json_and_checksum_rows_rejected(self):
        path = Path(self.temp.name) / 'bad.json'
        path.write_text('{"publish":false,"publish":true}')
        with self.assertRaises(ValueError):
            rp.read_json(path)
        path.write_text(('a' * 64 + '  file.zip\n') * 2)
        with self.assertRaises(ValueError):
            rp.checksums(path)

    def test_only_default_branch_controller_has_write_permission(self):
        release = (ROOT / '.github/workflows/first-release.yml').read_text()
        controller = (ROOT / '.github/workflows/publish-first-release.yml').read_text()
        windows = (ROOT / '.github/workflows/windows-review.yml').read_text()
        self.assertEqual(controller.count('contents: write'), 1)
        self.assertNotIn('contents: write', controller.split('  publisher:', 1)[0])
        self.assertNotIn('contents: write', release + windows)
        self.assertIn('workflow_run:', controller)
        self.assertIn("github.event.workflow_run.event == 'push'", controller)
        self.assertIn("github.event.workflow_run.head_branch == 'release-approval/v2.0.0'", controller)
        self.assertIn('ref: main', controller.split('  publisher:', 1)[1])
        self.assertNotIn('pull_request_target', release + windows + controller)
        for ref in re.findall(r'uses:\s+[^@\s]+@([^\s#]+)', release + windows + controller):
            self.assertRegex(ref, r'^[0-9a-f]{40}$')
        self.assertIn('needs: windows-build-and-smoke', windows)
        self.assertIn('persist-credentials: false', release + controller)

    def test_controller_rejects_wrong_approval_trigger_provenance(self):
        run = {'id': 123, 'head_sha': EVENT, 'head_branch': 'release-approval/v2.0.0',
               'path': '.github/workflows/first-release.yml', 'event': 'push',
               'status': 'completed', 'conclusion': 'success',
               'repository': {'full_name': rp.REPO}, 'head_repository': {'full_name': rp.REPO}}
        rp.verify_approval_run(run, EVENT, 123)
        for key, value in [('head_sha', SHA), ('head_branch', 'main'), ('event', 'pull_request'),
                           ('id', 124), ('path', 'other.yml'), ('status', 'in_progress'),
                           ('conclusion', 'failure'), ('head_repository', {'full_name': 'fork/other'})]:
            changed = copy.deepcopy(run)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                rp.verify_approval_run(changed, EVENT, 123)

    def test_mutated_draft_metadata_never_becomes_public(self):
        for field, value in [('body', 'different'), ('prerelease', True), ('name', 'different'),
                             ('tag_name', 'v9.0.0'), ('target_commitish', EVENT), ('draft', False)]:
            class MutatedAPI(FakeGitHub):
                def request(self, method, path, data=None, **kwargs):
                    result = super().request(method, path, data, **kwargs)
                    if method == 'GET' and path.endswith('/releases/7'):
                        result[field] = value
                    return result
            api = MutatedAPI(self.approval)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'metadata differs'):
                rp.publish(api, self.approval, self.directory, EVENT)
            self.assertFalse(api.published)

    def test_source_run_is_rechecked_after_upload_before_publication(self):
        class ChangedRunAPI(FakeGitHub):
            def request(self, method, path, data=None, **kwargs):
                result = super().request(method, path, data, **kwargs)
                if '/actions/runs/' in path and self.assets:
                    result['run_attempt'] = 2
                return result
        api = ChangedRunAPI(self.approval)
        with self.assertRaisesRegex(ValueError, 'exact-main Windows'):
            rp.publish(api, self.approval, self.directory, EVENT)
        self.assertFalse(api.published)

    def test_returned_public_metadata_must_match_approval(self):
        class UnexpectedAPI(FakeGitHub):
            def request(self, method, path, data=None, **kwargs):
                result = super().request(method, path, data, **kwargs)
                if method == 'PATCH':
                    result['body'] = 'unexpected'
                return result
        api = UnexpectedAPI(self.approval)
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            rp.publish(api, self.approval, self.directory, EVENT)
        # Public PATCH may have happened; report uncertainty, never retry/undo.
        self.assertEqual(sum(m == 'PATCH' for m, _, _ in api.calls), 1)


if __name__ == '__main__':
    unittest.main()
