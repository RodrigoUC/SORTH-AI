"""Remove only unused Qt PDF image support from a finished onedir build.

ReportLab provides SORTH PDF export. This removes qpdf.dll and, only after PE
normal/delay-import inspection of every retained executable, Qt6Pdf.dll. It
never strips Network, Mesa or unrelated Qt plugins. A Windows smoke is still
required because PE imports cannot describe dynamic LoadLibrary requests.
"""
import argparse
import hashlib
import json
from pathlib import Path

PLUGIN = '_internal/PyQt6/Qt6/plugins/imageformats/qpdf.dll'
LIBRARY = '_internal/PyQt6/Qt6/bin/Qt6Pdf.dll'


def pe_imports(path):
    import pefile
    with pefile.PE(str(path), fast_load=True) as pe:
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
            pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT']])
        return sorted({entry.dll.decode('ascii').lower()
                       for attribute in ('DIRECTORY_ENTRY_IMPORT', 'DIRECTORY_ENTRY_DELAY_IMPORT')
                       for entry in getattr(pe, attribute, [])})


def prune(app_dir, report_path, scan=pe_imports):
    root = Path(app_dir).resolve()
    report_path = Path(report_path)
    if report_path.exists():
        raise FileExistsError('Use a fresh evidence report path.')
    if not (root / 'SORTH.exe').is_file():
        raise ValueError('Expected a finished onedir build with SORTH.exe.')
    files = sorted(p for p in root.rglob('*') if p.is_file())
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Symlinked build contents are not supported.')
    targets = {root / PLUGIN, root / LIBRARY}
    for path in files:
        if path.name.lower() in ('qpdf.dll', 'qt6pdf.dll') and path not in targets:
            raise ValueError(f'Unexpected Qt PDF location: {path.relative_to(root)}')
        if path.name.lower().startswith('qtpdf') and path.suffix.lower() == '.pyd':
            raise ValueError('QtPdf Python bindings present; removal requires review.')
    retained = [p for p in files if p not in targets and p.suffix.lower() in {'.dll', '.pyd', '.exe'}]
    imports = {p.relative_to(root).as_posix(): scan(p) for p in retained}
    dependents = [name for name, deps in imports.items() if {'qt6pdf.dll', 'qpdf.dll'} & set(deps)]
    if dependents:
        raise ValueError(f'Retained binaries require Qt PDF: {dependents}')
    removed = [{'path': p.relative_to(root).as_posix(),
                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(targets) if p.exists()]
    report = {'policy': 'remove-unused-qt-pdf-only-v1', 'removed': removed,
              'retained_pe_imports': imports,
              'runtime_validation': 'PENDING packaged and installed Windows smoke; dynamic loading is not proven by PE imports',
              'license_clearance': False}
    # Write evidence before mutation, so a report failure leaves the build intact.
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('x', encoding='utf-8') as out:
        json.dump(report, out, indent=2)
    for p in sorted(targets):
        if p.exists():
            p.unlink()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', type=Path, default=Path('dist/SORTH'))
    parser.add_argument('--report', type=Path, default=Path('build/reports/qt-pdf-pruning.json'))
    args = parser.parse_args()
    prune(args.app_dir, args.report)


if __name__ == '__main__':
    main()
