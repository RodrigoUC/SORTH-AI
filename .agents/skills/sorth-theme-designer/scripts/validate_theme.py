#!/usr/bin/env python3
"""Validate a theme with SORTH's canonical contract, without applying it."""

import argparse
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys


def _contract(repo_root):
    roots = [Path(repo_root).resolve()] if repo_root else Path(__file__).resolve().parents
    for root in roots:
        candidate = root / "project_root" / "src" / "gui" / "theme_contract.py"
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location("sorth_theme_contract", candidate)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
    raise FileNotFoundError(
        "SORTH's canonical theme_contract.py was not found. Run this skill inside "
        "the matching SORTH repository, or provide --repo-root. No fallback validator is used."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("theme", help="Local UTF-8 .sorth-theme.json file")
    parser.add_argument("--repo-root", help="SORTH repository containing project_root/")
    parser.add_argument("--json", action="store_true", help="Print the complete contrast report as JSON")
    args = parser.parse_args()
    try:
        contract = _contract(args.repo_root)
    except (OSError, ImportError) as error:
        print(json.dumps({"valid": False, "error": str(error)}), file=sys.stderr)
        return 3
    try:
        theme = contract.load_theme_file(args.theme)
    except (contract.ThemeValidationError, OSError) as error:
        issues = list(error.issues) if isinstance(error, contract.ThemeValidationError) else [str(error)]
        if args.json:
            print(json.dumps({"valid": False, "issues": issues}, ensure_ascii=False))
        else:
            print("Invalid SORTH theme:", file=sys.stderr)
            for issue in issues:
                print(f"- {issue}", file=sys.stderr)
        return 2
    checks = contract.contrast_checks(theme)
    if args.json:
        print(json.dumps({"valid": True, "schema_version": theme.schema_version,
                          "name": theme.name, "mode": theme.mode,
                          "runtime_compatibility": "not_checked",
                          "checks": [dict(asdict(check), passes=check.passes) for check in checks]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"Valid SORTH theme v{theme.schema_version}: {theme.name} ({theme.mode}); "
              f"{len(checks)} contrast checks passed.")
        print("This verifies the data contract, not application import or rendered accessibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
