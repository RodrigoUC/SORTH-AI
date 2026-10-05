"""Fail-closed first-release preparation. Never executes downloaded assets.

Only the explicit `publish` command writes to GitHub. It has no retry, clobber,
resume, tag-update, or deletion mode. A partial draft requires human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = 'RodrigoUC/SORTH-AI'
VERSION = '2.0.0'
TAG = 'v2.0.0'
ROOT = Path(__file__).resolve().parents[2]
APPROVAL = '.github/release-approval.json'
WORKFLOW = '.github/workflows/windows-review.yml'
GATES = ('windows_acceptance', 'defender_review', 'native_source_correspondence',
         'license_and_redistribution', 'unsigned_distribution_accepted',
         'public_release_authorized')
SHA = re.compile('[0-9a-f]{40}')
DIGEST = re.compile('[0-9a-f]{64}')
SAFE_NAME = re.compile('[A-Za-z0-9][A-Za-z0-9._-]*')
MAX_ASSET = 1024 * 1024 * 1024
MAX_INSTALLER = 512 * 1024 * 1024
MAX_METADATA = 2 * 1024 * 1024
GIT = shutil.which('git')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    with Path(path).open('rb') as source:
        raw = source.read(MAX_METADATA + 1)
    require(len(raw) <= MAX_METADATA, 'Local metadata exceeds bound')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def record(path):
    return {'size': Path(path).stat().st_size, 'sha256': digest(path)}


def asset_names(sha):
    build = f'{VERSION}-{sha[:12]}'
    return {
        f'SORTH-windows-x64-{build}-unsigned.zip',
        f'SORTH-{build}-windows-x64-unsigned-setup.exe',
        f'SORTH-{VERSION}-{sha}-source.tar.gz',
        'THIRD-PARTY-SOURCES.tar.gz', 'MANUAL_USUARIO.pdf', 'build-info.json',
        'SHA256SUMS.txt',
    }


def validate_records(records, names):
    require(isinstance(records, dict) and set(records) == set(names), 'Exact asset file list required')
    for name, item in records.items():
        require(bool(SAFE_NAME.fullmatch(name)), 'Unsafe asset filename')
        require(isinstance(item, dict) and set(item) == {'size', 'sha256'}, 'Invalid asset record')
        limit = MAX_INSTALLER if name.endswith('-setup.exe') else MAX_ASSET
        require(type(item['size']) is int and 0 < item['size'] <= limit, 'Invalid asset size')
        require(isinstance(item['sha256'], str) and bool(DIGEST.fullmatch(item['sha256'])), 'Missing SHA-256')


def validate_approval(value, *, publishing=False):
    keys = {'schema_version', 'repository', 'version', 'tag', 'publish', 'source_commit',
            'source_run_id', 'source_run_attempt', 'artifact_id', 'artifact_sha256',
            'candidate_sha256', 'assets', 'gates', 'release_notes'}
    require(isinstance(value, dict) and set(value) == keys, 'Unexpected approval fields')
    require(type(value['schema_version']) is int and value['schema_version'] == 1 and value['repository'] == REPO, 'Wrong schema/repository')
    require(value['version'] == VERSION and value['tag'] == TAG, 'Wrong release version/tag')
    require(type(value['publish']) is bool, 'publish must be a boolean')
    require(not publishing or value['publish'], 'Public release is held')
    require(isinstance(value['gates'], dict) and set(value['gates']) == set(GATES), 'Missing release gates')
    for gate in value['gates'].values():
        require(isinstance(gate, dict) and set(gate) == {'passed', 'evidence'}, 'Invalid gate')
        require(type(gate['passed']) is bool and isinstance(gate['evidence'], str), 'Invalid gate evidence')
    require(isinstance(value['release_notes'], str) and len(value['release_notes']) <= 64000, 'Invalid release notes')
    if not value['publish']:
        return value
    require(isinstance(value['source_commit'], str) and bool(SHA.fullmatch(value['source_commit'])), 'Full source SHA required')
    for key in ('source_run_id', 'source_run_attempt', 'artifact_id'):
        require(type(value[key]) is int and value[key] > 0, f'Invalid {key}')
    for key in ('artifact_sha256', 'candidate_sha256'):
        require(isinstance(value[key], str) and bool(DIGEST.fullmatch(value[key])), f'Invalid {key}')
    validate_records(value['assets'], asset_names(value['source_commit']))
    require(all(g['passed'] and g['evidence'].strip() for g in value['gates'].values()), 'Outstanding release gates')
    require(bool(value['release_notes'].strip()), 'Approved release notes required')
    return value


def verify_identity(info, sha):
    require(info.get('version') == VERSION and info.get('source_commit') == sha
            and info.get('build_id') == f'{VERSION}-{sha[:12]}'
            and info.get('signed') is False, 'Wrong build identity/version/signing state')


def checksums(path):
    result = {}
    with Path(path).open('rb') as source:
        raw = source.read(8193)
    require(len(raw) <= 8192, 'Checksum metadata exceeds bound')
    lines = raw.decode('utf-8-sig').splitlines()
    require(len(lines) <= 16, 'Too many checksum rows')
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)', line)
        require(match is not None, 'Malformed SHA256SUMS.txt')
        require(match[2] not in result, 'Duplicate checksum entry')
        result[match[2]] = match[1]
    return result


def verify_candidate(directory, sha, approval=None):
    directory = Path(directory)
    names = asset_names(sha)
    require(directory.is_dir(), 'Candidate directory missing')
    require({p.name for p in directory.iterdir()} == names | {'release-candidate.json'}, 'Missing/extra candidate assets')
    require(all(p.is_file() and not p.is_symlink() for p in directory.iterdir()), 'Unsafe candidate asset')
    candidate = read_json(directory / 'release-candidate.json')
    require(set(candidate) == {'schema_version', 'repository', 'version', 'tag', 'source_commit',
                              'source_run_id', 'source_run_attempt', 'assets'}, 'Invalid candidate manifest')
    require(type(candidate['schema_version']) is int and candidate['schema_version'] == 1 and candidate['repository'] == REPO
            and candidate['source_commit'] == sha and candidate['version'] == VERSION
            and candidate['tag'] == TAG, 'Wrong candidate identity')
    validate_records(candidate['assets'], names)
    require(all(record(directory / n) == r for n, r in candidate['assets'].items()), 'Candidate asset digest/size mismatch')
    sums = checksums(directory / 'SHA256SUMS.txt')
    require(sums == {n: candidate['assets'][n]['sha256'] for n in names - {'SHA256SUMS.txt'}}, 'Missing/extra/incorrect checksums')
    verify_identity(read_json(directory / 'build-info.json'), sha)
    if approval is not None:
        validate_approval(approval, publishing=True)
        require(digest(directory / 'release-candidate.json') == approval['candidate_sha256'], 'Candidate manifest not approved')
        require(candidate['assets'] == approval['assets'], 'Approved assets differ')
        require(candidate['source_run_id'] == approval['source_run_id']
                and candidate['source_run_attempt'] == approval['source_run_attempt'], 'Wrong candidate run')
    return candidate


def git(*args):
    require(GIT is not None and Path(GIT).is_absolute(), 'Installed Git executable required')
    return subprocess.check_output([GIT, '-C', str(ROOT), *args], text=True).strip()


def verify_packaged_sources(archive, info, sources):
    """Compare real ZIP bytes with inventory and pinned supplier expectations.

    This proves the scoped Qt/PyQt correspondence only. It does not certify
    Microsoft/Mesa redistribution rights or replace the separate release gates.
    """
    expected = read_json(ROOT / 'third_party/release-source-correspondence.json')
    require(expected.get('schema_version') == 1, 'Wrong supplier correspondence schema')
    with tarfile.open(sources, 'r:gz') as bundle:
        matches = []
        for index, item in enumerate(bundle):
            require(index < 5000, 'Source bundle member count exceeds bound')
            if item.name == 'THIRD-PARTY-SOURCES/supplier-correspondence.json':
                matches.append(item)
        require(len(matches) == 1 and matches[0].isfile() and matches[0].size <= MAX_METADATA,
                'Missing/unsafe bundled supplier correspondence')
        supplied = json.loads(bundle.extractfile(matches[0]).read(), object_pairs_hook=unique_object)
    require(supplied == expected, 'Bundled source correspondence differs from reviewed source')
    rows = expected.get('artifact_file_expectations')
    require(isinstance(rows, list) and bool(rows), 'Missing supplier artifact expectations')
    by_path = {r['packaged_path']: r for r in rows}
    require(len(by_path) == len(rows), 'Duplicate supplier expectation')
    inventory = info.get('files')
    require(isinstance(inventory, list) and bool(inventory), 'Missing Windows file inventory')
    inventory_by_path = {r['path']: r for r in inventory}
    require(len(inventory_by_path) == len(inventory), 'Duplicate Windows inventory path')
    with zipfile.ZipFile(archive) as zf:
        entries = zf.infolist()
        names = [i.filename for i in entries]
        require(len(entries) <= 100000 and len(names) == len({n.casefold() for n in names}), 'Invalid packaged ZIP inventory')
        require(sum(i.file_size for i in entries) <= 4 * MAX_ASSET, 'Packaged ZIP exceeds bound')
        for item in entries:
            path = PurePosixPath(item.filename)
            # ZipInfo hides NUL suffixes and, on Windows, rewrites backslashes.
            require(item.orig_filename == item.filename
                    and path.as_posix() == item.filename and not path.is_absolute() and '..' not in path.parts
                    and '\\' not in item.filename and not stat.S_ISLNK(item.external_attr >> 16), 'Unsafe packaged ZIP entry')
        require(zf.getinfo('SORTH/build-info.json').file_size <= MAX_METADATA, 'Build metadata exceeds bound')
        require(json.loads(zf.read('SORTH/build-info.json'), object_pairs_hook=unique_object) == info, 'Embedded build inventory differs')
        for path, row in inventory_by_path.items():
            name = 'SORTH/' + path
            require(name in names and type(row['size']) is int and 0 <= row['size'] <= MAX_ASSET, 'Invalid/missing packaged file')
            require(zf.getinfo(name).file_size == row['size'], 'Packaged file size mismatch')
            with zf.open(name) as file:
                require(hashlib.file_digest(file, 'sha256').hexdigest() == row['sha256'], 'Packaged file digest mismatch')
        def scoped(path):
            low = path.lower()
            name = PurePosixPath(low).name
            # Detect misplaced Qt DLLs too: narrowing to the usual PyQt folder
            # would silently omit a newly introduced native dependency.
            if name.startswith('qt6') and name.endswith('.dll'):
                return True
            pyqt_path = any('pyqt' in part for part in PurePosixPath(low).parts)
            return pyqt_path and (low.endswith('.pyd') or low.endswith('.qm')
                                  or (low.endswith('.dll') and '/plugins/' in low))
        shipped = {n.removeprefix('SORTH/') for n in names if n.startswith('SORTH/') and scoped(n.removeprefix('SORTH/'))}
        required = {r['packaged_path'] for r in rows if r.get('required') is True}
        require(required <= shipped, 'Required Qt/PyQt artifact missing')
        require(bool(shipped), 'No scoped Qt/PyQt artifacts present')
        for path in shipped:
            require(path in by_path and path in inventory_by_path, 'Unmapped shipped Qt/PyQt artifact')
            expected_row, actual = by_path[path], inventory_by_path[path]
            require(expected_row.get('source_delivery_in_scope') is True, 'Shipped Qt/PyQt source is out of scope')
            require(actual['sha256'] == expected_row['sha256'] and actual['size'] == expected_row['size'],
                    'Final Qt/PyQt bytes differ from pinned supplier/source correspondence')
    return {'verified_scoped_files': len(shipped), 'required_files': len(required)}


def assemble_candidate(review, manual, sources, output, sha, run_id, attempt):
    require(bool(SHA.fullmatch(sha)), 'Full source SHA required')
    require(git('rev-parse', 'HEAD') == sha, 'Checkout is not exact source SHA')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'Tracked source tree is dirty')
    require((ROOT / 'project_root/VERSION').read_text().strip() == VERSION, 'Wrong repository version')
    review, manual, sources, output = map(Path, (review, manual, sources, output))
    require(not output.exists(), 'Candidate destination must be new')
    require(sources.is_file() and not sources.is_symlink(), 'Corresponding-source bundle not prepared')
    require(manual.is_file() and manual.read_bytes()[:5] == b'%PDF-', 'Current manual missing')
    info = read_json(review / 'build-info.json')
    verify_identity(info, sha)
    names = asset_names(sha)
    installer = next(n for n in names if n.endswith('.exe'))
    archive = next(n for n in names if n.endswith('-unsigned.zip'))
    require({p.name for p in review.iterdir()} == {installer, archive, 'build-info.json', 'SHA256SUMS.txt'}, 'Review assets missing/extra/duplicate installers')
    require(checksums(review / 'SHA256SUMS.txt') == {n: digest(review / n) for n in (installer, archive)}, 'Review checksum verification failed')
    correspondence = verify_packaged_sources(review / archive, info, sources)
    print('Verified scoped source correspondence:', json.dumps(correspondence, sort_keys=True))
    output.mkdir(parents=True)
    for name in (installer, archive, 'build-info.json'):
        require(not (review / name).is_symlink(), 'Symlinked review asset')
        shutil.copyfile(review / name, output / name)
    shutil.copyfile(manual, output / 'MANUAL_USUARIO.pdf')
    shutil.copyfile(sources, output / 'THIRD-PARTY-SOURCES.tar.gz')
    source_name = next(n for n in names if n.startswith(f'SORTH-{VERSION}') and n.endswith('.tar.gz'))
    git('archive', '--format=tar.gz', f'--prefix=SORTH-{VERSION}/',
        '-o', str(output.resolve() / source_name), sha)
    payload = {n: record(output / n) for n in sorted(names - {'SHA256SUMS.txt'})}
    (output / 'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {n}\n' for n, r in payload.items()), encoding='utf-8')
    payload['SHA256SUMS.txt'] = record(output / 'SHA256SUMS.txt')
    write_json(output / 'release-candidate.json', {
        'schema_version': 1, 'repository': REPO, 'version': VERSION, 'tag': TAG,
        'source_commit': sha, 'source_run_id': run_id, 'source_run_attempt': attempt, 'assets': payload,
    })
    return verify_candidate(output, sha)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    """Fixed repository/API host; no authenticated redirects or write retries."""
    def __init__(self, token):
        require(bool(token), 'Ephemeral GITHUB_TOKEN required')
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, method, path, data=None, *, missing=False, upload=False):
        host = 'uploads.github.com' if upload else 'api.github.com'
        require(path.startswith(f'/repos/{REPO}/'), 'Unexpected API repository')
        headers = {'Authorization': f'Bearer {self.token}', 'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'SORTH-first-release'}
        if isinstance(data, dict):
            data = json.dumps(data).encode()
            headers['Content-Type'] = 'application/json'
        elif data is not None:
            headers['Content-Type'] = 'application/octet-stream'
        request = urllib.request.Request(f'https://{host}{path}', data=data, method=method, headers=headers)
        try:
            with self.opener.open(request, timeout=120) as response:
                raw = response.read(MAX_METADATA + 1)
                require(len(raw) <= MAX_METADATA, 'GitHub metadata exceeds bound')
                return json.loads(raw, object_pairs_hook=unique_object)
        except urllib.error.HTTPError as error:
            if error.code == 404 and missing:
                return None
            raise RuntimeError(f'GitHub {method} failed with HTTP {error.code}; no automatic retry') from None

    def download_artifact(self, artifact_id, destination):
        request = urllib.request.Request(
            f'https://api.github.com/repos/{REPO}/actions/artifacts/{artifact_id}/zip',
            headers={'Authorization': f'Bearer {self.token}', 'User-Agent': 'SORTH-first-release'})
        try:
            with self.opener.open(request, timeout=60):
                raise ValueError('Expected a GitHub artifact redirect')
        except urllib.error.HTTPError as error:
            require(error.code == 302, f'Artifact download failed: HTTP {error.code}')
            url = error.headers['Location']
            error.close()
        self.download_storage(url, destination)

    def download_storage(self, url, destination):
        # Only official Actions storage, signed URL from authenticated GitHub.
        # Every hop is checked; no Authorization header ever leaves api.github.com.
        for hop in range(4):
            validate_storage_url(url)
            request = urllib.request.Request(url, headers={'User-Agent': 'SORTH-first-release'})
            try:
                response = self.opener.open(request, timeout=120)
            except urllib.error.HTTPError as error:
                require(error.code in {301, 302, 303, 307, 308} and hop < 3,
                        f'Artifact storage download failed: HTTP {error.code}')
                url = urllib.parse.urljoin(url, error.headers['Location'])
                error.close()
                continue
            with response, Path(destination).open('xb') as out:
                copied = 0
                while block := response.read(1024 * 1024):
                    copied += len(block)
                    require(copied <= 2 * MAX_ASSET, 'Artifact archive exceeds bound')
                    out.write(block)
            return
        raise ValueError('Artifact storage redirect limit exceeded')


def validate_storage_url(url):
    require(isinstance(url, str) and len(url) <= 16384
            and not any(ord(c) <= 32 or ord(c) >= 127 for c in url)
            and '\\' not in url, 'Unsafe artifact storage URL')
    parts = urllib.parse.urlsplit(url)
    require(parts.scheme == 'https' and parts.hostname and parts.netloc == parts.hostname
            and not parts.username and not parts.password and not parts.fragment,
            'Unsafe artifact storage redirect')
    require(parts.hostname == 'results-receiver.actions.githubusercontent.com'
            or parts.hostname.endswith('.blob.core.windows.net'), 'Unexpected artifact storage host')


def prefix(path):
    return f'/repos/{REPO}/{path}'


def verify_run(run, manifest):
    require(run.get('head_sha') == manifest['source_commit'] and run.get('head_branch') == 'main'
            and run.get('event') == 'push' and run.get('path') == WORKFLOW
            and run.get('status') == 'completed' and run.get('conclusion') == 'success'
            and run.get('run_attempt') == manifest['source_run_attempt']
            and run.get('id') == manifest['source_run_id']
            and run.get('repository', {}).get('full_name') == REPO
            and run.get('head_repository', {}).get('full_name') == REPO, 'Candidate must come from successful exact-main Windows push run')


def verify_approval_run(run, event_sha, run_id):
    require(run.get('id') == run_id and run.get('head_sha') == event_sha
            and run.get('head_branch') == 'release-approval/v2.0.0'
            and run.get('path') == '.github/workflows/first-release.yml'
            and run.get('event') == 'push' and run.get('status') == 'completed'
            and run.get('conclusion') == 'success'
            and run.get('repository', {}).get('full_name') == REPO
            and run.get('head_repository', {}).get('full_name') == REPO,
            'Invalid approval workflow trigger provenance')


def check_absent(api):
    require(api.request('GET', prefix(f'git/ref/tags/{TAG}'), missing=True) is None, 'Tag already exists; never replace it')
    require(api.request('GET', prefix(f'releases/tags/{TAG}'), missing=True) is None, 'Release already exists; never overwrite it')
    # The tag endpoint alone may omit drafts. Enumerate authenticated releases.
    for page in range(1, 101):
        releases = api.request('GET', prefix(f'releases?per_page=100&page={page}'))
        require(isinstance(releases, list), 'Invalid release listing')
        require(all(item.get('tag_name') != TAG for item in releases), 'Release/draft already exists; never overwrite it')
        if len(releases) < 100:
            return
    raise ValueError('Release listing exceeds inspection bound; publication held')


def verify_approval_tree(manifest, event_sha):
    require(bool(SHA.fullmatch(event_sha)), 'Full approval commit required')
    sha = manifest['source_commit']
    require(git('rev-parse', 'HEAD') in {event_sha, sha}, 'Wrong approval/source checkout')
    require(int(git('cat-file', '-s', f'{event_sha}:{APPROVAL}')) <= MAX_METADATA, 'Committed approval exceeds bound')
    committed = json.loads(git('show', f'{event_sha}:{APPROVAL}'), object_pairs_hook=unique_object)
    require(committed == manifest, 'Approval is not the event commit manifest')
    git('merge-base', '--is-ancestor', sha, event_sha)
    require(git('diff', '--name-only', sha, event_sha).splitlines() == [APPROVAL], 'Approval commit may change only release-approval.json')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'Dirty approval checkout')


def extract_flat(archive, destination, expected=None):
    destination = Path(destination)
    require(not destination.exists(), 'Artifact destination must be new')
    with zipfile.ZipFile(archive) as zf:
        entries = zf.infolist()
        require(len(entries) <= 100, 'Too many artifact ZIP entries')
        names = [item.filename for item in entries]
        require(len(names) == len({n.casefold() for n in names}), 'Duplicate/case-aliased ZIP entry')
        if expected is not None:
            require(set(names) == set(expected), 'Wrong artifact file list')
        require(sum(i.file_size for i in entries) <= 2 * MAX_ASSET, 'Expanded artifact exceeds bound')
        for item in entries:
            path = PurePosixPath(item.filename)
            parts = path.parts
            # Validate the actual archived name before trusting its normalized form.
            require(item.orig_filename == item.filename
                    and parts and path.as_posix() == item.filename and not path.is_absolute()
                    and '..' not in parts and all(SAFE_NAME.fullmatch(p) and not p.endswith('.') for p in parts)
                    and '\\' not in item.filename and ':' not in item.filename, 'Unsafe/noncanonical ZIP path')
            require(not stat.S_ISLNK(item.external_attr >> 16), 'Symlink in artifact')
        destination.mkdir(parents=True)
        for item in entries:
            target = destination.joinpath(*PurePosixPath(item.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(item) as source, target.open('xb') as out:
                shutil.copyfileobj(source, out, length=1024 * 1024)


def verify_current_approval(api, event_sha):
    require(bool(SHA.fullmatch(event_sha)), 'Exact approval SHA required')
    current = api.request('GET', prefix('git/ref/heads/release-approval/v2.0.0'), missing=True)
    require(current is not None and current.get('object', {}).get('sha') == event_sha,
            'Approval branch moved or was removed; publication held')


def fetch_candidate(api, manifest, output, event_sha):
    validate_approval(manifest, publishing=True)
    sha = manifest['source_commit']
    verify_current_approval(api, event_sha)
    require(api.request('GET', prefix('git/ref/heads/main'))['object']['sha'] == sha, 'Approved source is no longer exact main')
    verify_run(api.request('GET', prefix(f'actions/runs/{manifest["source_run_id"]}')), manifest)
    artifact = api.request('GET', prefix(f'actions/artifacts/{manifest["artifact_id"]}'))
    require(artifact.get('name') == f'SORTH-release-candidate-{manifest["source_run_id"]}-{manifest["source_run_attempt"]}'
            and artifact.get('expired') is False
            and artifact.get('digest') == 'sha256:' + manifest['artifact_sha256']
            and artifact.get('workflow_run', {}).get('id') == manifest['source_run_id']
            and artifact.get('workflow_run', {}).get('head_sha') == sha, 'Wrong/expired/unapproved artifact')
    archive = Path(str(output) + '.zip')
    api.download_artifact(manifest['artifact_id'], archive)
    require(digest(archive) == manifest['artifact_sha256'], 'Artifact archive SHA-256 mismatch')
    extract_flat(archive, output, asset_names(sha) | {'release-candidate.json'})
    verify_candidate(output, sha, manifest)
    check_absent(api)


def verify_release_metadata(release, manifest, release_id, draft):
    require(release.get('id') == release_id and release.get('draft') is draft
            and release.get('tag_name') == TAG and release.get('name') == f'SORTH-AI {VERSION}'
            and release.get('body') == manifest['release_notes']
            and release.get('prerelease') is False
            and release.get('target_commitish') == manifest['source_commit'],
            'Release metadata differs from approved draft/public state; stop')


def publish(api, manifest, directory, event_sha):
    """Call only after explicit public-release approval. No asset is executed."""
    validate_approval(manifest, publishing=True)
    verify_candidate(directory, manifest['source_commit'], manifest)
    verify_current_approval(api, event_sha)
    require(api.request('GET', prefix('git/ref/heads/main'))['object']['sha'] == manifest['source_commit'], 'Main changed before publication')
    verify_run(api.request('GET', prefix(f'actions/runs/{manifest["source_run_id"]}')), manifest)
    check_absent(api)
    api.request('POST', prefix('git/refs'), {'ref': f'refs/tags/{TAG}', 'sha': manifest['source_commit']})
    release = api.request('POST', prefix('releases'), {
        'tag_name': TAG, 'target_commitish': manifest['source_commit'], 'name': f'SORTH-AI {VERSION}',
        'body': manifest['release_notes'], 'draft': True, 'prerelease': False, 'make_latest': 'false',
    })
    require(release.get('draft') is True and type(release.get('id')) is int, 'Draft creation unverified; stop')
    release_id = release['id']
    for name in sorted(manifest['assets']):
        response = api.request('POST', prefix(f'releases/{release_id}/assets?name={urllib.parse.quote(name)}'),
                               (Path(directory) / name).read_bytes(), upload=True)
        expected = manifest['assets'][name]
        require(response.get('name') == name and response.get('state') == 'uploaded'
                and response.get('size') == expected['size']
                and response.get('digest') == 'sha256:' + expected['sha256'], 'Uploaded asset digest missing/mismatched; draft remains held')
    assets = api.request('GET', prefix(f'releases/{release_id}/assets?per_page=100'))
    expected = manifest['assets']
    require(len(assets) == len(expected) and {a.get('name') for a in assets} == set(expected), 'Wrong uploaded file list; draft remains held')
    require(all(a.get('state') == 'uploaded' and a.get('size') == expected[a['name']]['size']
                and a.get('digest') == 'sha256:' + expected[a['name']]['sha256'] for a in assets), 'Remote asset verification failed')
    require(api.request('GET', prefix(f'git/ref/tags/{TAG}'))['object']['sha'] == manifest['source_commit'], 'Tag moved; draft remains held')
    require(api.request('GET', prefix('git/ref/heads/main'))['object']['sha'] == manifest['source_commit'], 'Main changed; draft remains held')
    held = api.request('GET', prefix(f'releases/{release_id}'))
    verify_release_metadata(held, manifest, release_id, True)
    verify_run(api.request('GET', prefix(f'actions/runs/{manifest["source_run_id"]}')), manifest)
    verify_current_approval(api, event_sha)
    result = api.request('PATCH', prefix(f'releases/{release_id}'), {'draft': False, 'make_latest': 'true'})
    verify_release_metadata(result, manifest, release_id, False)
    print(result['html_url'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    candidate = sub.add_parser('candidate')
    for arg in ('review', 'manual', 'sources', 'output', 'sha'):
        candidate.add_argument('--' + arg, required=True)
    candidate.add_argument('--run-id', type=int, required=True)
    candidate.add_argument('--attempt', type=int, required=True)
    validate = sub.add_parser('validate')
    validate.add_argument('--approval', default=str(ROOT / APPROVAL))
    for command in ('check', 'controller', 'fetch', 'publish'):
        entry = sub.add_parser(command)
        entry.add_argument('--approval', default=str(ROOT / APPROVAL))
        entry.add_argument('--directory', default='release-download')
        entry.add_argument('--event-sha', required=True)
        entry.add_argument('--approval-run-id', type=int, required=command != 'check')
    download = sub.add_parser('download-review')
    download.add_argument('--run-id', type=int, required=True)
    download.add_argument('--directory', required=True)
    args = parser.parse_args()
    if args.command == 'candidate':
        assemble_candidate(args.review, args.manual, args.sources, args.output, args.sha, args.run_id, args.attempt)
    elif args.command == 'validate':
        value = validate_approval(read_json(args.approval))
        print('Public release approved' if value['publish'] else 'Public release held (publish=false)')
    elif args.command == 'download-review':
        api = GitHub(os.environ.get('GH_TOKEN'))
        artifacts = api.request('GET', prefix(f'actions/runs/{args.run_id}/artifacts?per_page=100'))['artifacts']
        matches = [a for a in artifacts if a['name'] == f'SORTH-windows-review-{args.run_id}' and not a['expired']]
        require(len(matches) == 1, 'Exactly one same-run Windows review artifact required')
        archive = Path(args.directory + '.zip')
        api.download_artifact(matches[0]['id'], archive)
        require(matches[0].get('digest') == 'sha256:' + digest(archive), 'Review artifact SHA-256 mismatch')
        extract_flat(archive, args.directory)
    else:
        value = validate_approval(read_json(args.approval))
        if not value['publish']:
            require(args.command in {'check', 'controller'}, 'Public release held')
            print('publish=false')
            return
        verify_approval_tree(value, args.event_sha)
        if args.command == 'check':
            print('publish=true')
            return
        require(git('rev-parse', 'HEAD') == value['source_commit'], 'Controller must execute exact integrated main code')
        api = GitHub(os.environ.get('GH_TOKEN'))
        verify_approval_run(api.request('GET', prefix(f'actions/runs/{args.approval_run_id}')), args.event_sha, args.approval_run_id)
        verify_current_approval(api, args.event_sha)
        require(api.request('GET', prefix('git/ref/heads/main'))['object']['sha'] == value['source_commit'], 'Controller source is not current main')
        if args.command == 'controller':
            print('publish=true')
        elif args.command == 'fetch':
            fetch_candidate(api, value, args.directory, args.event_sha)
        else:
            publish(api, value, args.directory, args.event_sha)


if __name__ == '__main__':
    main()
