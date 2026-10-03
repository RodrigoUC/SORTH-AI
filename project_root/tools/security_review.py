"""Read-only security checks. Exit 0: reviewed; 1: findings; 2: incomplete/error."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(finding):
    # Ignore line numbers, but bind each exception to its exact source context.
    code = '\n'.join(re.sub(r'^\d+ ', '', line) for line in finding['code'].splitlines())
    return (finding['filename'].removeprefix('./'), finding['test_id'],
            hashlib.sha256(code.encode()).hexdigest())


def review_bandit(report, baseline, returncode):
    if returncode not in (0, 1) or report.get('errors') or not report.get('metrics', {}).get('_totals', {}).get('loc'):
        raise ValueError('Bandit scan failed, skipped source, or scanned no code')
    reviewed = {}
    for item in baseline:
        if not item.get('reason') or not item.get('reviewed_on'):
            raise ValueError('Every exception needs a reason and review date')
        key = (item['file'], item['test_id'], item['code_sha256'])
        if key in reviewed:
            raise ValueError('Duplicate exception')
        reviewed[key] = item['count']
    new = []
    for finding in report['results']:
        key = fingerprint(finding)
        if reviewed.get(key, 0) > 0:
            reviewed[key] -= 1
        else:
            new.append(finding)
    # Removing a finding must also remove its obsolete exception.
    if any(reviewed.values()):
        raise ValueError('Stale Bandit exception: review/remove it; do not regenerate blindly')
    if (returncode == 0) != (not report['results']):
        raise ValueError('Bandit return code disagrees with findings')
    return new


def review_audit(report, returncode):
    dependencies = report.get('dependencies')
    if returncode not in (0, 1) or not dependencies:
        raise ValueError('Dependency audit failed or returned no dependencies')
    if any('skip_reason' in item or 'vulns' not in item for item in dependencies):
        raise ValueError('Dependency audit skipped packages')
    findings = [item for item in dependencies if item['vulns']]
    if (returncode == 0) != (not findings):
        raise ValueError('Dependency audit return code disagrees with findings')
    return findings


def read_lock(lock_name):
    text = (ROOT / lock_name).read_text()
    # pip-compile writes continuation lines and explanatory comments.
    lines = text.replace('\\\n', ' ').splitlines()
    pins, audit_lines = {}, []
    for line in lines:
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r'(.+?)((?:\s+--hash=sha256:[0-9a-f]{64})+)', line)
        if not match:
            raise ValueError('Unexpected lock syntax; review auditor compatibility')
        requirement = Requirement(match[1])
        specifiers = list(requirement.specifier)
        if requirement.url or len(specifiers) != 1 or specifiers[0].operator != '==' or '*' in specifiers[0].version:
            raise ValueError('Every audited requirement must have one exact version')
        name = re.sub(r'[-_.]+', '-', requirement.name.lower())
        if name in pins:
            raise ValueError('Duplicate lock package: split platform versions need separate reviewed audits')
        version = specifiers[0].version
        pins[name] = version
        # Audit the UNION of platform packages. Never evaluate markers on this host.
        # This derived inventory is for metadata queries only, NEVER installation.
        hashes = ' '.join(match[2].split())
        audit_lines.append(f'{name}=={version} {hashes}')
    if not pins:
        raise ValueError('Empty dependency lock')
    return pins, audit_lines


def write_audit_inventory(lock_name, output):
    pins, lines = read_lock(lock_name)
    output.write_text('# AUDIT ONLY: union of platforms; never install this file.\n' +
                      '\n'.join(lines) + '\n')
    return pins


def validate_lock(lock_name='requirements-windows.lock', manifests=None):
    manifests = manifests or ('requirements.txt', 'requirements-dev.txt', 'requirements-docs.txt')
    pins, _ = read_lock(lock_name)
    for manifest in manifests:
        for line in (ROOT / manifest).read_text().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            if line.startswith('-r '):
                if line[3:].strip() not in manifests:
                    raise ValueError(f'Unreviewed manifest include: {line}')
                continue
            name, version = line.split('==')
            if pins.get(re.sub(r'[-_.]+', '-', name.lower())) != version:
                raise ValueError(f'{manifest}: {name} differs from the selected lock')
    return pins


def execute(command, output):
    output.unlink(missing_ok=True)  # Never accept a stale report after a failed tool.
    result = subprocess.run(command, cwd=ROOT, check=False, timeout=600)
    return json.loads(output.read_text()), result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check', choices=['static', 'dependencies', 'optional-dependencies'])
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build/security')
    args = parser.parse_args()
    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        if args.check == 'static':
            report, code = execute([sys.executable, '-m', 'bandit', '--ignore-nosec', '-r',
                                    'src', 'tools', *sorted(p.name for p in ROOT.glob('*.py')),
                                    '-f', 'json', '-o', str(directory / 'bandit.json')], directory / 'bandit.json')
            baseline = json.loads((ROOT / 'security/bandit-reviewed.json').read_text())
            findings = review_bandit(report, baseline, code)
        else:
            optional = args.check == 'optional-dependencies'
            lock_name = 'requirements-mcp.lock' if optional else 'requirements-windows.lock'
            manifests = ('requirements-mcp.txt', 'requirements-mcp-dev.txt') if optional else None
            pins = validate_lock(lock_name, manifests)
            audit_input = directory / 'audit-inventory.txt'
            if write_audit_inventory(lock_name, audit_input) != pins:
                raise ValueError('Lock changed while preparing audit inventory')
            report, code = execute([sys.executable, '-m', 'pip_audit', '--disable-pip',
                                    '--require-hashes', '--strict', '-r', str(audit_input),
                                    '--format', 'json', '--output', str(directory / 'pip-audit.json'),
                                    '--progress-spinner', 'off', '--cache-dir', str(directory / 'cache')],
                                   directory / 'pip-audit.json')
            findings = review_audit(report, code)
            actual = {re.sub(r'[-_.]+', '-', d['name'].lower()): d['version'] for d in report['dependencies']}
            if actual != pins:
                raise ValueError('Audited packages do not exactly match the selected lock')
        status = 'findings' if findings else 'reviewed'
        result = {'check': args.check, 'status': status, 'new_findings': findings}
        exit_code = int(bool(findings))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {'check': args.check, 'status': 'incomplete', 'error': str(error)}
        exit_code = 2
    (directory / f'{args.check}-status.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
